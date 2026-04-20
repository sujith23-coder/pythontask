from django.contrib import admin

from .models import Administrator, Category, Vehicle


@admin.register(Administrator)
class AdministratorAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "phone", "email_departure_notifications")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("parking_area_no", "vehicle_type", "vehicle_limit", "parking_charge", "status", "doc")
    list_filter = ("status",)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_serial",
        "vehicle_no",
        "vehicle_type",
        "parking_area_no",
        "status",
        "arrival_time",
        "total_fee",
    )
    list_filter = ("status",)
    search_fields = ("vehicle_no", "receipt_serial")
