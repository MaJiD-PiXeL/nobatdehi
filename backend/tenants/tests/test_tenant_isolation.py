from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from tenants.models import Branch, Business, BusinessMember


class TenantIsolationTests(TestCase):
    def test_member_cannot_list_another_tenants_branches(self) -> None:
        owner_one = User.objects.create_user(email="one@example.test", password="correct-horse-battery-staple")
        owner_two = User.objects.create_user(email="two@example.test", password="correct-horse-battery-staple")
        first = Business.objects.create(owner=owner_one, name="اول", slug="first")
        second = Business.objects.create(owner=owner_two, name="دوم", slug="second")
        BusinessMember.objects.create(business=first, user=owner_one, role=BusinessMember.Role.OWNER)
        BusinessMember.objects.create(business=second, user=owner_two, role=BusinessMember.Role.OWNER)
        own_branch = Branch.objects.create(business=first, name="شعبهٔ اول", slug="one")
        Branch.objects.create(business=second, name="شعبهٔ دوم", slug="two")

        client = APIClient()
        client.force_authenticate(owner_one)
        response = client.get("/api/v1/branches/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [str(own_branch.id)])

