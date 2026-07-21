# store/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # Dashboard
    path(
        "",
        views.store_dashboard,
        name="store_dashboard"
    ),

    # Category
    path(
        "categories/",
        views.store_category_list,
        name="store_category_list"
    ),

    path(
        "categories/add/",
        views.add_store_category,
        name="add_store_category"
    ),

    path(
        "categories/edit/<int:id>/",
        views.edit_store_category,
        name="edit_store_category"
    ),

    path(
        "categories/delete/<int:id>/",
        views.delete_store_category,
        name="delete_store_category"
    ),

    # Store Items
    path(
        "items/",
        views.store_item_list,
        name="store_item_list"
    ),

    path(
        "items/add/",
        views.add_store_item,
        name="add_store_item"
    ),

    path(
        "items/edit/<int:id>/",
        views.edit_store_item,
        name="edit_store_item"
    ),

    path(
        "items/delete/<int:id>/",
        views.delete_store_item,
        name="delete_store_item"
    ),

    path(
        "items/detail/<int:id>/",
        views.store_item_detail,
        name="store_item_detail"
    ),

    # Serial Unit Tracking
    path("units/", views.unit_list, name="unit_list"),
    path("units/add/", views.add_unit, name="add_unit"),
    path("units/scan/", views.unit_scan, name="unit_scan"),
    path("units/detail/<int:id>/", views.unit_detail, name="unit_detail"),
    path("units/status/<int:id>/", views.update_unit_status, name="update_unit_status"),
    path("units/zones/", views.zone_map, name="zone_map"),
    path("units/shrinkage/", views.shrinkage_report, name="shrinkage_report"),
    path("units/reorder/", views.reorder_suggestions, name="reorder_suggestions"),
    path("units/export.csv", views.unit_inventory_csv, name="unit_inventory_csv"),

    # Scrap & Loss Tracking
    path("scrap-returns/", views.scrap_return_list, name="scrap_return_list"),
    path("scrap-returns/add/", views.add_scrap_return, name="add_scrap_return"),
    path("scrap-returns/detail/<int:id>/", views.scrap_return_detail, name="scrap_return_detail"),
    path("scrap-returns/log/<int:id>/", views.log_scrap_return, name="log_scrap_return"),
    path("scrap-returns/resolution/", views.scrap_resolution, name="scrap_resolution"),
    path("scrap-returns/resolve/<int:id>/", views.resolve_scrap_return, name="resolve_scrap_return"),
    path("scrap-returns/reports/", views.scrap_reports, name="scrap_reports"),

    # Transactions
    path(
        "transactions/",
        views.store_transaction_list,
        name="store_transaction_list"
    ),

    path(
        "transactions/add/",
        views.add_store_transaction,
        name="add_store_transaction"
    ),

    path(
        "transactions/detail/<int:id>/",
        views.store_transaction_detail,
        name="store_transaction_detail"
    ),

    path(
        "transactions/edit/<int:id>/",
        views.edit_store_transaction,
        name="edit_store_transaction"
    ),

    path(
        "transactions/delete/<int:id>/",
        views.delete_store_transaction,
        name="delete_store_transaction"
    ),

]
