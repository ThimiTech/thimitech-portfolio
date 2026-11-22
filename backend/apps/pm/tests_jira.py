"""Workspace flow: issue history, ranking, the project activity feed and comment notices."""
from rest_framework.test import APITestCase
from apps.notifications.models import Notification
from apps.users.models import User
from .models import Task, TaskActivity


class WorkspaceFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lead = User.objects.create_user(username='lead', email='lead@ws.test', password='x', role='manager', first_name='Lena')
        cls.member = User.objects.create_user(username='member', email='member@ws.test', password='x', role='employee', first_name='Milo')
        cls.outsider = User.objects.create_user(username='out', email='out@ws.test', password='x', role='employee')

    def setUp(self):
        self.client.force_authenticate(self.lead)
        self.project = self.client.post('/api/pm/projects/', {'name': 'Spring', 'key': 'SPR', 'members': [self.member.pk]}, format='json').data
        self.cols = {c['status']: c['id'] for c in self.project['boards'][0]['columns']}

    def item(self, title, type='task', **extra):
        r = self.client.post('/api/pm/tasks/', {'title': title, 'type': type, 'column': self.cols['backlog'], **extra}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        return r.data

    def test_new_items_go_to_the_bottom_and_carry_reporter(self):
        a, b = self.item('First'), self.item('Second')
        self.assertLess(a['position'], b['position'])
        self.assertEqual((b['created_by_name'], b['comment_count']), ('Lena', 0))

    def test_history_records_changes_as_display_text(self):
        epic = self.item('Layers', 'epic')
        t = self.item('Style editor', 'story')
        self.client.patch(f"/api/pm/tasks/{t['id']}/", {'column': self.cols['active'], 'assignee': self.member.pk, 'parent': epic['id'],
                                                         'description': 'long text', 'labels': ['gis']}, format='json')
        self.client.patch(f"/api/pm/tasks/{t['id']}/", {'title': 'Style editor'}, format='json')  # no change, no row
        rows = self.client.get(f"/api/pm/tasks/{t['id']}/activity/").data
        changes = {r['field']: (r['old'], r['new']) for r in rows}
        self.assertEqual(changes['column'], ('Backlog', 'In progress'))
        self.assertEqual(changes['assignee'], ('', 'Milo'))
        self.assertEqual(changes['parent'], ('', f"SPR-{epic['id']} Layers"))
        self.assertEqual(changes['description'], ('', ''))
        self.assertEqual(changes['labels'], ('', 'gis'))
        self.assertEqual(changes['created'], ('', 'Story'))
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]['actor_name'], 'Lena')
        # the assignee moving their own card is recorded too
        self.client.force_authenticate(self.member)
        self.client.patch(f"/api/pm/tasks/{t['id']}/", {'column': self.cols['done']}, format='json')
        self.assertEqual(TaskActivity.objects.filter(task_id=t['id'], field='column').first().new, 'Done')

    def test_reorder_moves_a_subset_and_keeps_the_rest(self):
        a, b, c, d = (self.item(n) for n in 'abcd')
        Task.objects.update(position=0)  # legacy data: every rank equal
        r = self.client.post('/api/pm/tasks/reorder/', {'project': self.project['id'], 'ids': [d['id'], b['id']]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        order = list(Task.objects.order_by('position', 'id').values_list('title', flat=True))
        self.assertEqual(order, ['a', 'd', 'c', 'b'])  # b and d swap slots; a and c stay put
        bad = self.client.post('/api/pm/tasks/reorder/', {'project': self.project['id'], 'ids': [a['id'], 99999]}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.post('/api/pm/tasks/reorder/', {'project': self.project['id'], 'ids': [a['id']]}, format='json').status_code, 403)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.post('/api/pm/tasks/reorder/', {'project': self.project['id'], 'ids': [a['id']]}, format='json').status_code, 404)

    def test_activity_feed_is_project_scoped(self):
        t = self.item('Feed me')
        self.client.patch(f"/api/pm/tasks/{t['id']}/", {'priority': 'high'}, format='json')
        feed = self.client.get('/api/pm/activity/', {'project': self.project['id']}).data
        self.assertEqual([(r['field'], r['task_key']) for r in feed][:2], [('priority', f"SPR-{t['id']}"), ('created', f"SPR-{t['id']}")])
        self.assertEqual(feed[0]['new'], 'High')
        self.assertEqual(self.client.get('/api/pm/activity/').status_code, 400)
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get('/api/pm/activity/', {'project': self.project['id']}).data, [])

    def test_comments_notify_assignee_and_reporter_and_count(self):
        t = self.item('Discuss', assignee=self.member.pk)
        self.client.force_authenticate(self.member)
        self.client.post('/api/pm/comments/', {'task': t['id'], 'body': 'Question about scope'}, format='json')
        n = Notification.objects.get(recipient=self.lead, kind='task_comment')
        self.assertEqual(n.link, f"/app/projects/{self.project['id']}/work?issue=SPR-{t['id']}")
        self.assertFalse(Notification.objects.filter(recipient=self.member, kind='task_comment').exists())  # not to the author
        self.assertEqual(self.client.get(f"/api/pm/tasks/{t['id']}/").data['comment_count'], 1)
