from decimal import Decimal
from math import ceil

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.conf import settings
from django.utils import timezone


class Administrator(models.Model):
    """Maps to assignment `admin` table — extends Django auth user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="administrator")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=32, blank=True)
    email_departure_notifications = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return self.name or self.user.get_username()


class Category(models.Model):
    """Maps to `category` — parking area, vehicle type, limit, charge, status."""

    class Status(models.TextChoices):
        ACTIVATED = "activated", "Activated"
        DEACTIVATED = "deactivated", "Deactivated"

    parking_area_no = models.CharField(max_length=100, db_index=True)
    vehicle_type = models.CharField(max_length=100)
    vehicle_limit = models.PositiveIntegerField(default=10)
    parking_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("2.00"))
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVATED, db_index=True
    )
    doc = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["parking_area_no", "vehicle_type"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.vehicle_type} (Area {self.parking_area_no})"

    def parked_count(self) -> int:
        return self.vehicles.filter(status=Vehicle.Status.PARKED).count()

    def can_accept_vehicle(self) -> bool:
        if self.status != self.Status.ACTIVATED:
            return False
        return self.parked_count() < self.vehicle_limit


class Vehicle(models.Model):
    """Maps to `add_vehicle` — parking sessions with receipt for search."""

    class Status(models.TextChoices):
        PARKED = "parked", "Parked"
        LEAVED = "leaved", "Leaved"

    receipt_serial = models.CharField(max_length=32, unique=True, editable=False, db_index=True, null=True, blank=True)
    vehicle_no = models.CharField(max_length=200, db_index=True)
    parking_area_no = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="vehicles")
    vehicle_type = models.CharField(max_length=200)
    parking_charge = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PARKED, db_index=True)
    arrival_time = models.DateTimeField(default=timezone.now)
    departure_time = models.DateTimeField(null=True, blank=True)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    recorded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="parking_entries"
    )

    class Meta:
        ordering = ["-arrival_time"]

    def __str__(self):
        return f"{self.vehicle_no} — {self.receipt_serial}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.receipt_serial:
            self.receipt_serial = f"PMS-{self.pk:06d}"
            super().save(update_fields=["receipt_serial"])

    @classmethod
    def active_plate(cls, vehicle_no: str):
        return cls.objects.filter(
            vehicle_no__iexact=vehicle_no.strip(),
            status=cls.Status.PARKED,
        ).first()

    def billable_hours(self, end=None) -> int:
        end = end or timezone.now()
        if self.arrival_time >= end:
            return 1
        secs = (end - self.arrival_time).total_seconds()
        return max(1, ceil(secs / 3600))

    def compute_exit_fee(self, end=None) -> Decimal:
        hours = self.billable_hours(end)
        return (self.parking_charge * hours).quantize(Decimal("0.01"))

    def mark_departed(self, end=None, notify=False):
        if self.status != self.Status.PARKED:
            raise ValueError("Vehicle is not parked.")
        end = end or timezone.now()
        self.departure_time = end
        self.total_fee = self.compute_exit_fee(end)
        self.status = self.Status.LEAVED
        self.save(update_fields=["departure_time", "total_fee", "status"])

        if notify and self.recorded_by_id:
            try:
                admin = self.recorded_by.administrator
            except Administrator.DoesNotExist:
                admin = None
            if admin and admin.email_departure_notifications and self.recorded_by.email:
                send_mail(
                    subject=f"Vehicle departed — {self.vehicle_no}",
                    message=f"Receipt {self.receipt_serial}. Fee: ${self.total_fee}.",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@local"),
                    recipient_list=[self.recorded_by.email],
                    fail_silently=True,
                )
