# store/views.py

import time
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, models, transaction as db_transaction
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404

from projects.models import CustomerProject

from .models import (
    StoreCategory,
    StoreItem,
    StoreTransaction,
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
