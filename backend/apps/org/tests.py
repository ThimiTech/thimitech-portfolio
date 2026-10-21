import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework.test import APITestCase

from .models import Department, EmployeeProfile, Organization

User = get_user_model()
PEOPLE = '/api/org/people/'
DEPTS = '/api/org/departments/'
ORG = '/api/org/organization/'


def png_bytes(size=(4, 4)):
    buf = io.BytesIO()
    Image.new('RGB', size, 'red').save(buf, 'PNG')
    return buf.getvalue()


MEDIA = tempfile.mkdtemp(prefix='thimi_org_test_')


@override_settings(MEDIA_ROOT=MEDIA)
class OrgBase(APITestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    @classmethod
    def setUpTestData(cls):
        def mk(email, role, **kw):
            return User.objects.create_user(username=email.split('@')[0], email=email, password='x-Pass-123',
                                            role=role, first_name=email.split('@')[0].title(), **kw)

        cls.sup = mk('sup@t.com', 'super_admin')
        cls.hr = mk('hr@t.com', 'hr_admin')
        cls.hr2 = mk('hr2@t.com', 'hr_admin')
        cls.mgr = mk('mgr@t.com', 'manager')
        cls.emp = mk('emp@t.com', 'employee')
        cls.other = mk('other@t.com', 'employee')
        cls.guest = mk('guest@t.com', 'guest')
        cls.eng = Department.objects.create(name='Engineering', manager=cls.mgr)
        cls.ops = Department.objects.create(name='Operations')
        for u, d in ((cls.mgr, cls.eng), (cls.emp, cls.eng), (cls.other, cls.ops)):
            EmployeeProfile.objects.filter(user=u).update(
                department=d, date_of_birth='1995-01-01', address='Thimi', emergency_contact_name='Kin',
                phone='98000', designation='Engineer',
            )

    def as_(self, user):
        self.client.force_authenticate(user)
        return self.client


class SignalTests(OrgBase):
    def test_staff_get_profile_guest_does_not(self):
        self.assertTrue(EmployeeProfile.objects.filter(user=self.emp).exists())
        self.assertFalse(EmployeeProfile.objects.filter(user=self.guest).exists())

    def test_promoting_guest_creates_profile(self):
        self.guest.role = 'employee'
        self.guest.save()
        self.assertTrue(EmployeeProfile.objects.filter(user=self.guest).exists())

    def test_resave_does_not_duplicate(self):
        self.emp.save()
        self.assertEqual(EmployeeProfile.objects.filter(user=self.emp).count(), 1)


class OrganizationTests(OrgBase):
    def test_permission_matrix(self):
        self.assertEqual(self.as_(self.guest).get(ORG).status_code, 403)
        self.assertEqual(self.as_(self.emp).get(ORG).status_code, 200)
        self.assertEqual(self.as_(self.mgr).patch(ORG, {'tagline': 'x'}).status_code, 403)
        r = self.as_(self.hr).patch(ORG, {'tagline': 'Maps'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['tagline'], 'Maps')

    def test_work_policy_super_admin_only(self):
        self.assertEqual(self.as_(self.hr).patch(ORG, {'late_grace_minutes': 5}).status_code, 403)
        r = self.as_(self.sup).patch(ORG, {'late_grace_minutes': 5, 'weekend_days': [6, 5]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(Organization.load().weekend_days, [5, 6])

    def test_weekend_validation(self):
        c = self.as_(self.sup)
        self.assertEqual(c.patch(ORG, {'weekend_days': [5, 5]}, format='json').status_code, 400)
        self.assertEqual(c.patch(ORG, {'weekend_days': [7]}, format='json').status_code, 400)
        self.assertEqual(c.patch(ORG, {'weekend_days': list(range(7))}, format='json').status_code, 400)
        self.assertEqual(c.patch(ORG, {'work_start': '18:00', 'work_end': '09:00'}).status_code, 400)

    def test_logo_upload(self):
        logo = SimpleUploadedFile('l.png', png_bytes(), content_type='image/png')
        r = self.as_(self.hr).patch(ORG, {'logo': logo}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('/media/org/', r.data['logo'])


class DepartmentTests(OrgBase):
    def test_permission_matrix(self):
        self.assertEqual(self.as_(self.guest).get(DEPTS).status_code, 403)
        r = self.as_(self.emp).get(DEPTS)
        self.assertEqual(r.status_code, 200)
        eng = next(d for d in r.data if d['name'] == 'Engineering')
        self.assertEqual(eng['manager'], {'id': self.mgr.id, 'full_name': self.mgr.full_name})
        self.assertEqual(eng['member_count'], 2)
        for u in (self.emp, self.mgr):
            self.assertEqual(self.as_(u).post(DEPTS, {'name': 'X'}).status_code, 403)
        r = self.as_(self.hr).post(DEPTS, {'name': 'GIS', 'parent': self.eng.id, 'manager_id': self.emp.id})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['parent'], self.eng.id)

    def test_guest_cannot_be_manager(self):
        r = self.as_(self.hr).post(DEPTS, {'name': 'X', 'manager_id': self.guest.id})
        self.assertEqual(r.status_code, 400)

    def test_cycle_prevention(self):
        c = self.as_(self.hr)
        child = Department.objects.create(name='Child', parent=self.eng)
        grandchild = Department.objects.create(name='Grandchild', parent=child)
        self.assertEqual(c.patch(f'{DEPTS}{self.eng.id}/', {'parent': self.eng.id}).status_code, 400)
        r = c.patch(f'{DEPTS}{self.eng.id}/', {'parent': grandchild.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn('parent', r.data)
        self.assertEqual(c.patch(f'{DEPTS}{grandchild.id}/', {'parent': self.ops.id}).status_code, 200)

    def test_existing_loop_does_not_hang_and_still_renders(self):
        a = Department.objects.create(name='LoopA')
        b = Department.objects.create(name='LoopB', parent=a)
        Department.objects.filter(pk=a.pk).update(parent=b)  # raw ORM loop A->B->A
        c = self.as_(self.hr)
        r = c.post(DEPTS, {'name': 'LoopC', 'parent': a.id})
        self.assertEqual(r.status_code, 400)
        self.assertIn('parent', r.data)
        self.assertEqual(c.patch(f'{DEPTS}{self.ops.id}/', {'parent': b.id}).status_code, 400)
        names = {d['name'] for d in self.as_(self.emp).get('/api/org/structure/').data['departments']}
        self.assertTrue({'LoopA', 'LoopB'} <= names)

    def test_model_clean_blocks_cycles(self):  # covers /admin (ModelForm -> full_clean)
        from django.core.exceptions import ValidationError
        child = Department.objects.create(name='Child', parent=self.eng)
        self.eng.parent = child
        with self.assertRaises(ValidationError):
            self.eng.full_clean()

    def test_inactive_or_demoted_manager_is_cleared(self):
        self.as_(self.hr).post(f'{PEOPLE}{self.mgr.id}/deactivate/')
        self.eng.refresh_from_db()
        self.assertIsNone(self.eng.manager)
        self.assertIsNone(self.as_(self.emp).get(f'{PEOPLE}me/').data['manager'])
        self.ops.manager = self.other
        self.ops.save()
        r = self.as_(self.hr).patch(f'{PEOPLE}{self.other.id}/', {'role': 'guest'})
        self.assertEqual(r.status_code, 200, r.data)
        self.ops.refresh_from_db()
        self.assertIsNone(self.ops.manager)

    def test_structure(self):
        Department.objects.create(name='Frontend', parent=self.eng)
        r = self.as_(self.emp).get('/api/org/structure/')
        self.assertEqual(r.status_code, 200)
        eng = next(d for d in r.data['departments'] if d['name'] == 'Engineering')
        self.assertEqual(eng['manager']['id'], self.mgr.id)
        self.assertEqual({m['id'] for m in eng['members']}, {self.mgr.id, self.emp.id})
        self.assertEqual([c['name'] for c in eng['children']], ['Frontend'])
        unassigned = {u['id'] for u in r.data['unassigned']}
        self.assertIn(self.hr.id, unassigned)
        self.assertNotIn(self.guest.id, unassigned)


class PeopleReadTests(OrgBase):
    def test_guest_blocked(self):
        self.assertEqual(self.as_(self.guest).get(PEOPLE).status_code, 403)

    def test_directory_hides_guests_and_sensitive_fields(self):
        r = self.as_(self.emp).get(PEOPLE)
        self.assertEqual(r.status_code, 200)
        ids = {p['id'] for p in r.data}
        self.assertNotIn(self.guest.id, ids)
        other = next(p for p in r.data if p['id'] == self.other.id)
        for f in ('date_of_birth', 'address', 'emergency_contact_name', 'emergency_contact_phone'):
            self.assertNotIn(f, other)
        self.assertEqual(other['visibility'], 'directory')
        self.assertEqual(other['phone'], '98000')

    def test_include_guests_hr_only(self):
        ids = {p['id'] for p in self.as_(self.emp).get(PEOPLE, {'include_guests': 1}).data}
        self.assertNotIn(self.guest.id, ids)
        ids = {p['id'] for p in self.as_(self.hr).get(PEOPLE, {'include_guests': 1}).data}
        self.assertIn(self.guest.id, ids)

    def test_filters(self):
        c = self.as_(self.emp)
        self.assertEqual({p['id'] for p in c.get(PEOPLE, {'department': self.eng.id}).data}, {self.mgr.id, self.emp.id})
        self.assertEqual([p['id'] for p in c.get(PEOPLE, {'role': 'manager'}).data], [self.mgr.id])
        self.assertEqual([p['id'] for p in c.get(PEOPLE, {'search': 'other@'}).data], [self.other.id])
        self.assertEqual(c.get(PEOPLE, {'role': 'boss'}).status_code, 400)

    def test_detail_visibility(self):
        url = f'{PEOPLE}{self.emp.id}/'
        self.assertNotIn('date_of_birth', self.as_(self.other).get(url).data)  # peer
        for viewer in (self.emp, self.mgr, self.hr, self.sup):  # self, manager, HR, super
            r = self.as_(viewer).get(url)
            self.assertEqual(r.data['date_of_birth'], '1995-01-01', viewer.email)
            self.assertEqual(r.data['visibility'], 'full')
        # manager of Engineering is not the manager of Operations staff
        self.assertNotIn('address', self.as_(self.mgr).get(f'{PEOPLE}{self.other.id}/').data)

    def test_manager_never_sees_hr_private_fields(self):
        EmployeeProfile.objects.filter(user=self.hr).update(department=self.eng, address='Secret')
        r = self.as_(self.mgr).get(f'{PEOPLE}{self.hr.id}/')
        self.assertEqual(r.data['visibility'], 'directory')
        self.assertNotIn('address', r.data)

    def test_me(self):
        r = self.as_(self.emp).get(f'{PEOPLE}me/')
        self.assertEqual(r.data['id'], self.emp.id)
        self.assertEqual(r.data['manager'], {'id': self.mgr.id, 'full_name': self.mgr.full_name})

    def test_inactive_hidden_from_employees(self):
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.as_(self.emp).get(f'{PEOPLE}{self.other.id}/').status_code, 404)
        self.assertEqual(self.as_(self.hr).get(f'{PEOPLE}{self.other.id}/').status_code, 200)


class PeopleWriteTests(OrgBase):
    def test_self_edit_contact_fields(self):
        r = self.as_(self.emp).patch(f'{PEOPLE}me/', {'phone': '111', 'skills': ['GIS', ' QGIS '], 'first_name': 'E'},
                                     format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['skills'], ['GIS', 'QGIS'])
        self.emp.profile.refresh_from_db()
        self.assertEqual(self.emp.profile.phone, '111')

    def test_self_cannot_edit_hr_fields(self):
        c = self.as_(self.emp)
        for payload in ({'designation': 'CTO'}, {'department_id': self.ops.id}, {'join_date': '2020-01-01'},
                        {'employee_code': 'X'}, {'employment_type': 'intern'}, {'email': 'n@t.com'}):
            r = c.patch(f'{PEOPLE}{self.emp.id}/', payload, format='json')
            self.assertEqual(r.status_code, 403, payload)

    def test_cannot_edit_others(self):
        r = self.as_(self.mgr).patch(f'{PEOPLE}{self.emp.id}/', {'phone': '1'})
        self.assertEqual(r.status_code, 403)

    def test_hr_edits_everything(self):
        r = self.as_(self.hr).patch(f'{PEOPLE}{self.emp.id}/', {
            'designation': 'Lead', 'department_id': self.ops.id, 'join_date': '2021-02-03', 'role': 'manager',
        }, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['department'], {'id': self.ops.id, 'name': 'Operations'})
        self.assertEqual(r.data['role'], 'manager')

    def test_role_escalation(self):
        url = f'{PEOPLE}{self.emp.id}/'
        self.assertEqual(self.as_(self.emp).patch(f'{PEOPLE}me/', {'role': 'super_admin'}).status_code, 403)
        self.assertEqual(self.as_(self.mgr).patch(url, {'role': 'manager'}).status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(url, {'role': 'hr_admin'}).status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(url, {'role': 'super_admin'}).status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(f'{PEOPLE}{self.hr2.id}/', {'role': 'employee'}).status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(f'{PEOPLE}me/', {'role': 'super_admin'}).status_code, 403)
        self.assertEqual(self.as_(self.sup).patch(f'{PEOPLE}me/', {'role': 'employee'}).status_code, 403)
        self.assertEqual(self.as_(self.sup).patch(url, {'role': 'hr_admin'}).status_code, 200)
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.role, 'hr_admin')

    def test_unchanged_own_role_is_fine(self):
        self.assertEqual(self.as_(self.hr).patch(f'{PEOPLE}me/', {'role': 'hr_admin', 'phone': '2'}).status_code, 200)
        self.assertEqual(self.as_(self.emp).patch(f'{PEOPLE}me/', {'role': 'employee', 'phone': '2'}).status_code, 200)

    def test_no_email_oracle_for_non_hr(self):
        c = self.as_(self.emp)
        for email in ('guest@t.com', 'nobody-xyz@t.com'):  # existing vs unknown: same 403
            self.assertEqual(c.patch(f'{PEOPLE}me/', {'email': email}).status_code, 403, email)
            self.assertEqual(c.patch(f'{PEOPLE}{self.hr.id}/', {'email': email}).status_code, 403, email)

    def test_skills_deduped(self):
        r = self.as_(self.emp).patch(f'{PEOPLE}me/', {'skills': ['Django', ' Django', 'GIS']}, format='json')
        self.assertEqual(r.data['skills'], ['Django', 'GIS'])

    def test_hr_onboards_guest(self):
        r = self.as_(self.hr).patch(f'{PEOPLE}{self.guest.id}/', {'role': 'employee', 'department_id': self.eng.id},
                                    format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(EmployeeProfile.objects.get(user=self.guest).department, self.eng)

    def test_create_person(self):
        payload = {'email': 'New@T.com', 'first_name': 'Nima', 'last_name': 'L', 'password': 'Str0ng-Pass!9',
                   'department_id': self.eng.id, 'designation': 'Analyst', 'employment_type': 'intern',
                   'join_date': '2026-10-01'}
        self.assertEqual(self.as_(self.mgr).post(PEOPLE, payload, format='json').status_code, 403)
        r = self.as_(self.hr).post(PEOPLE, payload, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['role'], 'employee')
        self.assertNotIn('password', r.data)
        u = User.objects.get(email='new@t.com')
        self.assertTrue(u.check_password('Str0ng-Pass!9'))
        self.assertEqual(u.profile.designation, 'Analyst')
        # duplicate email, weak password, no password -> unusable
        self.assertEqual(self.as_(self.hr).post(PEOPLE, payload, format='json').status_code, 400)
        r = self.as_(self.hr).post(PEOPLE, {'email': 'w@t.com', 'password': '123'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('password', r.data)
        r = self.as_(self.hr).post(PEOPLE, {'email': 'np@t.com'}, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertFalse(User.objects.get(email='np@t.com').has_usable_password())

    def test_password_reset_and_change(self):
        url = f'{PEOPLE}{self.emp.id}/'
        new = {'password': 'N3w-Strong-Pass!'}
        # employees and managers cannot reset others; hr cannot reset an hr peer; nobody resets self via PATCH
        self.assertEqual(self.as_(self.mgr).patch(url, new, format='json').status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(f'{PEOPLE}{self.hr2.id}/', new, format='json').status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(f'{PEOPLE}me/', new, format='json').status_code, 400)
        self.assertEqual(self.as_(self.emp).patch(f'{PEOPLE}me/', new, format='json').status_code, 403)
        self.assertEqual(self.as_(self.hr).patch(url, {'password': '123'}, format='json').status_code, 400)
        r = self.as_(self.hr).patch(url, new, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.emp.refresh_from_db()
        self.assertTrue(self.emp.check_password('N3w-Strong-Pass!'))
        # self-service change needs the current password
        pw = f'{PEOPLE}me/password/'
        r = self.as_(self.emp).post(pw, {'current_password': 'wrong', 'new_password': 'An0ther-Pass!'}, format='json')
        self.assertEqual(r.status_code, 400)
        self.assertIn('current_password', r.data)
        r = self.as_(self.emp).post(pw, {'current_password': 'N3w-Strong-Pass!', 'new_password': 'short'}, format='json')
        self.assertIn('new_password', r.data)
        r = self.as_(self.emp).post(pw, {'current_password': 'N3w-Strong-Pass!', 'new_password': 'An0ther-Pass!'}, format='json')
        self.assertEqual(r.status_code, 204)
        self.emp.refresh_from_db()
        self.assertTrue(self.emp.check_password('An0ther-Pass!'))
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post(pw, {}, format='json').status_code, 401)

    def test_create_role_rules(self):
        r = self.as_(self.hr).post(PEOPLE, {'email': 'a@t.com', 'role': 'hr_admin'}, format='json')
        self.assertEqual(r.status_code, 403)
        r = self.as_(self.sup).post(PEOPLE, {'email': 'a@t.com', 'role': 'hr_admin'}, format='json')
        self.assertEqual(r.status_code, 201)

    def test_deactivate_reactivate(self):
        url = f'{PEOPLE}{self.emp.id}/'
        self.assertEqual(self.as_(self.mgr).post(f'{url}deactivate/').status_code, 403)
        r = self.as_(self.hr).post(f'{url}deactivate/')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data['is_active'])
        self.assertTrue(User.objects.filter(pk=self.emp.pk).exists())
        self.assertEqual(self.as_(self.hr).post(f'{url}reactivate/').data['is_active'], True)
        self.assertEqual(self.as_(self.hr).post(f'{PEOPLE}{self.hr.id}/deactivate/').status_code, 403)
        self.assertEqual(self.as_(self.hr).post(f'{PEOPLE}{self.sup.id}/deactivate/').status_code, 403)
        self.assertEqual(self.as_(self.hr).delete(url).status_code, 405)

    def test_photo_upload(self):
        ok = SimpleUploadedFile('p.png', png_bytes(), content_type='image/png')
        r = self.as_(self.emp).patch(f'{PEOPLE}me/', {'photo': ok}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('/media/profiles/', r.data['photo'])
        bad = SimpleUploadedFile('p.png', b'not an image', content_type='image/png')
        self.assertEqual(self.as_(self.emp).patch(f'{PEOPLE}me/', {'photo': bad}, format='multipart').status_code, 400)
        big = SimpleUploadedFile('b.png', png_bytes() + b'0' * (3 * 1024 * 1024), content_type='image/png')
        r = self.as_(self.emp).patch(f'{PEOPLE}me/', {'photo': big}, format='multipart')
        self.assertEqual(r.status_code, 400)
        self.assertIn('photo', r.data)

    def test_photo_polyglot_with_html_extension_rejected(self):
        # A valid image named .html would be served from /media as text/html (stored XSS on the app origin).
        evil = SimpleUploadedFile('x.html', png_bytes(), content_type='image/png')
        r = self.as_(self.emp).patch(f'{PEOPLE}me/', {'photo': evil}, format='multipart')
        self.assertEqual(r.status_code, 400)
        self.assertIn('photo', r.data)
