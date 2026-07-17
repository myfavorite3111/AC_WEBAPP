from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from customers.models import Customer
from material_issue.models import MaterialIssue, MaterialIssueItem
from projects.models import CustomerProject

from .models import StoreCategory, StoreItem, StoreTransaction


class StoreItemRecalculationTests(TestCase):
    def test_edit_keeps_material_issue_deduction_in_current_stock(self):
        user = User.objects.create_user("store-tester", password="test-pass")
        customer = Customer.objects.create(
            customer_name="Stock Customer",
            phone_number="9999999999",
        )
        project = CustomerProject.objects.create(
            customer=customer,
            site_name="Stock Site",
        )
        category = StoreCategory.objects.create(category_name="Stock Test")
        item = StoreItem.objects.create(
            category=category,
            item_description="VRV Unit",
            is_vrv=True,
            opening_stock=Decimal("10"),
            current_stock=Decimal("10"),
            minimum_stock=Decimal("1"),
        )
        issue = MaterialIssue.objects.create(project=project, issued_by=user)
        MaterialIssueItem.objects.create(
            material_issue=issue,
            store_item=item,
            issued_quantity=Decimal("4"),
        )

        self.client.force_login(user)
        response = self.client.post(
            reverse("edit_store_item", args=[item.id]),
            {
                "category": category.id,
                "item_description": item.item_description,
                "size": "",
                "serial_number": "",
                "remarks": "",
                "is_vrv": "on",
                "is_non_vrv": "on",
                "unit": "NOS",
                "opening_stock": "10",
                "minimum_stock": "1",
                "alert_percentage": "85",
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.current_stock, Decimal("6"))


class StoreItemTypeTests(TestCase):
    def test_item_type_label_handles_all_checkbox_states(self):
        category = StoreCategory.objects.create(category_name="Type Test")

        both = StoreItem.objects.create(
            category=category,
            item_description="Copper Pipe Both",
            is_vrv=True,
            is_non_vrv=True,
        )
        vrv = StoreItem.objects.create(
            category=category,
            item_description="Copper Pipe VRV",
            is_vrv=True,
            is_non_vrv=False,
        )
        non_vrv = StoreItem.objects.create(
            category=category,
            item_description="Copper Pipe Non VRV",
            is_vrv=False,
            is_non_vrv=True,
        )
        empty = StoreItem.objects.create(
            category=category,
            item_description="Copper Pipe Empty",
            is_vrv=False,
            is_non_vrv=False,
        )
        other_item = StoreItem.objects.create(
            category=category,
            item_description="PVC Reducer",
            is_vrv=True,
            is_non_vrv=True,
        )

        self.assertEqual(both.item_type_label(), "VRV, Non-VRV")
        self.assertEqual(vrv.item_type_label(), "VRV")
        self.assertEqual(non_vrv.item_type_label(), "Non-VRV")
        self.assertEqual(empty.item_type_label(), "")
        self.assertTrue(other_item.is_vrv)
        self.assertTrue(other_item.is_non_vrv)
        self.assertEqual(other_item.item_type_label(), "VRV, Non-VRV")

    def test_add_and_edit_store_item_save_non_vrv_checkbox(self):
        user = User.objects.create_user("type-tester", password="test-pass")
        category = StoreCategory.objects.create(category_name="Type Save")
        self.client.force_login(user)

        add_response = self.client.post(
            reverse("add_store_item"),
            {
                "category": category.id,
                "item_description": "Copper Pipe Dual Type",
                "size": "",
                "serial_number": "",
                "remarks": "",
                "is_vrv": "on",
                "is_non_vrv": "on",
                "unit": "NOS",
                "opening_stock": "0",
                "minimum_stock": "0",
                "alert_percentage": "85",
            },
        )

        self.assertEqual(add_response.status_code, 302)
        item = StoreItem.objects.get(item_description="Copper Pipe Dual Type")
        self.assertTrue(item.is_vrv)
        self.assertTrue(item.is_non_vrv)

        edit_response = self.client.post(
            reverse("edit_store_item", args=[item.id]),
            {
                "category": category.id,
                "item_description": "Copper Pipe Dual Type",
                "size": "",
                "serial_number": "",
                "remarks": "",
                "unit": "NOS",
                "opening_stock": "0",
                "minimum_stock": "0",
                "alert_percentage": "85",
            },
        )

        self.assertEqual(edit_response.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(item.is_vrv)
        self.assertFalse(item.is_non_vrv)

    def test_non_copper_pipe_can_save_type_flags(self):
        user = User.objects.create_user("type-save-tester", password="test-pass")
        category = StoreCategory.objects.create(category_name="Type Save Other")
        self.client.force_login(user)

        response = self.client.post(
            reverse("add_store_item"),
            {
                "category": category.id,
                "item_description": "PVC Elbow",
                "size": "",
                "serial_number": "",
                "remarks": "",
                "is_vrv": "on",
                "is_non_vrv": "on",
                "unit": "NOS",
                "opening_stock": "0",
                "minimum_stock": "0",
                "alert_percentage": "85",
            },
        )

        self.assertEqual(response.status_code, 302)
        item = StoreItem.objects.get(item_description="PVC Elbow")
        self.assertTrue(item.is_vrv)
        self.assertTrue(item.is_non_vrv)
        self.assertEqual(item.item_type_label(), "VRV, Non-VRV")


class StoreCategoryEditTests(TestCase):
    def test_edit_store_category_duplicate_name_returns_form_error(self):
        user = User.objects.create_user("category-tester", password="test-pass")
        first = StoreCategory.objects.create(category_name="First")
        second = StoreCategory.objects.create(category_name="Second")
        self.client.force_login(user)

        response = self.client.post(
            reverse("edit_store_category", args=[second.id]),
            {"category_name": first.category_name},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Category already exists.")


class StoreTransactionEditTests(TestCase):
    def test_edit_store_transaction_recalculates_item_stock(self):
        user = User.objects.create_user("transaction-tester", password="test-pass")
        category = StoreCategory.objects.create(category_name="Transaction Test")
        item = StoreItem.objects.create(
            category=category,
            item_description="Copper Pipe",
            opening_stock=Decimal("10"),
            current_stock=Decimal("10"),
        )
        transaction = StoreTransaction.objects.create(
            item=item,
            transaction_type="IN",
            purpose="PURCHASE",
            quantity=Decimal("5"),
            created_by=user,
        )
        item.refresh_from_db()
        self.assertEqual(item.current_stock, Decimal("15"))

        self.client.force_login(user)
        response = self.client.post(
            reverse("edit_store_transaction", args=[transaction.id]),
            {
                "item": item.id,
                "transaction_type": "OUT",
                "purpose": "GENERAL",
                "project": "",
                "quantity": "4",
                "issued_to": "Technician",
                "amc_customer_name": "",
                "warranty_customer_name": "",
                "service_customer_name": "",
                "description": "Edited movement",
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        transaction.refresh_from_db()
        self.assertEqual(item.current_stock, Decimal("6"))
        self.assertEqual(transaction.transaction_type, "OUT")
        self.assertEqual(transaction.quantity, Decimal("4.00"))
        self.assertEqual(transaction.stock_before, Decimal("10.00"))
        self.assertEqual(transaction.stock_after, Decimal("6.00"))

# Create your tests here.
