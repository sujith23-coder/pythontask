from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import CategoryViewSet, VehicleViewSet

app_name = "parking"

router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="api-category")
router.register(r"vehicles", VehicleViewSet, basename="api-vehicle")

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("categories/", views.category_manage, name="categories"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/toggle/", views.category_toggle, name="category_toggle"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("vehicle-entry/", views.vehicle_entry, name="vehicle_entry"),
    path("manage-vehicles/", views.manage_vehicles, name="manage_vehicles"),
    path("vehicles/<int:pk>/done/", views.vehicle_done, name="vehicle_done"),
    path("vehicles/<int:pk>/receipt/", views.receipt, name="receipt"),
    path("reports/", views.reports, name="reports"),
    path("search/", views.search_vehicles, name="search"),
    path("account/", views.account_settings, name="account"),
    path("api/", include(router.urls)),
]
