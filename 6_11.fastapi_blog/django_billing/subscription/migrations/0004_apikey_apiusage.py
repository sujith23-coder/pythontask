from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("subscription", "0003_add_transaction_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="APIKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_keys",
                        to="subscription.bloguser",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="APIUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.CharField(max_length=255)),
                ("total_requests", models.PositiveIntegerField(default=0)),
                ("last_used", models.DateTimeField(auto_now=True)),
                ("usage_date", models.DateField(default=django.utils.timezone.localdate)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_usage_records",
                        to="subscription.bloguser",
                    ),
                ),
            ],
            options={
                "ordering": ["-last_used"],
            },
        ),
        migrations.AddConstraint(
            model_name="apiusage",
            constraint=models.UniqueConstraint(
                fields=("user", "endpoint", "usage_date"), name="uq_usage_user_endpoint_day"
            ),
        ),
    ]
