from django.db import models


class BlogUser(models.Model):
    """Read-only mapping to SQLAlchemy `users` table (FastAPI auth)."""

    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=64)
    email = models.CharField(max_length=255)
    hashed_password = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "users"


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Plan cost in INR")
    duration = models.PositiveIntegerField(help_text="Duration in days")

    class Meta:
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} ({self.price} INR / {self.duration}d)"


class BillingHistory(models.Model):
    user = models.ForeignKey(BlogUser, on_delete=models.CASCADE, related_name="billing_records")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="billing_records")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    invoice = models.CharField(max_length=500, help_text="Path to generated invoice PDF")
    transaction_id = models.CharField(max_length=64, blank=True, help_text="Unique transaction reference")

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"Billing #{self.id} — {self.user_id}"
