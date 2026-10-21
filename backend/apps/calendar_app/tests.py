import datetime as dt

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.leave.models import LeaveRequest, LeaveType
from apps.org.models import Department, EmployeeProfile, Organization
from .models import CalendarEvent, Holiday
from .utils import is_working_day, working_days

User = get_user_model()
D = dt.date


def make_user(email, role, dept=None, **profile):
    u = User.objects.create_user(email=email, username=email.split('@')[0], password='x',
                                 role=role, first_name=email.split('@')[0].title())
    if role != 'guest':
        EmployeeProfile.objects.update_or_create(user=u, defaults={'department': dept, **profile})
    return User.objects.get(pk=u.pk)  # drop the stale .profile cached by the org signal


class WorkingDaysTests(TestCase):
    def setUp(self):
        org = Organization.load()
        org.weekend_days = [5]  # Saturday
        org.save()

    def test_weekend_policy(self):
        # 2026-10-05 is Monday; 05..11 has one Saturday (10th)
        days = working_days(D(2026, 10, 5), D(2026, 10, 11))
        self.assertEqual(len(days), 6)
        self.assertNotIn(D(2026, 10, 10), days)
        org = Organization.load()
        org.weekend_days = [5, 6]
        org.save()
        self.assertEqual(len(working_days(D(2026, 10, 5), D(2026, 10, 11))), 5)

    def test_mandatory_holiday_excluded_optional_kept(self):
        Holiday.objects.create(name='Mandatory', date=D(2026, 10, 6))
        Holiday.objects.create(name='Optional', date=D(2026, 10, 7), is_optional=True)
        days = working_days(D(2026, 10, 5), D(2026, 10, 9))
        self.assertNotIn(D(2026, 10, 6), days)
        self.assertIn(D(2026, 10, 7), days)
        self.assertFalse(is_working_day(D(2026, 10, 6)))
        self.assertTrue(is_working_day(D(2026, 10, 7)))
        self.assertFalse(is_working_day(D(2026, 10, 10)))

    def test_end_before_start(self):
        self.assertEqual(working_days(D(2026, 10, 9), D(2026, 10, 5)), [])


class Base(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.eng = Department.objects.create(name='Engineering')
        cls.gis = Department.objects.create(name='GIS')
        cls.hr = make_user('hr@t.com', 'hr_admin')
        cls.mgr = make_user('mgr@t.com', 'manager', cls.eng, date_of_birth=D(1990, 10, 20), join_date=D(2020, 10, 22))
        cls.eng.manager = cls.mgr
        cls.eng.save()
        cls.sita = make_user('sita@t.com', 'employee', cls.eng, date_of_birth=D(1995, 10, 18), join_date=D(2026, 10, 19))
        cls.maya = make_user('maya@t.com', 'employee', cls.gis)
        cls.guest = make_user('guest@t.com', 'guest')

    def as_(self, user):
        self.client.force_authenticate(user)


class HolidayApiTests(Base):
    def test_list_by_year_and_permissions(self):
        Holiday.objects.create(name='A', date=D(2026, 1, 1))
        Holiday.objects.create(name='B', date=D(2027, 1, 1))
        self.as_(self.sita)
        r = self.client.get('/api/calendar/holidays/?year=2027')
        self.assertEqual(r.status_code, 200)
        self.assertEqual([h['name'] for h in r.data], ['B'])
        self.assertEqual(self.client.get('/api/calendar/holidays/?year=abc').status_code, 400)
        for bad in ('0', '-5', '10000'):  # int() accepts these; date__year would 500
            self.assertEqual(self.client.get(f'/api/calendar/holidays/?year={bad}').status_code, 400, bad)
        self.assertEqual(self.client.post('/api/calendar/holidays/', {'name': 'X', 'date': '2026-05-01'}).status_code, 403)
        self.as_(self.guest)
        self.assertEqual(self.client.get('/api/calendar/holidays/').status_code, 403)
        self.as_(self.hr)
        self.assertEqual(self.client.post('/api/calendar/holidays/', {'name': 'X', 'date': '2026-05-01'}).status_code, 201)

    def test_bulk_dedupes_and_reports(self):
        Holiday.objects.create(name='Existing', date=D(2026, 4, 14))
        payload = [
            {'name': 'New Year', 'date': '2026-04-14'},  # exists
            {'name': 'Labour Day', 'date': '2026-05-01'},
            {'name': 'Labour Day dup', 'date': '2026-05-01'},  # dup inside payload
            {'name': 'Opt', 'date': '2026-06-01', 'is_optional': True},
        ]
        self.as_(self.mgr)
        self.assertEqual(self.client.post('/api/calendar/holidays/bulk/', payload, format='json').status_code, 403)
        self.as_(self.hr)
        r = self.client.post('/api/calendar/holidays/bulk/', payload, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual([h['name'] for h in r.data['created']], ['Labour Day', 'Opt'])
        self.assertTrue(all(h['id'] for h in r.data['created']))
        self.assertEqual([s['date'] for s in r.data['skipped']], ['2026-04-14', '2026-05-01'])
        self.assertEqual(Holiday.objects.count(), 3)
        self.assertTrue(Holiday.objects.get(date=D(2026, 6, 1)).is_optional)

    def test_bulk_validation(self):
        self.as_(self.hr)
        self.assertEqual(self.client.post('/api/calendar/holidays/bulk/', [], format='json').status_code, 400)
        r = self.client.post('/api/calendar/holidays/bulk/', [{'name': 'Bad', 'date': 'nope'}], format='json')
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Holiday.objects.count(), 0)


class EventVisibilityTests(Base):
    RANGE = '?start=2026-10-01&end=2026-10-31'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        mk = lambda title, aud, by, dept=None: CalendarEvent.objects.create(  # noqa: E731
            title=title, audience=aud, department=dept, created_by=by,
            start=dt.datetime(2026, 10, 10, 10, tzinfo=dt.timezone.utc),
            end=dt.datetime(2026, 10, 10, 11, tzinfo=dt.timezone.utc))
        cls.org_ev = mk('org', 'organization', cls.hr)
        cls.eng_ev = mk('eng', 'department', cls.mgr, cls.eng)
        cls.gis_ev = mk('gis', 'department', cls.hr, cls.gis)
        cls.priv = mk('priv', 'private', cls.sita)
        cls.priv_inv = mk('priv-inv', 'private', cls.maya)
        cls.priv_inv.attendees.add(cls.sita)
        cls.priv_other = mk('priv-other', 'private', cls.maya)

    def titles(self, user):
        self.as_(user)
        r = self.client.get('/api/calendar/events/' + self.RANGE)
        self.assertEqual(r.status_code, 200, r.data)
        return {e['title'] for e in r.data}

    def test_matrix(self):
        self.assertEqual(self.titles(self.sita), {'org', 'eng', 'priv', 'priv-inv'})
        self.assertEqual(self.titles(self.maya), {'org', 'gis', 'priv-inv', 'priv-other'})
        self.assertEqual(self.titles(self.mgr), {'org', 'eng'})
        self.assertEqual(self.titles(self.hr), {'org', 'eng', 'gis', 'priv', 'priv-inv', 'priv-other'})

    def test_hidden_event_detail_404(self):
        self.as_(self.sita)
        self.assertEqual(self.client.get(f'/api/calendar/events/{self.priv_other.pk}/').status_code, 404)

    def test_range_required_and_capped(self):
        self.as_(self.sita)
        self.assertEqual(self.client.get('/api/calendar/events/').status_code, 400)
        self.assertEqual(self.client.get('/api/calendar/events/?start=2026-01-01&end=2026-06-01').status_code, 400)
        self.assertEqual(self.client.get('/api/calendar/events/?start=2026-10-31&end=2026-10-01').status_code, 400)
        self.assertEqual(self.titles(self.sita) & {'org'}, {'org'})
        r = self.client.get('/api/calendar/events/?start=2026-11-01&end=2026-11-30')
        self.assertEqual(r.data, [])

    def test_create_rules(self):
        base = {'title': 'T', 'start': '2026-10-12T10:00:00+05:45', 'end': '2026-10-12T11:00:00+05:45'}
        self.as_(self.sita)
        r = self.client.post('/api/calendar/events/', {**base, 'audience': 'private', 'attendees': [self.maya.pk]}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['created_by']['id'], self.sita.pk)
        self.assertTrue(r.data['can_edit'])
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'organization'}, format='json').status_code, 403)
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'department', 'department': self.eng.pk}, format='json').status_code, 403)
        # guests cannot be invited
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'private', 'attendees': [self.guest.pk]}, format='json').status_code, 400)

        self.as_(self.mgr)
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'department', 'department': self.eng.pk}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'department', 'department': self.gis.pk}, format='json').status_code, 403)

        self.as_(self.hr)
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'organization'}, format='json').status_code, 201)
        self.assertEqual(self.client.post('/api/calendar/events/', {**base, 'audience': 'department', 'department': self.gis.pk}, format='json').status_code, 201)

    def test_validation(self):
        self.as_(self.hr)
        r = self.client.post('/api/calendar/events/', {'title': 'T', 'start': '2026-10-12T11:00:00Z', 'end': '2026-10-12T10:00:00Z'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('end', r.data)
        r = self.client.post('/api/calendar/events/', {'title': 'T', 'audience': 'department', 'start': '2026-10-12T10:00:00Z', 'end': '2026-10-12T11:00:00Z'}, format='json')
        self.assertIn('department', r.data)
        r = self.client.post('/api/calendar/events/', {'title': 'T', 'audience': 'private', 'department': self.eng.pk, 'start': '2026-10-12T10:00:00Z', 'end': '2026-10-12T11:00:00Z'}, format='json')
        self.assertIn('department', r.data)

    def test_update_delete_creator_or_hr(self):
        self.as_(self.sita)  # can see the invite but did not create it
        self.assertEqual(self.client.patch(f'/api/calendar/events/{self.priv_inv.pk}/', {'title': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'/api/calendar/events/{self.org_ev.pk}/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/calendar/events/{self.priv.pk}/', {'title': 'mine'}, format='json').status_code, 200)
        self.as_(self.hr)
        self.assertEqual(self.client.delete(f'/api/calendar/events/{self.priv_inv.pk}/').status_code, 204)
        self.as_(self.sita)
        self.assertEqual(self.client.delete(f'/api/calendar/events/{self.priv.pk}/').status_code, 204)

    def test_creator_can_edit_after_losing_department(self):
        self.eng.manager = self.hr
        self.eng.save()
        self.as_(self.mgr)
        url = f'/api/calendar/events/{self.eng_ev.pk}/'
        self.assertTrue(self.client.get(url).data['can_edit'])
        self.assertEqual(self.client.patch(url, {'title': 'typo fixed'}, format='json').status_code, 200)
        # full-form save with unchanged scope is fine too
        r = self.client.patch(url, {'title': 'again', 'audience': 'department', 'department': self.eng.pk}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        # but changing scope is still role-checked
        self.assertEqual(self.client.patch(url, {'department': self.gis.pk}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(url, {'audience': 'organization'}, format='json').status_code, 403)


class FeedTests(Base):
    URL = '/api/calendar/feed/?start=2026-10-15&end=2026-10-31'

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Holiday.objects.create(name='Dashain', date=D(2026, 10, 17))
        Holiday.objects.create(name='Outside', date=D(2026, 12, 1))
        CalendarEvent.objects.create(title='All hands', audience='organization', created_by=cls.hr,
                                     start=dt.datetime(2026, 10, 20, 5, tzinfo=dt.timezone.utc),
                                     end=dt.datetime(2026, 10, 20, 6, tzinfo=dt.timezone.utc))
        CalendarEvent.objects.create(title='Maya private', audience='private', created_by=cls.maya,
                                     start=dt.datetime(2026, 10, 20, 5, tzinfo=dt.timezone.utc),
                                     end=dt.datetime(2026, 10, 20, 6, tzinfo=dt.timezone.utc))
        lt = LeaveType.objects.create(name='Annual', code='annual', color='#7a6a52')
        mk = lambda u, s='approved': LeaveRequest.objects.create(  # noqa: E731
            user=u, leave_type=lt, start_date=D(2026, 10, 25), end_date=D(2026, 10, 27), reason='secret', status=s)
        cls.sita_leave = mk(cls.sita)
        mk(cls.maya)
        mk(cls.sita, 'pending')

    def feed(self, user, url=None):
        self.as_(user)
        r = self.client.get(url or self.URL)
        self.assertEqual(r.status_code, 200, getattr(r, 'data', None))
        return r.data

    def kinds(self, data, kind):
        return [i for i in data['items'] if i['kind'] == kind]

    def test_envelope_and_contents(self):
        data = self.feed(self.sita)
        self.assertEqual(data['weekend_days'], [5])
        self.assertEqual(set(data), {'start', 'end', 'weekend_days', 'items'})
        self.assertEqual([h['title'] for h in self.kinds(data, 'holiday')], ['Dashain'])
        self.assertEqual([e['title'] for e in self.kinds(data, 'event')], ['All hands'])
        leaves = self.kinds(data, 'leave')
        self.assertEqual([lv['meta']['user']['id'] for lv in leaves], [self.sita.pk])  # approved, own dept only
        self.assertNotIn('reason', leaves[0]['meta'])
        for i in data['items']:
            self.assertEqual(set(i), {'kind', 'id', 'title', 'start', 'end', 'all_day', 'color', 'meta'})
        starts = [i['start'][:10] for i in data['items']]
        self.assertEqual(starts, sorted(starts))
        self.assertNotIn('weekend', {i['kind'] for i in data['items']})

    def test_leave_visibility(self):
        self.assertEqual(len(self.kinds(self.feed(self.mgr), 'leave')), 1)  # team only
        self.assertEqual([lv['meta']['user']['id'] for lv in self.kinds(self.feed(self.maya), 'leave')], [self.maya.pk])
        self.assertEqual(len(self.kinds(self.feed(self.hr), 'leave')), 2)

    def test_birthdays_and_anniversaries_hide_year(self):
        data = self.feed(self.maya)
        bdays = self.kinds(data, 'birthday')
        self.assertEqual({b['meta']['user']['id'] for b in bdays}, {self.mgr.pk, self.sita.pk})
        sita = next(b for b in bdays if b['id'] == self.sita.pk)
        self.assertEqual(sita['start'], '2026-10-18')
        self.assertEqual(sita['meta'], {'user': {'id': self.sita.pk, 'full_name': self.sita.full_name}, 'month': 10, 'day': 18})
        self.assertNotIn('1995', str(data))
        self.assertNotIn('1990', str(data))
        ann = self.kinds(data, 'work_anniversary')
        self.assertEqual([(a['id'], a['meta']['years']) for a in ann], [(self.mgr.pk, 6)])  # sita joined this year: none

    def test_birthday_across_year_boundary(self):
        EmployeeProfile.objects.filter(user=self.sita).update(date_of_birth=D(1996, 1, 3))
        data = self.feed(self.sita, '/api/calendar/feed/?start=2026-12-20&end=2027-01-10')
        self.assertEqual([b['start'] for b in self.kinds(data, 'birthday')], ['2027-01-03'])

    def test_range_cap_and_auth(self):
        self.as_(self.sita)
        self.assertEqual(self.client.get('/api/calendar/feed/').status_code, 400)
        r = self.client.get('/api/calendar/feed/?start=2026-01-01&end=2026-04-15')
        self.assertEqual(r.status_code, 400)
        self.assertIn('end', r.data)
        self.assertEqual(self.client.get('/api/calendar/feed/?start=2026-01-01&end=2026-04-11').status_code, 200)
        self.assertEqual(self.client.get('/api/calendar/feed/?start=bad&end=2026-04-11').status_code, 400)
        self.as_(self.guest)
        self.assertEqual(self.client.get(self.URL).status_code, 403)
