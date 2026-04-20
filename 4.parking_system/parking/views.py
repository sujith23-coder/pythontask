from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import AccountPasswordForm, CategoryForm, VehicleEntryForm
from .models import Administrator, Category, Vehicle


def _dashboard_stats():
    parked = Vehicle.objects.filter(status=Vehicle.Status.PARKED).count()
    leaved = Vehicle.objects.filter(status=Vehicle.Status.LEAVED).count()
    active_categories = Category.objects.filter(status=Category.Status.ACTIVATED).count()
    earnings = (
        Vehicle.objects.filter(status=Vehicle.Status.LEAVED).aggregate(t=Sum("total_fee"))["t"]
        or 0
    )
    total_records = Vehicle.objects.count()
    slots = (
        Category.objects.filter(status=Category.Status.ACTIVATED).aggregate(s=Sum("vehicle_limit"))["s"]
        or 0
    )
    return {
        "stat_parked": parked,
        "stat_leaved": leaved,
        "stat_categories": active_categories,
        "stat_earnings": earnings,
        "stat_records": total_records,
        "stat_slots": slots,
    }


def login_view(request):
    if request.user.is_authenticated:
        return redirect("parking:dashboard")
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = User.objects.filter(username=username).first()
        if user and user.check_password(password) and user.is_staff:
            login(request, user)
            Administrator.objects.get_or_create(
                user=user, defaults={"name": user.get_full_name() or user.username}
            )
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect("parking:dashboard")
        error = "Invalid credentials or not an administrator."
    return render(request, "parking/login.html", {"error": error})


@login_required
def dashboard(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    ctx = _dashboard_stats()
    ctx["nav"] = "dashboard"
    return render(request, "parking/dashboard.html", ctx)


@login_required
def category_manage(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Category added.")
            return redirect("parking:categories")
    else:
        form = CategoryForm()
    categories = Category.objects.all().order_by("parking_area_no")
    summary = [(c.vehicle_type, c.parking_charge) for c in categories if c.status == Category.Status.ACTIVATED]
    ctx = {
        "form": form,
        "categories": categories,
        "summary_charges": summary,
        "nav": "categories",
    }
    return render(request, "parking/categories.html", ctx)


@login_required
def category_edit(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=cat)
        if form.is_valid():
            form.save()
            messages.success(request, "Category updated.")
            return redirect("parking:categories")
    else:
        form = CategoryForm(instance=cat)
    return render(
        request,
        "parking/category_edit.html",
        {"form": form, "category": cat, "nav": "categories"},
    )


@login_required
def category_toggle(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        if cat.status == Category.Status.ACTIVATED:
            cat.status = Category.Status.DEACTIVATED
        else:
            cat.status = Category.Status.ACTIVATED
        cat.save(update_fields=["status"])
        messages.success(request, f"Category {cat.get_status_display()}.")
    return redirect("parking:categories")


@login_required
def category_delete(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    cat = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        cat.delete()
        messages.success(request, "Category deleted.")
    return redirect("parking:categories")


@login_required
def vehicle_entry(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    if request.method == "POST":
        form = VehicleEntryForm(request.POST)
        if form.is_valid():
            cat = form.cleaned_data["category"]
            v = Vehicle.objects.create(
                vehicle_no=form.cleaned_data["vehicle_no"].strip(),
                category=cat,
                parking_area_no=cat.parking_area_no,
                vehicle_type=cat.vehicle_type,
                parking_charge=cat.parking_charge,
                status=Vehicle.Status.PARKED,
                recorded_by=request.user,
            )
            messages.success(request, f"Vehicle checked in. Receipt: {v.receipt_serial}")
            return redirect("parking:vehicle_entry")
    else:
        form = VehicleEntryForm()
    parked = Vehicle.objects.filter(status=Vehicle.Status.PARKED).select_related("category")
    limits = []
    for c in Category.objects.filter(status=Category.Status.ACTIVATED).order_by("vehicle_type"):
        limits.append(
            {
                "label": c.vehicle_type,
                "parked": c.parked_count(),
                "limit": c.vehicle_limit,
            }
        )
    ctx = {
        "form": form,
        "parked_now": parked,
        "limits": limits,
        "nav": "entry",
    }
    return render(request, "parking/vehicle_entry.html", ctx)


@login_required
def manage_vehicles(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    cutoff = timezone.now() - timedelta(days=30)
    vehicles = (
        Vehicle.objects.filter(arrival_time__gte=cutoff)
        .select_related("category")
        .order_by("-arrival_time")
    )
    return render(
        request,
        "parking/manage_vehicles.html",
        {"vehicles": vehicles, "nav": "manage"},
    )


@login_required
def vehicle_done(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST" and vehicle.status == Vehicle.Status.PARKED:
        try:
            notify = False
            try:
                notify = request.user.administrator.email_departure_notifications
            except Administrator.DoesNotExist:
                pass
            vehicle.mark_departed(notify=notify)
            messages.success(request, f"Marked departed. Fee: ${vehicle.total_fee}")
        except ValueError as e:
            messages.error(request, str(e))
    return redirect("parking:manage_vehicles")


@login_required
def reports(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    now = timezone.now()
    period_start = (now - timedelta(days=9)).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = (
        Vehicle.objects.filter(arrival_time__gte=period_start, arrival_time__lte=now)
        .annotate(day=TruncDate("arrival_time"))
        .values("day")
        .annotate(entries=Count("id"), revenue=Sum("total_fee"))
        .order_by("day")
    )
    ctx = {
        "report_rows": rows,
        "period_start": period_start.date(),
        "period_end": now.date(),
        "nav": "reports",
    }
    return render(request, "parking/reports.html", ctx)


@login_required
def search_vehicles(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    q = request.GET.get("q", "").strip()
    cutoff = timezone.now() - timedelta(days=30)
    vehicles = Vehicle.objects.none()
    if q:
        vehicles = (
            Vehicle.objects.filter(
                Q(vehicle_no__icontains=q) | Q(receipt_serial__icontains=q),
                arrival_time__gte=cutoff,
            )
            .select_related("category")
            .order_by("-arrival_time")
        )
    return render(
        request,
        "parking/search.html",
        {"vehicles": vehicles, "q": q, "nav": "search"},
    )


@login_required
def account_settings(request):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    admin, _ = Administrator.objects.get_or_create(
        user=request.user,
        defaults={"name": request.user.get_full_name() or request.user.username},
    )
    if request.method == "POST":
        if request.POST.get("save_notifications"):
            admin.email_departure_notifications = request.POST.get("email_notifications") == "on"
            admin.save(update_fields=["email_departure_notifications"])
            messages.success(request, "Notification preference saved.")
            return redirect("parking:account")
        form = AccountPasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Password updated.")
            return redirect("parking:account")
    else:
        form = AccountPasswordForm(user=request.user)
    return render(
        request,
        "parking/account.html",
        {"form": form, "admin_profile": admin, "nav": "account"},
    )


@login_required
def receipt(request, pk):
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access only.")
    vehicle = get_object_or_404(Vehicle, pk=pk)
    return render(request, "parking/receipt.html", {"vehicle": vehicle, "nav": "entry"})
