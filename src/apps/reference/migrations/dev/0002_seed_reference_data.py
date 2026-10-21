from django.db import migrations

from apps.reference.seed import seed_reference_data


def seed(apps, schema_editor):
    seed_reference_data(apps)


class Migration(migrations.Migration):

    dependencies = [
        ("reference", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
