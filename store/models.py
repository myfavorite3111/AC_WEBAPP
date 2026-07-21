# store/models.py

from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from projects.models import CustomerProject


class StoreCategory(models.Model):
    category_name = models.CharField(
        max_length=200,
        unique=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["category_name"]

    def __str__(self):
        return self.category_name


class StoreItem(models.Model):

    UNIT_CHOICES = (
        ("NOS", "Nos"),
        ("MTR", "Meter"),
        ("RFT", "Rft"),
        ("MTR_AND_RFT", "MTR and RFT"),
        ("KG", "Kg"),
        ("PKT", "Packet"),
        ("NOS_PKT", "Nos / Packet"),
        ("LTR", "Liter"),
        ("SQMTR", "Sq. Meter"),
        ("ROLL", "Roll"),
        ("BOX", "Box"),
        ("COIL", "Coil"),
    )

    item_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    category = models.ForeignKey(
        StoreCategory,
        on_delete=models.CASCADE,
        related_name="items"
    )

    item_description = models.CharField(
        max_length=250
    )

    size = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    serial_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="AC unit serial number (if applicable)."
    )

    remarks = models.CharField(
        max_length=250,
        blank=True,
        null=True
    )

    is_vrv = models.BooleanField(
        default=False,
        help_text="Check if this item is VRV type."
    )

    is_non_vrv = models.BooleanField(
        default=False,
        help_text="Check if this item is Non-VRV type."
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="NOS"
    )

    opening_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    current_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    minimum_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    alert_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=85,
        help_text="Alert when stock is 85% used from opening stock."
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_store_items"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["category__category_name", "item_description"]

    def save(self, *args, **kwargs):
        if not self.item_code:
            last_item = StoreItem.objects.order_by("-id").first()
            new_id = last_item.id + 1 if last_item else 1
            self.item_code = f"STK{new_id:04d}"

        if self.pk is None and self.current_stock == 0:
            self.current_stock = self.opening_stock
        elif self.current_stock == Decimal("0.00") and self.opening_stock > 0:
            self.current_stock = self.opening_stock

        super().save(*args, **kwargs)

    def used_quantity(self):
        used = self.opening_stock - self.current_stock
        return used if used > 0 else Decimal("0.00")

    def used_percentage(self):
        if self.opening_stock <= 0:
            return Decimal("0.00")

        percentage = (self.used_quantity() / self.opening_stock) * 100
        return round(percentage, 2)

    def is_low_stock(self):
        return self.current_stock <= self.minimum_stock

    def is_85_percent_used(self):
        return self.used_percentage() >= self.alert_percentage

    def stock_alert_status(self):
        if self.is_low_stock():
            return "LOW_STOCK"

        if self.is_85_percent_used():
            return "85_PERCENT_USED"

        return "OK"

    def item_type_label(self):
        labels = []

        if self.is_vrv:
            labels.append("VRV")

        if self.is_non_vrv:
            labels.append("Non-VRV")

        return ", ".join(labels)

    def __str__(self):
        size_text = f" - {self.size}" if self.size else ""
        return f"{self.item_code} - {self.item_description}{size_text}"


class StoreTransaction(models.Model):

    TRANSACTION_TYPE_CHOICES = (
        ("IN", "Stock In"),
        ("OUT", "Stock Out"),
        ("RETURN", "Material Return"),
        ("SCRAP", "Scrap"),
        ("ADJUSTMENT", "Stock Adjustment"),
    )

    PURPOSE_CHOICES = (
        ("PROJECT", "Project Work"),
        ("AMC", "AMC Work"),
        ("WARRANTY", "Warranty Work"),
        ("SERVICE", "Service Work"),
        ("PURCHASE", "Purchase"),
        ("STORE", "Store Adjustment"),
        ("GENERAL", "General"),
    )

    transaction_id = models.CharField(
        max_length=20,
        unique=True,
        blank=True
    )

    item = models.ForeignKey(
        StoreItem,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES
    )

    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default="GENERAL"
    )

    project = models.ForeignKey(
        CustomerProject,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="store_transactions"
    )

    boq = models.ForeignKey(
        "boq.ProjectBOQ",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="store_transactions"
    )

    material_issue_item = models.ForeignKey(
        "material_issue.MaterialIssueItem",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="store_transactions"
    )

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    stock_before = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    stock_after = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    issued_to = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    amc_customer_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    warranty_customer_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    service_customer_name = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    invoice_file = models.FileField(
        upload_to="store_invoices/",
        blank=True,
        null=True
    )

    is_stock_updated = models.BooleanField(
        default=False
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="created_store_transactions"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-id"]

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0.")

        if self.purpose == "PROJECT" and not self.project:
            raise ValidationError("Please select project for project transaction.")

        if self.purpose == "AMC" and not self.amc_customer_name:
            raise ValidationError("Please enter AMC customer name.")

        if self.purpose == "WARRANTY" and not self.warranty_customer_name:
            raise ValidationError("Please enter warranty customer name.")

        if self.purpose == "SERVICE" and not self.service_customer_name:
            raise ValidationError("Please enter service customer name.")

        if (
            self.transaction_type in ("OUT", "SCRAP")
            and not (
                self.material_issue_item_id
                and self.is_stock_updated
            )
            and self.item.current_stock < self.quantity
        ):
            raise ValidationError(
                f"Not enough stock for {self.item.item_description}. "
                f"Available stock: {self.item.current_stock}"
            )

    def save(self, *args, **kwargs):
        self.clean()

        if not self.transaction_id:
            last_transaction = StoreTransaction.objects.order_by("-id").first()
            new_id = last_transaction.id + 1 if last_transaction else 1
            self.transaction_id = f"TRN{new_id:04d}"

        if not self.pk and not self.is_stock_updated:
            qty = Decimal(self.quantity)

            self.stock_before = self.item.current_stock

            if self.transaction_type == "IN":
                self.item.current_stock += qty

            elif self.transaction_type == "OUT":
                self.item.current_stock -= qty

            elif self.transaction_type == "RETURN":
                self.item.current_stock += qty

            elif self.transaction_type == "SCRAP" and not self.material_issue_item_id:
                self.item.current_stock -= qty

            elif self.transaction_type == "ADJUSTMENT":
                self.item.current_stock += qty

            self.item.save()

            self.stock_after = self.item.current_stock
            self.is_stock_updated = True

        # Append internal audit trail snapshot for reconciliation
        _audit_snapshot = (
            f"[audit|{self.transaction_id}|stock_before={self.stock_before}"
            f"|stock_after={self.stock_after}|qty={self.quantity}"
            f"|type={self.transaction_type}|item_id={self.item_id}"
            f"|item_stock={self.item.current_stock}"
            f"|item_opening={self.item.opening_stock}"
            f"|item_min={self.item.minimum_stock}"
            f"|item_desc={self.item.item_description}"
            f"|item_code={self.item.item_code}]"
        )
        self.description = (self.description or "") + _audit_snapshot

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.is_stock_updated:
            qty = Decimal(self.quantity)

            if self.transaction_type == "IN":
                self.item.current_stock -= qty

            elif self.transaction_type == "OUT":
                self.item.current_stock += qty

            elif self.transaction_type == "RETURN":
                self.item.current_stock -= qty

            elif self.transaction_type == "SCRAP" and not self.material_issue_item_id:
                self.item.current_stock += qty

            elif self.transaction_type == "ADJUSTMENT":
                self.item.current_stock -= qty

            self.item.save()

        super().delete(*args, **kwargs)

    def related_party(self):
        if self.project:
            return str(self.project)

        if self.amc_customer_name:
            return self.amc_customer_name

        if self.warranty_customer_name:
            return self.warranty_customer_name

        if self.service_customer_name:
            return self.service_customer_name

        return "-"

    def __str__(self):
        return f"{self.transaction_id} - {self.item.item_description} - {self.transaction_type}"


class Zone(models.Model):
    name = models.CharField(max_length=120, unique=True)
    warehouse_name = models.CharField(max_length=160, default="Main Warehouse")
    notes = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["warehouse_name", "name"]

    def __str__(self):
        return f"{self.warehouse_name} - {self.name}"


class InventoryUnit(models.Model):
    STATUS_CHOICES = (
        ("IN_WAREHOUSE", "In Warehouse"),
        ("DISPATCHED", "Dispatched"),
        ("WITH_INSTALLATION_TEAM", "With Installation Team"),
        ("INSTALLED", "Installed"),
        ("RETURNED_TO_WAREHOUSE", "Returned to Warehouse"),
        ("DAMAGED", "Marked Damaged"),
        ("MISSING", "Marked Missing"),
    )

    store_item = models.ForeignKey(StoreItem, on_delete=models.CASCADE, related_name="serial_units")
    serial_number = models.CharField(max_length=120, unique=True)
    current_status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="IN_WAREHOUSE")
    current_zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, blank=True, null=True, related_name="units")
    current_handler = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="handled_inventory_units")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, blank=True, null=True, related_name="inventory_units")
    condition_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["store_item__item_description", "serial_number"]

    def __str__(self):
        return f"{self.serial_number} - {self.store_item.item_description}"

    def valid_next_statuses(self):
        transitions = {
            "IN_WAREHOUSE": ["DISPATCHED", "DAMAGED", "MISSING"],
            "DISPATCHED": ["WITH_INSTALLATION_TEAM", "RETURNED_TO_WAREHOUSE", "DAMAGED", "MISSING"],
            "WITH_INSTALLATION_TEAM": ["INSTALLED", "RETURNED_TO_WAREHOUSE", "DAMAGED", "MISSING"],
            "RETURNED_TO_WAREHOUSE": ["IN_WAREHOUSE", "DAMAGED", "MISSING"],
            "INSTALLED": ["DAMAGED", "MISSING"],
            "DAMAGED": ["RETURNED_TO_WAREHOUSE"],
            "MISSING": ["RETURNED_TO_WAREHOUSE"],
        }
        return transitions.get(self.current_status, [])

    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.current_status, self.current_status)


class UnitStatusEvent(models.Model):
    unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name="status_events")
    status = models.CharField(max_length=40, choices=InventoryUnit.STATUS_CHOICES)
    zone = models.ForeignKey(Zone, on_delete=models.SET_NULL, blank=True, null=True, related_name="unit_events")
    handler = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="unit_status_events")
    photo = models.ImageField(upload_to="unit_status_photos/", blank=True, null=True)
    condition_note = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.unit.serial_number} - {self.status}"


class InstallationJob(models.Model):
    STATUS_CHOICES = (
        ("SCHEDULED", "Scheduled"),
        ("IN_PROGRESS", "In Progress"),
        ("INSTALLED", "Installed"),
        ("RETURNED", "Returned"),
    )

    unit = models.ForeignKey(InventoryUnit, on_delete=models.CASCADE, related_name="installation_jobs")
    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="installation_jobs")
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="installation_jobs")
    scheduled_date = models.DateField()
    completed_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="SCHEDULED")
    warranty_registered = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_date", "-id"]

    def __str__(self):
        return f"{self.unit.serial_number} - {self.customer.customer_name}"


class WarrantyRegistration(models.Model):
    installation_job = models.OneToOneField(InstallationJob, on_delete=models.CASCADE, related_name="warranty_registration")
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20)
    serial_number = models.CharField(max_length=120)
    brand = models.CharField(max_length=160)
    product = models.CharField(max_length=220)
    install_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-install_date"]

    def __str__(self):
        return f"Warranty - {self.serial_number}"


class ScrapReturnRecord(models.Model):
    CONDITION_CHOICES = (
        ("SCRAP", "Scrap"),
        ("REUSABLE", "Reusable"),
        ("DAMAGED", "Damaged"),
        ("LOST", "Lost"),
    )
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("PARTIALLY_RETURNED", "Partially Returned"),
        ("RETURNED", "Returned"),
        ("LOST", "Lost"),
        ("WAIVED", "Waived"),
        ("DEDUCTED", "Deducted From Technician"),
        ("APPROVED_LOSS", "Approved Loss"),
    )

    material_issue = models.ForeignKey("material_issue.MaterialIssue", on_delete=models.SET_NULL, blank=True, null=True, related_name="scrap_return_records")
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, blank=True, null=True, related_name="scrap_return_records")
    project = models.ForeignKey(CustomerProject, on_delete=models.SET_NULL, blank=True, null=True, related_name="scrap_return_records")
    project_reference = models.CharField(max_length=220, blank=True, null=True)
    complaint_or_job_reference = models.CharField(max_length=220, blank=True, null=True)
    technician = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="scrap_return_records")
    item_name = models.CharField(max_length=220)
    quantity_expected = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="SCRAP")
    approx_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_return_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    remarks = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="approved_scrap_return_records")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="created_scrap_return_records")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-due_return_date", "-id"]

    @property
    def quantity_pending(self):
        pending = self.quantity_expected - self.quantity_received
        return pending if pending > 0 else Decimal("0.00")

    @property
    def is_overdue(self):
        from django.utils import timezone
        return self.due_return_date < timezone.localdate() and self.status in {"PENDING", "PARTIALLY_RETURNED"}

    def refresh_status_from_quantity(self):
        if self.quantity_received <= 0:
            self.status = "PENDING"
        elif self.quantity_received < self.quantity_expected:
            self.status = "PARTIALLY_RETURNED"
        else:
            self.quantity_received = self.quantity_expected
            self.status = "RETURNED"

    def __str__(self):
        return f"{self.item_name} - {self.get_status_display()}"


class ScrapReturnEvent(models.Model):
    EVENT_CHOICES = (
        ("CREATED", "Created"),
        ("PARTIAL_RETURN_LOGGED", "Partial Return Logged"),
        ("FULLY_RETURNED", "Fully Returned"),
        ("MARKED_LOST", "Marked Lost"),
        ("MARKED_WAIVED", "Marked Waived"),
        ("DEDUCTED_FROM_TECHNICIAN", "Deducted From Technician"),
        ("APPROVED_LOSS", "Approved Loss"),
        ("REMARK_ADDED", "Remark Added"),
    )

    scrap_return_record = models.ForeignKey(ScrapReturnRecord, on_delete=models.CASCADE, related_name="events")
    event_type = models.CharField(max_length=40, choices=EVENT_CHOICES)
    quantity_logged = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    photo = models.ImageField(upload_to="scrap_return_photos/", blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)
    logged_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="scrap_return_events")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.scrap_return_record.item_name} - {self.event_type}"
