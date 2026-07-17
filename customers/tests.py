from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Customer, CustomerServiceSchedule


class CustomerServiceScheduleLinkTests(TestCase):
    def test_schedule_list_links_to_customer_and_edit(self):
        user = User.objects.create_user("schedule-tester", password="test-pass")
        customer = Customer.objects.create(
            customer_name="Schedule Customer",
            phone_number="9999999999",
        )
        schedule = CustomerServiceSchedule.objects.create(
            customer=customer,
            service_type="AMC",
            service_date=date(2026, 7, 8),
        )
        self.client.force_login(user)

        response = self.client.get(reverse("customer_service_schedule_list"))

        self.assertContains(response, reverse("customer_detail", args=[customer.id]))
        self.assertContains(
            response,
            f"{reverse('edit_service_schedule', args=[schedule.id])}?next=schedule_list",
        )

    def test_schedule_list_orders_pending_before_completed(self):
        user = User.objects.create_user("schedule-filter-tester", password="test-pass")
        customer = Customer.objects.create(
            customer_name="Schedule Filter Customer",
            phone_number="9999999999",
        )
        pending = CustomerServiceSchedule.objects.create(
            customer=customer,
            service_type="AMC",
            service_date=date(2026, 7, 8),
            status="PENDING",
        )
        completed = CustomerServiceSchedule.objects.create(
            customer=customer,
            service_type="AMC",
            service_date=date(2026, 7, 9),
            status="COMPLETED",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("customer_service_schedule_list"))

        content = response.content.decode()
        self.assertContains(response, pending.service_date.strftime("%d %b %Y"))
        self.assertContains(response, completed.service_date.strftime("%d %b %Y"))
        self.assertLess(
            content.index(pending.service_date.strftime("%d %b %Y")),
            content.index(completed.service_date.strftime("%d %b %Y")),
        )

        response = self.client.get(
            reverse("customer_service_schedule_list"),
            {"status": ""},
        )

        self.assertContains(response, pending.service_date.strftime("%d %b %Y"))
        self.assertContains(response, completed.service_date.strftime("%d %b %Y"))

    def test_edit_from_schedule_list_returns_to_schedule_list(self):
        user = User.objects.create_user("schedule-edit-tester", password="test-pass")
        customer = Customer.objects.create(
            customer_name="Schedule Edit Customer",
            phone_number="9999999999",
        )
        schedule = CustomerServiceSchedule.objects.create(
            customer=customer,
            service_type="AMC",
            service_date=date(2026, 7, 8),
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_service_schedule", args=[schedule.id]),
            {
                "status": "COMPLETED",
                "completed_date": "2026-07-08",
                "complaint_title": "Done",
                "complaint_description": "Completed service",
                "remarks": "",
                "next": "schedule_list",
            },
        )

        self.assertRedirects(response, reverse("customer_service_schedule_list"))

# Create your tests here.
