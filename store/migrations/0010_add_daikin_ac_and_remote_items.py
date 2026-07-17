from django.db import migrations


ITEMS = [
    ("Remotes and Receiver Kits", "CORDED REMOTE BRC2E61", "", "NOS"),
    ("Remotes and Receiver Kits", "NAVIGATION REMOTE BRCIE63", "", "NOS"),
    ("Remotes and Receiver Kits", "HANDSET BRC4M150W16", "", "NOS"),
    ("Remotes and Receiver Kits", "RECEIVER KIT BRC7N618-6", "", "NOS"),
    ("Remotes and Receiver Kits", "RECEIVER KIT BRC63AV", "", "NOS"),
    ("Remotes and Receiver Kits", "RECEIVER KIT BRC4M61-6", "", "NOS"),
    ("Remotes and Receiver Kits", "RECEIVER KIT BRC91A157", "", "NOS"),
    ("Remotes and Receiver Kits", "RECEIVER KIT BRC7M632 F-6", "", "NOS"),
    ("Remotes and Receiver Kits", "REMOTE BRC91A152", "", "NOS"),
    ("Daikin AC", "RA IDU (7.1 KW 2.02 TR   INV)", "GTKL71UV16M", "NOS"),
    ("Daikin AC", "RA ODU (7.1 KW 2.02 TR INV)", "RKLG71UV16M", "NOS"),
    ("Daikin AC", "RA IDU (6.0 KW 1.8 TR 3 STAR INV)", "FTHT60XVI6UAA", "NOS"),
    ("Daikin AC", "RA ODU (6.0 KW 1.8 TR 3 STAR INV)", "RHT60XV16UAA", "NOS"),
    ("Daikin AC", "VRV - IDU LARGE DUCT UNIT", "FXMQ250NVE6", "NOS"),
    ("Daikin AC", "ROUND FLOW CASSETTE UNIT 2.65 TR", "FXFSQ80ARV16", "NOS"),
    ("Daikin AC", "DECORATIVE PANNEL FOR ROUND FLOW CASSETTE", "BYCQ125EAF6", "NOS"),
    ("Daikin AC", "VRV 1 WAY CASSETTE IDU -2 TR", "FXKQ63ARV16", "NOS"),
    ("Daikin AC", "PA DUCT IDU - NON INV", "FDR100FRV16", "NOS"),
    ("Daikin AC", "PA DUCT ODU NON INV", "RR100FRY16", "NOS"),
    ("Daikin AC", "VRV IDU LARGE DUCT", "FXMQ170NVE6", "NOS"),
    ("Daikin AC", "SA CASSETTE INV IDU 2.0 TR", "FCA71AV16", "NOS"),
    ("Daikin AC", "SA CASSETTE IN ODU 2.0 TR", "RZCA71AV16", "NOS"),
    ("Daikin AC", "SA CASSETTE INV IDU 1.5 TR", "FCA50AV16", "NOS"),
    ("Daikin AC", "SA CASSETTE INV ODU 1.5 TR", "RZCA50AV16", "NOS"),
    ("Daikin AC", "PA DUCT IDU NON INVERTER UNIT", "FDR65FRV16", "NOS"),
    ("Daikin AC", "PA DUCT ODU NON INVERTER UNIT", "RR65FRY16", "NOS"),
    ("Daikin AC", "SA CASSETTE INVERTER IDU 3.5 TR", "FCA125AV16", "NOS"),
    ("Daikin AC", "SA CASSETTE INVERTER ODU 3.5 TR", "RZCA125AV16", "NOS"),
    ("Daikin AC", "GAS TIGHT DGT JOINTS", "SDGTB2825", "NOS"),
    ("Daikin AC", "GAS TIGHT DGT JOINTS", "SDGTB2219", "NOS"),
    ("Daikin AC", "SA DUCT INVERTER IDU 2.0 TR", "FDMA71AV16", "NOS"),
    ("Daikin AC", "SA DUCT INVERTER ODU 2.0 TR", "RZA71AV16", "NOS"),
    ("Daikin AC", "VRV INDOOR UNIT 1.6 HP", "FXAQ40ARVE6", "NOS"),
    ("Daikin AC", "VRV INDOOR UNIT 2.0 HP", "FXAQ50ARVE6", "NOS"),
    ("Daikin AC", "VRV HIGHWALL 2.5 HP", "FXAQ63ARVE6", "NOS"),
    ("Daikin AC", "VRV 1 WAY CASSETTE IDU -1.65 TR", "FXKQ50ARV16", "NOS"),
    ("Daikin AC", "RA IDU 3.5 KW INVERTER UNIT", "GTKM35UV16WA", "NOS"),
    ("Daikin AC", "RA ODU 3.5 KM INVERTER UNIT", "RKMG35UV16WA", "NOS"),
    ("Daikin AC", "RA IDU 1.5 TR INVERTER  UNIT", "GTKM50UV16WA", "NOS"),
    ("Daikin AC", "RA ODU 1.5 TR INVERTER UNIT", "RKMG50UV16VA", "NOS"),
    ("Daikin AC", "RA IDU 1.0 TR UNIT", "FTHT35XV16WAA", "NOS"),
    ("Daikin AC", "RA OUD 1.0 TR UNIT", "RHT35XV16WAA", "NOS"),
    ("Daikin AC", "SA CASSETTE UNIT INDOOR NON VRV", "FCQF24ARV16", "NOS"),
    ("Daikin AC", "SA CASSETTE UNIT OUTDOOR NON VRV", "RGVF24ASV16", "NOS"),
    ("Daikin AC", "DECORATIVE PANNEL FOR CASSETTE UNIT", "BYCQ48EAF6", "NOS"),
    ("Daikin AC", "PA DUCT INDOOR UNIT NON VRV", "FDR130FRV16", "NOS"),
    ("Daikin AC", "VRV HSP DUCT INDOOR UNIT", "FXMQ125PBV36", "NOS"),
    ("Daikin AC", "PA DUCT OUTDOOR UNIT", "RR130FRY16", "NOS"),
    ("Daikin AC", "VRV HSP DUCT INDOOR UNIT", "FXMQ50PBV36", "NOS"),
    ("Daikin AC", "ONE WAY CASSETTE PANNEL", "BYKQ63AHW", "NOS"),
    ("Daikin AC", "VRV 6 HEAT PUMP", "RXYQ12BRY16", "NOS"),
    ("Daikin AC", "VRV 24 HP OUTDOOR UNIT", "RXYQ24BRY16", "NOS"),
    ("Daikin AC", "GAS TIGHT DGT JOINTS", "SDGTB1209", "NOS"),
    ("Daikin AC", "VRV CASSETTE UNIT 1.32 TR", "FXKQ40ARV16", "NOS"),
]


def add_items(apps, schema_editor):
    StoreCategory = apps.get_model("store", "StoreCategory")
    StoreItem = apps.get_model("store", "StoreItem")

    for category_name, description, size, unit in ITEMS:
        category, _ = StoreCategory.objects.get_or_create(
            category_name=category_name
        )
        normalized_description = description.upper()
        is_vrv = "VRV" in normalized_description and "NON VRV" not in normalized_description
        last_item = StoreItem.objects.order_by("-id").first()
        new_id = last_item.id + 1 if last_item else 1

        StoreItem.objects.get_or_create(
            category=category,
            item_description=description,
            size=size,
            remarks="",
            defaults={
                "item_code": f"STK{new_id:04d}",
                "unit": unit,
                "is_vrv": is_vrv,
                "is_non_vrv": not is_vrv,
                "opening_stock": 0,
                "current_stock": 0,
                "minimum_stock": 0,
            },
        )


def remove_items(apps, schema_editor):
    StoreCategory = apps.get_model("store", "StoreCategory")
    StoreItem = apps.get_model("store", "StoreItem")

    for category_name, description, size, _unit in ITEMS:
        try:
            category = StoreCategory.objects.get(category_name=category_name)
        except StoreCategory.DoesNotExist:
            continue

        StoreItem.objects.filter(
            category=category,
            item_description=description,
            size=size,
            remarks="",
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0009_storeitem_is_non_vrv"),
    ]

    operations = [
        migrations.RunPython(add_items, remove_items),
    ]
