from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from catalog.models import Service
from tenants.models import Branch, Business, BusinessMember
from workforce.models import Employee


class PublicDiscoveryTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.test", password="correct-horse-battery-staple")
        self.business = Business.objects.create(owner=self.owner, name="مرکز آرامش")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Role.OWNER)
        self.branch = Branch.objects.create(business=self.business, name="اصلی", slug="main")
        self.employee = Employee.objects.create(business=self.business, first_name="نیلوفر", last_name="احمدی", specialty="مشاوره")
        self.employee.branches.add(self.branch)
        self.service = Service.objects.create(business=self.business, name="مشاوره", price=500_000, duration_minutes=60)
        self.service.branches.add(self.branch)

    def test_public_search_matches_provider_name(self) -> None:
        response = self.client.get("/api/v1/businesses/?q=نیلوفر احمدی")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["slug"], self.business.slug)
        self.assertEqual(response.data[0]["providers"][0]["name"], "نیلوفر احمدی")

    def test_public_search_matches_service_and_includes_service_summary(self) -> None:
        response = self.client.get("/api/v1/businesses/?q=مشاوره")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["slug"], self.business.slug)
        self.assertEqual(response.data[0]["services"][0]["name"], "مشاوره")

    def test_onboarding_creates_a_bookable_business(self) -> None:
        client = APIClient()
        client.force_authenticate(self.owner)

        response = client.post(
            "/api/v1/businesses/onboard/",
            {
                "business_name": "کلینیک نمونه",
                "professional_first_name": "سارا",
                "professional_last_name": "رضایی",
                "service_name": "ویزیت اولیه",
                "service_price": 300_000,
                "service_duration_minutes": 45,
                "working_days": [0, 1],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        business = Business.objects.get(slug=response.data["slug"])
        self.assertTrue(business.branches.exists())
        self.assertTrue(business.services.exists())
        self.assertTrue(business.employees.exists())
        self.assertEqual(business.branches.first().work_hours.count(), 2)
