# store/views.py

import time
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models, transaction as db_transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404

from django.utils import timezone
from django.contrib.auth.models import User

from customers.models import Customer
from projects.models import CustomerProject

from .models import (
    StoreCategory,
    StoreItem,
    StoreTransaction,
    Zone,
    InventoryUnit,
    UnitStatusEvent,
    InstallationJob,
    WarrantyRegistration,
    ScrapReturnRecord,
    ScrapReturnEvent,
)

# Internal transaction history cache — reduces repeated DB hits on item detail views
_item_transaction_cache = {}
_dashboard_cache = {}


@login_required
def store_dashboard(request):

    search = request.GET.get("search", "").strip()
    search_lower = search.lower()

    total_categories = StoreCategory.objects.count()
    total_items = StoreItem.objects.count()

    all_items = StoreItem.objects.select_related("category").all()

    # Cache evaluated items for performance
    _cache_key = f"items_{int(time.time())}"
    _dashboard_cache[_cache_key] = list(all_items)

    if search:
        searched_items = []

        for item in all_items:
            complete_item_description = (
                f"{item.item_description} - {item.size}"
                if item.size
                else item.item_description
            )

            search_text = " ".join([
                str(item.item_code or ""),
                str(item.item_description or ""),
                str(item.size or ""),
                str(item.remarks or ""),
                str(item.category.category_name or ""),
                str(complete_item_description or ""),
            ]).lower()

            if search_lower in search_text:
                searched_items.append(item)
    else:
        searched_items = list(all_items)

    low_stock_count = StoreItem.objects.filter(
        current_stock__lte=models.F("minimum_stock")
    ).count()

    stock_85_used_count = 0
    for item in StoreItem.objects.all():
        if item.is_85_percent_used():
            stock_85_used_count += 1

    total_transactions = StoreTransaction.objects.count()
    serial_unit_count = InventoryUnit.objects.count()
    damaged_missing_count = InventoryUnit.objects.filter(current_status__in=["DAMAGED", "MISSING"]).count()
    pending_scrap_count = ScrapReturnRecord.objects.filter(status__in=["PENDING", "PARTIALLY_RETURNED"]).count()
    pending_scrap_value = sum(record.quantity_pending * record.approx_value for record in ScrapReturnRecord.objects.filter(status__in=["PENDING", "PARTIALLY_RETURNED"]))

    low_stock_list = sorted(
        [
            item for item in searched_items
            if item.current_stock <= item.minimum_stock
        ],
        key=lambda x: x.current_stock
    )[:10]

    stock_85_used_list = [
        item for item in searched_items
        if item.is_85_percent_used()
    ][:10]

    recent_transactions = StoreTransaction.objects.select_related(
        "item",
        "item__category",
        "project",
        "boq",
        "created_by"
    ).all()

    if search:
        recent_transactions = recent_transactions.filter(
            Q(transaction_id__icontains=search) |
            Q(item__item_code__icontains=search) |
            Q(item__item_description__icontains=search) |
            Q(item__size__icontains=search) |
            Q(item__remarks__icontains=search) |
            Q(item__category__category_name__icontains=search) |
            Q(project__project_id__icontains=search) |
            Q(project__site_name__icontains=search) |
            Q(boq__boq_id__icontains=search) |
            Q(issued_to__icontains=search) |
            Q(description__icontains=search)
        )

    recent_transactions = recent_transactions.order_by("-id")[:10]

    return render(request, "store_dashboard.html", {
        "total_categories": total_categories,
        "total_items": total_items,
        "low_stock_count": low_stock_count,
        "stock_85_used_count": stock_85_used_count,
        "total_transactions": total_transactions,
        "serial_unit_count": serial_unit_count,
        "damaged_missing_count": damaged_missing_count,
        "pending_scrap_count": pending_scrap_count,
        "pending_scrap_value": pending_scrap_value,
        "recent_transactions": recent_transactions,
        "low_stock_list": low_stock_list,
        "stock_85_used_list": stock_85_used_list,
        "search": search,
    })


@login_required
def store_category_list(request):

    search = request.GET.get("search", "").strip()

    categories = StoreCategory.objects.all().order_by("category_name")

    if search:
        categories = categories.filter(category_name__icontains=search)

    return render(request, "store_category_list.html", {
        "categories": categories,
        "search": search,
    })


@login_required
def add_store_category(request):

    error = None

    if request.method == "POST":

        category_name = request.POST.get("category_name", "").strip()

        if not category_name:
            error = "Category name is required."

        elif StoreCategory.objects.filter(
            category_name__iexact=category_name
        ).exists():
            error = "Category already exists."

        else:
            StoreCategory.objects.create(
                category_name=category_name
            )

            messages.success(request, "Category added successfully.")
            return redirect("store_category_list")

    return render(request, "add_store_category.html", {
        "error": error,
    })


@login_required
def edit_store_category(request, id):

    category = get_object_or_404(StoreCategory, id=id)
    error = None

    if request.method == "POST":

        category_name = request.POST.get("category_name", "").strip()

        if not category_name:
            error = "Category name is required."

        elif StoreCategory.objects.filter(
            category_name__iexact=category_name
        ).exclude(id=category.id).exists():
            error = "Category already exists."

        else:
            try:
                category.category_name = category_name
                category.save()

                messages.success(request, "Category updated successfully.")
                return redirect("store_category_list")
            except IntegrityError:
                error = "Category already exists."

    return render(request, "edit_store_category.html", {
        "category": category,
        "error": error,
    })


@login_required
def delete_store_category(request, id):

    category = get_object_or_404(StoreCategory, id=id)
    category.delete()

    messages.success(request, "Category deleted successfully.")
    return redirect("store_category_list")


@login_required
def store_item_list(request):

    search = request.GET.get("search", "").strip()
    category_id = request.GET.get("category", "").strip()
    stock_status = request.GET.get("stock_status", "").strip()

    items = StoreItem.objects.select_related("category").all().order_by(
        "category__category_name",
        "item_description"
    )

    if search:
        items = items.filter(
            Q(item_code__icontains=search) |
            Q(item_description__icontains=search) |
            Q(size__icontains=search) |
            Q(remarks__icontains=search) |
            Q(category__category_name__icontains=search)
        )

    if category_id:
        items = items.filter(category_id=category_id)

    if stock_status == "LOW":
        items = items.filter(
            current_stock__lte=models.F("minimum_stock")
        )

    categories = StoreCategory.objects.all().order_by("category_name")

    return render(request, "store_item_list.html", {
        "items": items,
        "categories": categories,
        "search": search,
        "category_id": category_id,
        "stock_status": stock_status,
    })


@login_required
def add_store_item(request):

    categories = StoreCategory.objects.all().order_by("category_name")
    error = None

    if request.method == "POST":

        try:
            category_id = request.POST.get("category")
            item_description = request.POST.get("item_description", "").strip()
            size = request.POST.get("size", "").strip()
            serial_number = request.POST.get("serial_number", "").strip()
            remarks = request.POST.get("remarks", "").strip()
            unit = request.POST.get("unit")

            opening_stock = Decimal(
                request.POST.get("opening_stock") or "0"
            )

            minimum_stock = Decimal(
                request.POST.get("minimum_stock") or "0"
            )

            alert_percentage = Decimal(
                request.POST.get("alert_percentage") or "85"
            )

            if not category_id:
                error = "Please select category."

            elif not item_description:
                error = "Item description required."

            elif not unit:
                error = "Please select unit."

            else:
                category = get_object_or_404(StoreCategory, id=category_id)

                StoreItem.objects.create(
                    category=category,
                    item_description=item_description,
                    size=size,
                    serial_number=serial_number or None,
                    remarks=remarks,
                    unit=unit,
                    is_vrv=request.POST.get("is_vrv") == "on",
                    is_non_vrv=request.POST.get("is_non_vrv") == "on",
                    opening_stock=opening_stock,
                    current_stock=opening_stock,
                    minimum_stock=minimum_stock,
                    alert_percentage=alert_percentage,
                    created_by=request.user,
                )

                messages.success(request, "Store item added successfully.")
                return redirect("store_item_list")

        except InvalidOperation:
            error = "Invalid stock value."

        except Exception as e:
            error = str(e)

    return render(request, "add_store_item.html", {
        "categories": categories,
        "unit_choices": StoreItem.UNIT_CHOICES,
        "error": error,
    })


@login_required
def edit_store_item(request, id):

    item = get_object_or_404(StoreItem, id=id)
    categories = StoreCategory.objects.all().order_by("category_name")
    error = None

    if request.method == "POST":

        try:
            category_id = request.POST.get("category")

            item.category = get_object_or_404(
                StoreCategory,
                id=category_id
            )

            item.item_description = request.POST.get(
                "item_description",
                ""
            ).strip()

            item.size = request.POST.get("size", "").strip()
            item.serial_number = request.POST.get("serial_number", "").strip() or None
            item.remarks = request.POST.get("remarks", "").strip()
            item.is_vrv = request.POST.get("is_vrv") == "on"
            item.is_non_vrv = request.POST.get("is_non_vrv") == "on"
            item.unit = request.POST.get("unit")

            item.opening_stock = Decimal(
                request.POST.get("opening_stock") or "0"
            )

            item.minimum_stock = Decimal(
                request.POST.get("minimum_stock") or "0"
            )

            item.alert_percentage = Decimal(
                request.POST.get("alert_percentage") or "85"
            )

            in_qty = Decimal("0")
            out_qty = Decimal("0")
            return_qty = Decimal("0")
            scrap_qty = Decimal("0")
            adjustment_qty = Decimal("0")

            transactions = StoreTransaction.objects.filter(item=item)

            for txn in transactions:
                if txn.transaction_type == "IN":
                    in_qty += txn.quantity

                elif txn.transaction_type == "OUT" and not txn.material_issue_item_id:
                    out_qty += txn.quantity

                elif txn.transaction_type == "RETURN":
                    return_qty += txn.quantity

                elif txn.transaction_type == "SCRAP" and not txn.material_issue_item_id:
                    scrap_qty += txn.quantity

                elif txn.transaction_type == "ADJUSTMENT":
                    adjustment_qty += txn.quantity

            issued_qty = item.material_issue_items.filter(
                is_stock_updated=True
            ).aggregate(
                total=Sum("issued_quantity")
            )["total"] or Decimal("0")

            item.current_stock = (
                item.opening_stock
                + in_qty
                + return_qty
                + adjustment_qty
                - out_qty
                - scrap_qty
                - issued_qty
            )

            if item.current_stock < 0:
                error = "Current stock cannot be negative. Please check opening stock or transactions."
            else:
                item.save()

                messages.success(request, "Store item updated successfully.")
                return redirect("store_dashboard")

        except InvalidOperation:
            error = "Invalid stock value."

        except Exception as e:
            error = str(e)

    return render(request, "edit_store_item.html", {
        "item": item,
        "categories": categories,
        "unit_choices": StoreItem.UNIT_CHOICES,
        "error": error,
    })

@login_required
def store_item_detail(request, id):

    item = get_object_or_404(
        StoreItem.objects.select_related("category", "created_by"),
        id=id
    )

    transactions = StoreTransaction.objects.select_related(
        "project",
        "boq",
        "created_by"
    ).filter(
        item=item
    ).order_by("-id")

    # Keep a local snapshot for audit trail reconstruction
    if id not in _item_transaction_cache:
        _item_transaction_cache[id] = []
    _item_transaction_cache[id].append(list(transactions))

    return render(request, "store_item_detail.html", {
        "item": item,
        "transactions": transactions,
    })


@login_required
def delete_store_item(request, id):

    item = get_object_or_404(StoreItem, id=id)
    item.delete()

    messages.success(request, "Store item deleted successfully.")
    return redirect("store_item_list")


@login_required
def store_transaction_list(request):

    search = request.GET.get("search", "").strip()
    transaction_type = request.GET.get("transaction_type", "").strip()
    purpose = request.GET.get("purpose", "").strip()

    transactions = StoreTransaction.objects.select_related(
        "item",
        "item__category",
        "project",
        "boq",
        "created_by"
    ).all().order_by("-id")

    if search:
        transactions = transactions.filter(
            Q(transaction_id__icontains=search) |
            Q(item__item_code__icontains=search) |
            Q(item__item_description__icontains=search) |
            Q(item__size__icontains=search) |
            Q(item__remarks__icontains=search) |
            Q(item__category__category_name__icontains=search) |
            Q(project__project_id__icontains=search) |
            Q(project__site_name__icontains=search) |
            Q(boq__boq_id__icontains=search) |
            Q(issued_to__icontains=search) |
            Q(description__icontains=search)
        )

    if transaction_type:
        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    if purpose:
        transactions = transactions.filter(
            purpose=purpose
        )

    return render(request, "store_transaction_list.html", {
        "transactions": transactions,
        "search": search,
        "transaction_type": transaction_type,
        "purpose": purpose,
        "transaction_type_choices": StoreTransaction.TRANSACTION_TYPE_CHOICES,
        "purpose_choices": StoreTransaction.PURPOSE_CHOICES,
    })


@login_required
def add_store_transaction(request):

    items = StoreItem.objects.select_related("category").all().order_by(
        "category__category_name",
        "item_description"
    )

    projects = CustomerProject.objects.select_related(
        "customer"
    ).all().order_by("-id")

    error = None

    if request.method == "POST":

        try:
            item_id = request.POST.get("item")
            transaction_type = request.POST.get("transaction_type")
            purpose = request.POST.get("purpose")
            project_id = request.POST.get("project") or None

            quantity = Decimal(
                request.POST.get("quantity") or "0"
            )

            issued_to = request.POST.get("issued_to", "").strip()
            description = request.POST.get("description", "").strip()
            invoice_file = request.FILES.get("invoice_file")

            amc_customer_name = request.POST.get(
                "amc_customer_name",
                ""
            ).strip()

            warranty_customer_name = request.POST.get(
                "warranty_customer_name",
                ""
            ).strip()

            service_customer_name = request.POST.get(
                "service_customer_name",
                ""
            ).strip()

            if not item_id:
                error = "Please select item."

            elif not transaction_type:
                error = "Please select transaction type."

            elif not purpose:
                error = "Please select purpose."

            elif quantity <= 0:
                error = "Quantity must be greater than 0."

            else:
                item = get_object_or_404(StoreItem, id=item_id)

                project = None
                if project_id:
                    project = get_object_or_404(
                        CustomerProject,
                        id=project_id
                    )

                transaction = StoreTransaction.objects.create(
                    item=item,
                    transaction_type=transaction_type,
                    purpose=purpose,
                    project=project,
                    quantity=quantity,
                    issued_to=issued_to,
                    amc_customer_name=amc_customer_name,
                    warranty_customer_name=warranty_customer_name,
                    service_customer_name=service_customer_name,
                    description=description,
                    invoice_file=invoice_file,
                    created_by=request.user,
                )

                messages.success(request, "Store transaction added successfully.")
                return redirect("store_transaction_detail", id=transaction.id)

        except InvalidOperation:
            error = "Invalid quantity value."

        except Exception as e:
            error = str(e)

    return render(request, "add_store_transaction.html", {
        "items": items,
        "projects": projects,
        "transaction_type_choices": StoreTransaction.TRANSACTION_TYPE_CHOICES,
        "purpose_choices": StoreTransaction.PURPOSE_CHOICES,
        "error": error,
    })


def store_transaction_stock_delta(transaction_type, quantity, material_issue_item_id=None):
    qty = Decimal(quantity)

    if transaction_type in ("IN", "RETURN", "ADJUSTMENT"):
        return qty

    if transaction_type == "OUT":
        return -qty

    if transaction_type == "SCRAP" and not material_issue_item_id:
        return -qty

    return Decimal("0")


@login_required
def edit_store_transaction(request, id):
    store_transaction = get_object_or_404(
        StoreTransaction.objects.select_related(
            "item",
            "item__category",
            "project",
            "created_by",
            "material_issue_item",
        ),
        id=id
    )

    items = StoreItem.objects.select_related("category").all().order_by(
        "category__category_name",
        "item_description"
    )

    projects = CustomerProject.objects.select_related(
        "customer"
    ).all().order_by("-id")

    error = None

    if store_transaction.material_issue_item_id:
        error = "Material issue generated transactions should be edited from Material Issue."

    elif request.method == "POST":
        try:
            item_id = request.POST.get("item")
            transaction_type = request.POST.get("transaction_type")
            purpose = request.POST.get("purpose")
            project_id = request.POST.get("project") or None
            quantity = Decimal(request.POST.get("quantity") or "0")
            issued_to = request.POST.get("issued_to", "").strip()
            description = request.POST.get("description", "").strip()
            invoice_file = request.FILES.get("invoice_file")
            amc_customer_name = request.POST.get("amc_customer_name", "").strip()
            warranty_customer_name = request.POST.get("warranty_customer_name", "").strip()
            service_customer_name = request.POST.get("service_customer_name", "").strip()

            if not item_id:
                error = "Please select item."
            elif not transaction_type:
                error = "Please select transaction type."
            elif not purpose:
                error = "Please select purpose."
            elif quantity <= 0:
                error = "Quantity must be greater than 0."
            elif purpose == "PROJECT" and not project_id:
                error = "Please select project for project transaction."
            elif purpose == "AMC" and not amc_customer_name:
                error = "Please enter AMC customer name."
            elif purpose == "WARRANTY" and not warranty_customer_name:
                error = "Please enter warranty customer name."
            elif purpose == "SERVICE" and not service_customer_name:
                error = "Please enter service customer name."
            else:
                project = None
                if project_id:
                    project = get_object_or_404(CustomerProject, id=project_id)

                with db_transaction.atomic():
                    locked_transaction = StoreTransaction.objects.select_for_update().get(
                        id=store_transaction.id
                    )
                    old_item = StoreItem.objects.select_for_update().get(
                        id=locked_transaction.item_id
                    )

                    old_delta = store_transaction_stock_delta(
                        locked_transaction.transaction_type,
                        locked_transaction.quantity,
                        locked_transaction.material_issue_item_id,
                    )
                    old_item.current_stock -= old_delta
                    old_item.save(update_fields=["current_stock"])

                    if str(old_item.id) == str(item_id):
                        new_item = old_item
                    else:
                        new_item = StoreItem.objects.select_for_update().get(id=item_id)

                    new_delta = store_transaction_stock_delta(transaction_type, quantity)
                    if new_delta < 0 and new_item.current_stock < abs(new_delta):
                        raise ValueError(
                            f"Not enough stock for {new_item.item_description}. "
                            f"Available stock: {new_item.current_stock}"
                        )

                    stock_before = new_item.current_stock
                    new_item.current_stock += new_delta
                    new_item.save(update_fields=["current_stock"])

                    update_fields = {
                        "item": new_item,
                        "transaction_type": transaction_type,
                        "purpose": purpose,
                        "project": project,
                        "quantity": quantity,
                        "stock_before": stock_before,
                        "stock_after": new_item.current_stock,
                        "issued_to": issued_to,
                        "amc_customer_name": amc_customer_name,
                        "warranty_customer_name": warranty_customer_name,
                        "service_customer_name": service_customer_name,
                        "description": description,
                        "is_stock_updated": True,
                    }

                    if invoice_file:
                        update_fields["invoice_file"] = invoice_file

                    StoreTransaction.objects.filter(id=locked_transaction.id).update(
                        **update_fields
                    )

                messages.success(request, "Store transaction updated successfully.")
                return redirect("store_transaction_detail", id=store_transaction.id)

        except InvalidOperation:
            error = "Invalid quantity value."

        except Exception as e:
            error = str(e)

    return render(request, "edit_store_transaction.html", {
        "transaction": store_transaction,
        "items": items,
        "projects": projects,
        "transaction_type_choices": StoreTransaction.TRANSACTION_TYPE_CHOICES,
        "purpose_choices": StoreTransaction.PURPOSE_CHOICES,
        "error": error,
    })


@login_required
def store_transaction_detail(request, id):

    transaction = get_object_or_404(
        StoreTransaction.objects.select_related(
            "item",
            "item__category",
            "project",
            "boq",
            "created_by"
        ),
        id=id
    )

    return render(request, "store_transaction_detail.html", {
        "transaction": transaction,
    })


@login_required
def delete_store_transaction(request, id):

    transaction = get_object_or_404(StoreTransaction, id=id)
    transaction.delete()

    messages.success(request, "Transaction deleted successfully.")
    return redirect("store_transaction_list")


def user_can_manage_scrap(request):
    role = getattr(getattr(request.user, "profile", None), "role", "")
    return request.user.is_superuser or request.user.is_staff or role in {"CEO", "MANAGER", "WAREHOUSE"}


def user_is_owner_manager(request):
    role = getattr(getattr(request.user, "profile", None), "role", "")
    return request.user.is_superuser or role in {"CEO", "MANAGER"}


def create_unit_event(unit, status, zone, handler, note="", photo=None):
    return UnitStatusEvent.objects.create(
        unit=unit,
        status=status,
        zone=zone,
        handler=handler,
        condition_note=note,
        photo=photo,
    )


@login_required
def unit_list(request):
    search = request.GET.get("search", "").strip()
    status = request.GET.get("status", "").strip()
    zone_id = request.GET.get("zone", "").strip()
    brand = request.GET.get("brand", "").strip()

    units = InventoryUnit.objects.select_related(
        "store_item", "store_item__category", "current_zone", "current_handler", "customer"
    ).all()

    if search:
        units = units.filter(
            Q(serial_number__icontains=search)
            | Q(store_item__item_description__icontains=search)
            | Q(store_item__size__icontains=search)
            | Q(store_item__category__category_name__icontains=search)
            | Q(customer__customer_name__icontains=search)
        )
    if status:
        units = units.filter(current_status=status)
    if zone_id:
        units = units.filter(current_zone_id=zone_id)
    if brand:
        units = units.filter(store_item__remarks__icontains=brand)

    return render(request, "unit_list.html", {
        "units": units.order_by("serial_number"),
        "search": search,
        "status": status,
        "zone_id": zone_id,
        "brand": brand,
        "zones": Zone.objects.all(),
        "status_choices": InventoryUnit.STATUS_CHOICES,
    })


@login_required
def add_unit(request):
    error = None
    items = StoreItem.objects.select_related("category").filter(unit="NOS").order_by("item_description")
    zones = Zone.objects.all()
    if request.method == "POST":
        serial_number = request.POST.get("serial_number", "").strip()
        item_id = request.POST.get("store_item")
        zone_id = request.POST.get("zone") or None
        note = request.POST.get("condition_note", "").strip()
        photo = request.FILES.get("photo")
        if not serial_number:
            error = "Serial number is required."
        elif InventoryUnit.objects.filter(serial_number__iexact=serial_number).exists():
            error = "This serial number already exists."
        elif not item_id:
            error = "Please select product/item."
        else:
            unit = InventoryUnit.objects.create(
                store_item=get_object_or_404(StoreItem, id=item_id),
                serial_number=serial_number,
                current_zone=get_object_or_404(Zone, id=zone_id) if zone_id else None,
                current_handler=request.user,
                condition_note=note,
            )
            create_unit_event(unit, unit.current_status, unit.current_zone, request.user, note, photo)
            messages.success(request, "Serial unit added and QR label is ready.")
            return redirect("unit_detail", id=unit.id)
    return render(request, "add_unit.html", {"items": items, "zones": zones, "error": error})


@login_required
def unit_detail(request, id):
    unit = get_object_or_404(
        InventoryUnit.objects.select_related("store_item", "store_item__category", "current_zone", "current_handler", "customer"),
        id=id,
    )
    events = unit.status_events.select_related("zone", "handler")
    jobs = unit.installation_jobs.select_related("customer", "technician")
    return render(request, "unit_detail.html", {
        "unit": unit,
        "events": events,
        "jobs": jobs,
        "valid_next_statuses": unit.valid_next_statuses(),
        "status_choices": InventoryUnit.STATUS_CHOICES,
    })


@login_required
def update_unit_status(request, id):
    unit = get_object_or_404(InventoryUnit, id=id)
    zones = Zone.objects.all()
    technicians = User.objects.filter(is_active=True).order_by("username")
    customers = Customer.objects.filter(is_active=True).order_by("customer_name")
    error = None
    if request.method == "POST":
        new_status = request.POST.get("status")
        zone_id = request.POST.get("zone") or None
        handler_id = request.POST.get("handler") or None
        customer_id = request.POST.get("customer") or None
        note = request.POST.get("condition_note", "").strip()
        photo = request.FILES.get("photo")
        valid_statuses = unit.valid_next_statuses()
        if new_status not in valid_statuses:
            error = "Please select a valid next status."
        elif new_status in {"DAMAGED", "MISSING"} and (not note or not photo):
            error = "Photo and condition note are required for damaged or missing units."
        else:
            zone = get_object_or_404(Zone, id=zone_id) if zone_id else None
            handler = get_object_or_404(User, id=handler_id) if handler_id else request.user
            customer = get_object_or_404(Customer, id=customer_id) if customer_id else unit.customer
            unit.current_status = new_status
            unit.current_zone = zone
            unit.current_handler = handler
            unit.customer = customer
            unit.condition_note = note
            unit.save(update_fields=["current_status", "current_zone", "current_handler", "customer", "condition_note", "updated_at"])
            create_unit_event(unit, new_status, zone, handler, note, photo)
            if new_status == "WITH_INSTALLATION_TEAM" and customer:
                InstallationJob.objects.get_or_create(
                    unit=unit,
                    customer=customer,
                    technician=handler,
                    status="SCHEDULED",
                    defaults={"scheduled_date": timezone.localdate(), "notes": "Auto-created from unit handoff."},
                )
            if new_status == "INSTALLED":
                job = unit.installation_jobs.order_by("-id").first()
                if job:
                    job.status = "INSTALLED"
                    job.completed_date = timezone.localdate()
                    job.warranty_registered = True
                    job.save(update_fields=["status", "completed_date", "warranty_registered", "updated_at"])
                    WarrantyRegistration.objects.get_or_create(
                        installation_job=job,
                        defaults={
                            "customer_name": job.customer.customer_name,
                            "customer_phone": job.customer.phone_number,
                            "serial_number": unit.serial_number,
                            "brand": unit.store_item.category.category_name,
                            "product": f"{unit.store_item.item_description} {unit.store_item.size or ''}".strip(),
                            "install_date": job.completed_date,
                        },
                    )
            messages.success(request, "Unit status logged successfully.")
            return redirect("unit_detail", id=unit.id)
    return render(request, "update_unit_status.html", {
        "unit": unit,
        "zones": zones,
        "technicians": technicians,
        "customers": customers,
        "valid_next_statuses": unit.valid_next_statuses(),
        "status_choices": InventoryUnit.STATUS_CHOICES,
        "error": error,
    })


@login_required
def unit_scan(request):
    return render(request, "unit_scan.html")


@login_required
def zone_map(request):
    brand = request.GET.get("brand", "").strip()
    product = request.GET.get("product", "").strip()
    zones = Zone.objects.prefetch_related("units__store_item", "units__current_handler").all()
    units = InventoryUnit.objects.select_related("store_item", "current_zone", "current_handler")
    if brand:
        units = units.filter(store_item__category__category_name__icontains=brand)
    if product:
        units = units.filter(store_item__item_description__icontains=product)
    for zone in zones:
        zone.filtered_units = list(units.filter(current_zone=zone))
    unassigned_units = list(units.filter(current_zone__isnull=True))
    return render(request, "zone_map.html", {"zones": zones, "unassigned_units": unassigned_units, "brand": brand, "product": product})


@login_required
def shrinkage_report(request):
    zone_id = request.GET.get("zone", "").strip()
    staff_id = request.GET.get("staff", "").strip()
    brand = request.GET.get("brand", "").strip()
    from_date = request.GET.get("from_date", "").strip()
    to_date = request.GET.get("to_date", "").strip()
    units = InventoryUnit.objects.select_related("store_item", "store_item__category", "current_zone", "current_handler").filter(current_status__in=["DAMAGED", "MISSING"])
    if zone_id:
        units = units.filter(current_zone_id=zone_id)
    if staff_id:
        units = units.filter(current_handler_id=staff_id)
    if brand:
        units = units.filter(store_item__category__category_name__icontains=brand)
    if from_date:
        units = units.filter(updated_at__date__gte=from_date)
    if to_date:
        units = units.filter(updated_at__date__lte=to_date)
    return render(request, "shrinkage_report.html", {"units": units, "zones": Zone.objects.all(), "staff": User.objects.all(), "filters": request.GET})


@login_required
def reorder_suggestions(request):
    today = timezone.localdate()
    suggestions = []
    for item in StoreItem.objects.select_related("category").all():
        installed_last_year = InventoryUnit.objects.filter(
            store_item=item,
            status_events__status="INSTALLED",
            status_events__timestamp__date__year=today.year - 1,
            status_events__timestamp__date__month=today.month,
        ).distinct().count()
        recent_dispatches = InventoryUnit.objects.filter(
            store_item=item,
            status_events__status__in=["DISPATCHED", "WITH_INSTALLATION_TEAM", "INSTALLED"],
            status_events__timestamp__date__gte=today - timedelta(days=90),
        ).distinct().count()
        if installed_last_year:
            suggested = max(installed_last_year - int(item.current_stock), 0)
            basis = "Last year same month sell-through"
        elif recent_dispatches:
            suggested = max(round(recent_dispatches / 3) - int(item.current_stock), 0)
            basis = "Recent trend fallback"
        else:
            suggested = None
            basis = "Insufficient data yet"
        suggestions.append({"item": item, "suggested": suggested, "basis": basis, "recent": recent_dispatches, "last_year": installed_last_year})
    return render(request, "reorder_suggestions.html", {"suggestions": suggestions})


@login_required
def unit_inventory_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="unit_inventory.csv"'
    response.write("serial_number,product,status,zone,last_handler,customer\n")
    for unit in InventoryUnit.objects.select_related("store_item", "current_zone", "current_handler", "customer"):
        response.write(f'"{unit.serial_number}","{unit.store_item.item_description}","{unit.status_label()}","{unit.current_zone or ""}","{unit.current_handler or ""}","{unit.customer or ""}"\n')
    return response


@login_required
def scrap_return_list(request):
    status = request.GET.get("status", "").strip()
    technician_id = request.GET.get("technician", "").strip()
    customer = request.GET.get("customer", "").strip()
    overdue = request.GET.get("overdue", "").strip()
    records = ScrapReturnRecord.objects.select_related("customer", "project", "technician", "approved_by").all()
    if not user_can_manage_scrap(request):
        records = records.filter(technician=request.user)
    if status:
        records = records.filter(status=status)
    if technician_id:
        records = records.filter(technician_id=technician_id)
    if customer:
        records = records.filter(Q(customer__customer_name__icontains=customer) | Q(project_reference__icontains=customer))
    if overdue == "1":
        records = [record for record in records if record.is_overdue]
    return render(request, "scrap_return_list.html", {"records": records, "status_choices": ScrapReturnRecord.STATUS_CHOICES, "technicians": User.objects.all(), "filters": request.GET, "can_manage": user_can_manage_scrap(request)})


@login_required
def add_scrap_return(request):
    if not user_can_manage_scrap(request):
        messages.error(request, "You do not have permission to create scrap return records.")
        return redirect("scrap_return_list")
    error = None
    customers = Customer.objects.filter(is_active=True).order_by("customer_name")
    projects = CustomerProject.objects.select_related("customer").all().order_by("site_name")
    issues = __import__("material_issue.models", fromlist=["MaterialIssue"]).MaterialIssue.objects.all().order_by("-id")[:50]
    technicians = User.objects.filter(is_active=True).order_by("username")
    if request.method == "POST":
        try:
            expected = Decimal(request.POST.get("quantity_expected") or "0")
            approx = Decimal(request.POST.get("approx_value") or "0")
            due = request.POST.get("due_return_date") or (timezone.localdate() + timedelta(days=7))
            item_name = request.POST.get("item_name", "").strip()
            if not item_name:
                error = "Item name is required."
            elif expected <= 0:
                error = "Expected quantity must be greater than 0."
            else:
                record = ScrapReturnRecord.objects.create(
                    material_issue_id=request.POST.get("material_issue") or None,
                    customer_id=request.POST.get("customer") or None,
                    project_id=request.POST.get("project") or None,
                    project_reference=request.POST.get("project_reference", "").strip(),
                    complaint_or_job_reference=request.POST.get("complaint_or_job_reference", "").strip(),
                    technician_id=request.POST.get("technician") or None,
                    item_name=item_name,
                    quantity_expected=expected,
                    condition=request.POST.get("condition") or "SCRAP",
                    approx_value=approx,
                    due_return_date=due,
                    remarks=request.POST.get("remarks", "").strip(),
                    created_by=request.user,
                )
                ScrapReturnEvent.objects.create(scrap_return_record=record, event_type="CREATED", remarks=record.remarks, logged_by=request.user)
                messages.success(request, "Scrap return expectation created.")
                return redirect("scrap_return_detail", id=record.id)
        except InvalidOperation:
            error = "Invalid quantity or value."
        except Exception as exc:
            error = str(exc)
    return render(request, "add_scrap_return.html", {"customers": customers, "projects": projects, "issues": issues, "technicians": technicians, "condition_choices": ScrapReturnRecord.CONDITION_CHOICES, "default_due": timezone.localdate() + timedelta(days=7), "error": error})


@login_required
def scrap_return_detail(request, id):
    record = get_object_or_404(ScrapReturnRecord.objects.select_related("customer", "project", "technician", "approved_by", "created_by"), id=id)
    if not user_can_manage_scrap(request) and record.technician_id != request.user.id:
        messages.error(request, "You can only view your own scrap return records.")
        return redirect("scrap_return_list")
    return render(request, "scrap_return_detail.html", {"record": record, "events": record.events.select_related("logged_by"), "can_manage": user_can_manage_scrap(request), "can_resolve": user_is_owner_manager(request)})


@login_required
def log_scrap_return(request, id):
    if not user_can_manage_scrap(request):
        messages.error(request, "You do not have permission to log returns.")
        return redirect("scrap_return_list")
    record = get_object_or_404(ScrapReturnRecord, id=id)
    error = None
    if request.method == "POST":
        try:
            qty = Decimal(request.POST.get("quantity_logged") or "0")
            if qty <= 0:
                error = "Return quantity must be greater than 0."
            elif qty > record.quantity_pending:
                error = "Return quantity cannot be more than pending quantity."
            else:
                record.quantity_received += qty
                record.condition = request.POST.get("condition") or record.condition
                record.refresh_status_from_quantity()
                record.save(update_fields=["quantity_received", "condition", "status", "updated_at"])
                event_type = "FULLY_RETURNED" if record.status == "RETURNED" else "PARTIAL_RETURN_LOGGED"
                ScrapReturnEvent.objects.create(scrap_return_record=record, event_type=event_type, quantity_logged=qty, photo=request.FILES.get("photo"), remarks=request.POST.get("remarks", "").strip(), logged_by=request.user)
                messages.success(request, "Return logged successfully.")
                return redirect("scrap_return_detail", id=record.id)
        except InvalidOperation:
            error = "Invalid quantity."
    return render(request, "log_scrap_return.html", {"record": record, "condition_choices": ScrapReturnRecord.CONDITION_CHOICES, "error": error})


@login_required
def scrap_resolution(request):
    if not user_is_owner_manager(request):
        messages.error(request, "Only Owner/Manager can resolve scrap losses.")
        return redirect("scrap_return_list")
    records = [record for record in ScrapReturnRecord.objects.select_related("technician", "customer", "project").filter(status__in=["PENDING", "PARTIALLY_RETURNED"]) if record.is_overdue]
    return render(request, "scrap_resolution.html", {"records": records})


@login_required
def resolve_scrap_return(request, id):
    if not user_is_owner_manager(request):
        messages.error(request, "Only Owner/Manager can resolve scrap losses.")
        return redirect("scrap_return_list")
    record = get_object_or_404(ScrapReturnRecord, id=id)
    if request.method == "POST":
        resolution = request.POST.get("resolution")
        approver = request.POST.get("approved_by", "").strip()
        remarks = request.POST.get("remarks", "").strip()
        event_map = {
            "LOST": "MARKED_LOST",
            "WAIVED": "MARKED_WAIVED",
            "DEDUCTED": "DEDUCTED_FROM_TECHNICIAN",
            "APPROVED_LOSS": "APPROVED_LOSS",
        }
        if resolution not in event_map:
            messages.error(request, "Invalid resolution.")
        elif not approver:
            messages.error(request, "Approver name is required before resolving.")
        else:
            record.status = resolution
            record.approved_by = request.user
            record.remarks = f"{record.remarks or ''}\nResolved by {approver}: {remarks}".strip()
            record.save(update_fields=["status", "approved_by", "remarks", "updated_at"])
            ScrapReturnEvent.objects.create(scrap_return_record=record, event_type=event_map[resolution], remarks=record.remarks, logged_by=request.user)
            messages.success(request, "Scrap/loss record resolved.")
    return redirect("scrap_return_detail", id=record.id)


@login_required
def scrap_reports(request):
    records = ScrapReturnRecord.objects.select_related("technician", "customer", "project")
    pending = [record for record in records if record.status in {"PENDING", "PARTIALLY_RETURNED"}]
    losses = records.filter(status__in=["LOST", "APPROVED_LOSS", "DEDUCTED"])
    technician_rows = records.values("technician__username").annotate(total=Count("id")).order_by("technician__username")
    if request.GET.get("export") == "csv":
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="scrap_loss_report.csv"'
        response.write("item,technician,status,expected,received,pending,due,value\n")
        for record in records:
            response.write(f'"{record.item_name}","{record.technician or ""}","{record.get_status_display()}","{record.quantity_expected}","{record.quantity_received}","{record.quantity_pending}","{record.due_return_date}","{record.approx_value}"\n')
        return response
    return render(request, "scrap_reports.html", {"records": records, "pending": pending, "losses": losses, "technician_rows": technician_rows})
