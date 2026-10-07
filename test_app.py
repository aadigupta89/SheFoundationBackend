import unittest

from app import app


class AppApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_admin_login_valid_credentials(self):
        response = self.client.post(
            '/api/admin/login',
            json={'username': 'admin', 'password': 'shepower123'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('token', response.get_json())

    def test_admin_login_invalid_credentials(self):
        response = self.client.post(
            '/api/admin/login',
            json={'username': 'admin', 'password': 'wrongpass'}
        )
        self.assertEqual(response.status_code, 401)

    def test_get_content_returns_arrays(self):
        response = self.client.get('/api/content')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn('gallery', data)
        self.assertIn('work', data)

    def test_archive_and_delete_item(self):
        upload_response = self.client.post(
            '/api/admin/upload',
            data={
                'title': 'Archive Test',
                'note': 'Will be archived later',
                'type': 'gallery',
                'archive_date': '2025-10-01',
                'image': (b'fake-image-content', 'archive-test.png')
            },
            content_type='multipart/form-data',
            headers={'Authorization': 'Bearer demo-admin-token'}
        )
        self.assertEqual(upload_response.status_code, 201)
        item = upload_response.get_json()['entry']

        archive_response = self.client.patch(
            f"/api/admin/content/gallery/{item['id']}/archive",
            json={'archived': True, 'archive_date': '2025-10-01'},
            headers={'Authorization': 'Bearer demo-admin-token'}
        )
        self.assertEqual(archive_response.status_code, 200)
        self.assertTrue(archive_response.get_json()['entry']['archived'])

        delete_response = self.client.delete(
            f"/api/admin/content/gallery/{item['id']}",
            headers={'Authorization': 'Bearer demo-admin-token'}
        )
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn('deleted', delete_response.get_json()['message'])


if __name__ == '__main__':
    unittest.main()
