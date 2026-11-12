from rest_framework.test import APITestCase

from apps.pm.models import Board, Column, Note, Project, Task
from apps.users.models import Clearance, User


def mk(name, role, **kw):
    return User.objects.create_user(username=name, email=f'{name}@x.test', password='x', role=role, first_name=name.title(), **kw)


class SearchTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.lead, cls.member, cls.outsider = mk('lila', 'manager'), mk('maya', 'employee'), mk('omar', 'employee')
        mk('gita', 'guest')
        cls.project = Project.objects.create(name='Trail atlas', key='trail', lead=cls.lead)
        cls.project.members.add(cls.member)
        column = Column.objects.create(board=Board.objects.create(project=cls.project, name='Main'), name='To do')
        cls.task = Task.objects.create(title='Survey the trailhead', column=column, created_by=cls.lead)
        Note.objects.create(project=cls.project, title='Trail pricing', body='x', author=cls.lead,
                            classification=Clearance.CONFIDENTIAL)

    def kinds(self, user, q):
        self.client.force_authenticate(user)
        r = self.client.get('/api/search/', {'q': q})
        self.assertEqual(r.status_code, 200)
        return sorted(h['kind'] for h in r.data)

    def test_members_find_project_and_tasks_but_not_notes_above_their_clearance(self):
        self.assertEqual(self.kinds(self.member, 'trail'), ['project', 'task'])
        self.lead.clearance = Clearance.CONFIDENTIAL
        self.lead.save()
        self.assertEqual(self.kinds(self.lead, 'trail'), ['note', 'project', 'task'])

    def test_outsiders_find_nothing_from_a_project_they_are_not_on(self):
        self.assertEqual(self.kinds(self.outsider, 'trail'), [])
        self.assertEqual(self.kinds(self.outsider, f'TRAIL-{self.task.pk}'), [])

    def test_task_key_people_and_short_queries(self):
        self.client.force_authenticate(self.member)
        hit = self.client.get('/api/search/', {'q': f'trail-{self.task.pk}'}).data
        self.assertEqual([(h['kind'], h['label']) for h in hit], [('task', 'Survey the trailhead')])
        self.assertEqual(self.kinds(self.member, 'lila'), ['person'])
        self.assertEqual(self.kinds(self.member, 'gita'), [])  # guests are not in the directory
        self.assertEqual(self.kinds(self.member, 't'), [])

    def test_requires_staff(self):
        self.assertEqual(self.client.get('/api/search/', {'q': 'trail'}).status_code, 401)
