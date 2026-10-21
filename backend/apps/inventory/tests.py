from rest_framework.test import APITestCase
from apps.users.models import User


class InventoryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hr = User.objects.create_user(username='assetshr', email='hr@assets.test', password='x', role='hr_admin')
        cls.emp = User.objects.create_user(username='assetsemp', email='emp@assets.test', password='x', role='employee')
        cls.guest = User.objects.create_user(username='assetsguest', email='guest@assets.test', password='x', role='guest')

    def setUp(self):
        self.client.force_authenticate(self.hr)

    def asset(self):
        category = self.client.post('/api/inventory/categories/', {'name': 'Survey equipment'}, format='json')
        self.assertEqual(category.status_code, 201, getattr(category, 'data', None))
        asset = self.client.post('/api/inventory/assets/', {'tag': 'TT-001', 'name': 'Survey receiver', 'category': category.data['id']}, format='json')
        self.assertEqual(asset.status_code, 201, asset.data)
        return asset.data

    def test_assign_return_and_history(self):
        asset = self.asset()
        r = self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.emp.pk}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.get(f"/api/inventory/assets/{asset['id']}/").data['status'], 'assigned')
        self.assertEqual(self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.hr.pk}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f"/api/inventory/assets/{asset['id']}/", {'status': 'available'}, format='json').status_code, 400)
        url = f"/api/inventory/assignments/{r.data['id']}/return/"
        self.assertEqual(self.client.post(url, {'condition': 'maintenance', 'return_note': 'Inspect antenna'}, format='json').status_code, 200)
        self.assertEqual(self.client.post(url, {}, format='json').status_code, 400)
        self.assertEqual(self.client.get(f"/api/inventory/assets/{asset['id']}/").data['status'], 'maintenance')
        self.assertEqual(self.client.delete(f"/api/inventory/assets/{asset['id']}/").status_code, 400)

    def test_privacy_and_staff_validation(self):
        asset = self.asset()
        r = self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.guest.pk}, format='json')
        self.assertEqual(r.status_code, 400)
        self.client.force_authenticate(self.emp)
        for path in ['categories', 'assets', 'assignments', 'summary']:
            self.assertEqual(self.client.get(f'/api/inventory/{path}/').status_code, 403)

    def test_maintenance_and_retired_assets_cannot_be_assigned(self):
        asset = self.asset()
        for status in ['maintenance', 'retired']:
            self.client.patch(f"/api/inventory/assets/{asset['id']}/", {'status': status}, format='json')
            r = self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.emp.pk}, format='json')
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self.client.post('/api/inventory/assets/', {'tag': 'BAD', 'name': 'Invalid assigned', 'category': asset['category'], 'status': 'assigned'}, format='json').status_code, 400)

    def test_active_assignment_is_protected_by_database_constraint(self):
        from django.db import IntegrityError, transaction
        from .models import Assignment
        asset = self.asset()
        self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.emp.pk}, format='json')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Assignment.objects.create(asset_id=asset['id'], employee=self.hr, assigned_by=self.hr)

    def test_categories_in_use_and_inactive_assignees_are_rejected(self):
        asset = self.asset()
        self.assertEqual(self.client.delete(f"/api/inventory/categories/{asset['category']}/").status_code, 400)
        self.emp.is_active = False
        self.emp.save(update_fields=['is_active'])
        self.assertEqual(self.client.post('/api/inventory/assignments/', {'asset': asset['id'], 'employee': self.emp.pk}, format='json').status_code, 400)


class InventoryListQueryTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        from .models import Asset, Category
        cls.hr = User.objects.create_user(username='invq', email='q@assets.test', password='x', role='hr_admin')
        cat = Category.objects.create(name='Laptops')
        for i in range(30):
            Asset.objects.create(tag=f'LT-{i:02d}', name='Laptop' if i % 2 else 'Drone', category=cat, created_by=cls.hr,
                                 status='retired' if i == 0 else 'available')

    def setUp(self):
        self.client.force_authenticate(self.hr)

    def test_unpaged_list_stays_a_bare_list(self):
        r = self.client.get('/api/inventory/assets/')
        self.assertIsInstance(r.data, list)
        self.assertEqual(len(r.data), 30)

    def test_page_search_ordering_and_status(self):
        r = self.client.get('/api/inventory/assets/', {'page': 2, 'page_size': 10, 'ordering': '-tag'})
        self.assertEqual((r.data['count'], len(r.data['results']), r.data['results'][0]['tag']), (30, 10, 'LT-19'))
        r = self.client.get('/api/inventory/assets/', {'page': 1, 'search': 'drone'})
        self.assertEqual(r.data['count'], 15)
        r = self.client.get('/api/inventory/assets/', {'page': 1, 'status': 'retired'})
        self.assertEqual([a['tag'] for a in r.data['results']], ['LT-00'])
        self.assertEqual(self.client.get('/api/inventory/assets/', {'status': 'bogus'}).status_code, 400)
        self.assertEqual(self.client.get('/api/inventory/assets/', {'page': 99}).status_code, 404)

    def test_assignments_paged(self):
        r = self.client.get('/api/inventory/assignments/', {'page': 1, 'search': 'nobody'})
        self.assertEqual(r.data['count'], 0)

    def test_still_hr_only(self):
        emp = User.objects.create_user(username='invqe', email='qe@assets.test', password='x', role='employee')
        self.client.force_authenticate(emp)
        self.assertEqual(self.client.get('/api/inventory/assets/', {'page': 1}).status_code, 403)
