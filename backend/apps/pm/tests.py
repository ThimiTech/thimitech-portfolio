from rest_framework.test import APITestCase
from apps.users.models import User


class ProjectWorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        def user(name, role):
            return User.objects.create_user(username=name, email=f'{name}@pm.test', password='test', role=role)
        cls.lead = user('lead', 'manager')
        cls.member = user('member', 'employee')
        cls.outsider = user('outsider', 'manager')
        cls.hr = user('hr', 'hr_admin')
        cls.guest = user('guest', 'guest')

    def as_user(self, user):
        self.client.force_authenticate(user)
        return self.client

    def project(self):
        response = self.as_user(self.lead).post('/api/pm/projects/', {
            'name': 'Watershed platform', 'key': 'WATER', 'members': [self.member.pk],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_project_bootstraps_board_and_is_private(self):
        project = self.project()
        self.assertEqual(len(project['boards']), 1)
        self.assertEqual(len(project['boards'][0]['columns']), 4)
        self.assertEqual(self.as_user(self.member).get('/api/pm/projects/').data[0]['id'], project['id'])
        self.assertEqual(self.as_user(self.outsider).get('/api/pm/projects/').data, [])
        self.assertEqual(self.client.get(f"/api/pm/projects/{project['id']}/").status_code, 404)
        self.assertEqual(self.as_user(self.guest).get('/api/pm/projects/').status_code, 403)
        self.assertEqual(self.as_user(self.member).post('/api/pm/projects/', {'name': 'x', 'key': 'X'}).status_code, 403)

    def test_task_workflow_comments_and_progress(self):
        project = self.project()
        columns = project['boards'][0]['columns']
        task = self.as_user(self.lead).post('/api/pm/tasks/', {
            'title': 'Publish catchments', 'column': columns[0]['id'], 'assignee': self.member.pk,
            'estimate': 3, 'labels': ['GIS'],
        }, format='json')
        self.assertEqual(task.status_code, 201, task.data)
        url = f"/api/pm/tasks/{task.data['id']}/"
        move = self.as_user(self.member).patch(url, {'column': columns[-1]['id']}, format='json')
        self.assertEqual(move.status_code, 200, move.data)
        self.assertEqual(move.data['status'], 'done')
        denied = self.client.patch(url, {'assignee': self.lead.pk}, format='json')
        self.assertEqual(denied.status_code, 403)
        comment = self.client.post('/api/pm/comments/', {'task': task.data['id'], 'body': 'Ready for review.'}, format='json')
        self.assertEqual(comment.status_code, 201, comment.data)
        summary = self.client.get('/api/pm/summary/').data
        self.assertEqual(summary['done'], 1)
        self.assertEqual(summary['tasks'], 1)
        self.assertEqual(self.as_user(self.outsider).get(url).status_code, 404)
        self.assertEqual(self.client.get('/api/pm/comments/').data, [])

    def test_cross_project_column_milestone_and_assignment_rejected(self):
        project = self.project()
        other = self.as_user(self.hr).post('/api/pm/projects/', {'name': 'Other', 'key': 'OTHER'}, format='json').data
        task = self.as_user(self.lead).post('/api/pm/tasks/', {
            'title': 'Mapping', 'column': project['boards'][0]['columns'][0]['id'],
        }, format='json').data
        url = f"/api/pm/tasks/{task['id']}/"
        self.assertEqual(self.client.patch(url, {'column': other['boards'][0]['columns'][0]['id']}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'assignee': self.outsider.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'start_date': '2030-10-10', 'due_date': '2030-10-01'}, format='json').status_code, 400)

    def test_employee_cannot_manage_board_or_edit_unassigned_task(self):
        project = self.project()
        task = self.as_user(self.lead).post('/api/pm/tasks/', {
            'title': 'Unassigned', 'column': project['boards'][0]['columns'][0]['id'],
        }, format='json').data
        self.assertEqual(self.as_user(self.member).patch(f"/api/pm/tasks/{task['id']}/", {'column': project['boards'][0]['columns'][1]['id']}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/pm/milestones/', {'project': project['id'], 'title': 'Launch', 'due_date': '2030-10-10'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f"/api/pm/boards/{project['boards'][0]['id']}/").status_code, 403)

    def test_links_require_safe_urls_and_membership_cannot_orphan_assignee(self):
        project = self.project()
        bad = self.as_user(self.lead).post('/api/pm/links/', {'project': project['id'], 'title': 'Docs', 'url': 'javascript:alert(1)'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.client.post('/api/pm/tasks/', {'title': 'Mapping', 'column': project['boards'][0]['columns'][0]['id'], 'assignee': self.member.pk}, format='json')
        self.assertEqual(self.client.patch(f"/api/pm/projects/{project['id']}/", {'members': []}, format='json').status_code, 400)

    def test_case_insensitive_project_keys_and_invalid_labels(self):
        project = self.project()
        duplicate = self.as_user(self.lead).post('/api/pm/projects/', {'name': 'Duplicate', 'key': 'water'}, format='json')
        self.assertEqual(duplicate.status_code, 400)
        for labels in ({'bad': 'shape'}, ['a' * 41], ['']):
            r = self.client.post('/api/pm/tasks/', {'title': 'Test', 'column': project['boards'][0]['columns'][0]['id'], 'labels': labels}, format='json')
            self.assertEqual(r.status_code, 400, r.data)

    def test_milestone_and_link_lifecycle_and_hr_visibility(self):
        project = self.project()
        milestone = self.as_user(self.lead).post('/api/pm/milestones/', {'project': project['id'], 'title': 'Launch', 'due_date': '2030-10-10'}, format='json')
        self.assertEqual(milestone.status_code, 201, milestone.data)
        link = self.client.post('/api/pm/links/', {'project': project['id'], 'title': 'Repository', 'kind': 'github', 'url': 'https://github.com/thimitech'}, format='json')
        self.assertEqual(link.status_code, 201, link.data)
        self.assertEqual(len(self.as_user(self.hr).get('/api/pm/projects/').data), 1)
        self.assertEqual(self.as_user(self.outsider).get('/api/pm/milestones/').data, [])
        self.assertEqual(self.client.get('/api/pm/links/').data, [])
        self.assertEqual(self.as_user(self.lead).patch(f"/api/pm/milestones/{milestone.data['id']}/", {'completed': True}, format='json').status_code, 200)
        self.assertEqual(self.client.delete(f"/api/pm/links/{link.data['id']}/").status_code, 204)

    def test_boards_and_columns_cannot_move_projects_or_delete_tasks(self):
        project = self.project()
        board = self.as_user(self.lead).post('/api/pm/boards/', {'project': project['id'], 'name': 'Field operations'}, format='json')
        self.assertEqual(board.status_code, 201, board.data)
        self.assertEqual(len(board.data['columns']), 4)
        column = board.data['columns'][0]
        task = self.client.post('/api/pm/tasks/', {'title': 'Field survey', 'column': column['id']}, format='json')
        self.assertEqual(task.status_code, 201)
        self.assertEqual(self.client.delete(f"/api/pm/columns/{column['id']}/").status_code, 400)
        other = self.client.post('/api/pm/projects/', {'name': 'Second', 'key': 'SECOND'}, format='json').data
        self.assertEqual(self.client.patch(f"/api/pm/boards/{board.data['id']}/", {'project': other['id']}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f"/api/pm/columns/{column['id']}/", {'board': other['boards'][0]['id']}, format='json').status_code, 400)
