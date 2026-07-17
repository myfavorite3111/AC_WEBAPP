from django.db import migrations


def restore_all_item_type_flags(apps, schema_editor):
    StoreItem = apps.get_model("store", "StoreItem")

    for item in StoreItem.objects.all().iterator():
        description = (item.item_description or "").upper()

        is_non_vrv = "NON VRV" in description or "NON-VRV" in description
        is_vrv = "VRV" in description and not is_non_vrv

        if is_vrv:
            item.is_vrv = True
            item.is_non_vrv = False
        elif is_non_vrv:
            item.is_vrv = False
            item.is_non_vrv = True
        elif not item.is_vrv and not item.is_non_vrv:
            item.is_non_vrv = True

        item.save(update_fields=["is_vrv", "is_non_vrv"])


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0012_alter_storeitem_is_non_vrv"),
    ]

    operations = [
        migrations.RunPython(restore_all_item_type_flags, migrations.RunPython.noop),
    ]
