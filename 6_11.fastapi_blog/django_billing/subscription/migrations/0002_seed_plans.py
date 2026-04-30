from django.db import migrations


def seed_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscription", "SubscriptionPlan")
    plans = [
        ("Basic", 299, 30),
        ("Pro", 799, 30),
        ("Premium", 1499, 90),
    ]
    for name, price, duration in plans:
        SubscriptionPlan.objects.get_or_create(name=name, defaults={"price": price, "duration": duration})


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("subscription", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(name__in=["Basic", "Pro", "Premium"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("subscription", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed),
    ]
