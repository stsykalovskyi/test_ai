from django.test import SimpleTestCase
from django.urls import reverse


class HomeViewTests(SimpleTestCase):
    def test_homepage_renders(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ласкаво просимо")
        self.assertContains(response, "/morphology/dashboard/")
