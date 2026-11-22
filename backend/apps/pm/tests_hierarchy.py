from rest_framework.test import APITestCase
from apps.users.models import User
from .models import Task

SHEET = '\n'.join([
    'Modules\tFeatures/ Epics\tStory\tWork Item/Task\tdescription\tStatus\tblockers\tAssign to\tdeadline',
    'Project Kick Off\tSprint Planning\t\t\t\tdone',
    '\tCI/CD pipeline\t\t\t\tin progress\tWaiting on server access\tmember@pm.test\t2026-12-15',
    'Dashboard\tInformation Panel\tNature of spring',
    '\t\tSpring Flow Regime\t\tReplace Nature of Spring\t\t\tNobody',
    'WRI\tDB Design\tWater Source Type Codes\tAutomated Water Source Code Generation\t\tblocked',
    '\t\t\t\t\t\t\t\t',
    '\t\t\t\tdetails without a title',
])


class HierarchyTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lead = User.objects.create_user(username='lead', email='lead@pm.test', password='x', role='manager')
        cls.member = User.objects.create_user(username='member', email='member@pm.test', password='x', role='employee')

    def setUp(self):
        self.client.force_authenticate(self.lead)
        self.project = self.client.post('/api/pm/projects/', {'name': 'Spring DSS', 'key': 'SDSS', 'members': [self.member.pk]}, format='json').data
        self.backlog = self.project['boards'][0]['columns'][0]['id']

    def item(self, title, type, **extra):
        r = self.client.post('/api/pm/tasks/', {'title': title, 'type': type, 'column': self.backlog, **extra}, format='json')
        return r

    def test_parent_must_rank_higher_and_children_constrain_type(self):
        epic = self.item('WMS layers', 'epic').data
        story = self.item('Style management', 'story', parent=epic['id']).data
        self.assertEqual(self.item('Bad', 'epic', parent=story['id']).status_code, 400)
        self.assertEqual(self.client.patch(f"/api/pm/tasks/{epic['id']}/", {'type': 'story'}, format='json').status_code, 400)
        task = self.item('Write model', 'task', parent=story['id'], blocked_by=[epic['id']]).data
        self.assertEqual(task['blocked_by'], [epic['id']])
        self.assertEqual(self.client.patch(f"/api/pm/tasks/{task['id']}/", {'blocked_by': [task['id']]}, format='json').status_code, 400)
        # containers do not count towards project progress
        self.assertEqual(self.client.get(f"/api/pm/projects/{self.project['id']}/").data['progress']['total'], 2)

    def test_import_builds_tree_and_is_idempotent(self):
        r = self.client.post('/api/pm/tasks/import/', {'project': self.project['id'], 'text': SHEET}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['created'], 11)
        self.assertEqual(len(r.data['warnings']), 2)  # unknown assignee + row with no title
        tasks = Task.objects.filter(column__board__project_id=self.project['id'])
        cicd = tasks.get(title='CI/CD pipeline')
        self.assertEqual((cicd.type, cicd.parent.title, cicd.column.status), ('epic', 'Project Kick Off', 'active'))
        self.assertEqual((cicd.assignee, str(cicd.due_date), cicd.blocker), (self.member, '2026-12-15', 'Waiting on server access'))
        regime = tasks.get(title='Spring Flow Regime')
        self.assertEqual((regime.type, regime.parent.title, regime.description), ('story', 'Information Panel', 'Replace Nature of Spring'))
        leaf = tasks.get(title='Automated Water Source Code Generation')
        self.assertEqual((leaf.type, leaf.parent.parent.parent.title, leaf.blocker), ('task', 'WRI', 'Blocked'))
        again = self.client.post('/api/pm/tasks/import/', {'project': self.project['id'], 'text': SHEET}, format='json').data
        self.assertEqual((again['created'], again['updated']), (0, 0))
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.post('/api/pm/tasks/import/', {'project': self.project['id'], 'text': SHEET}, format='json').status_code, 403)
