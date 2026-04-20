from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category, Vehicle
from .serializers import CategorySerializer, VehicleSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by("parking_area_no", "vehicle_type")
    serializer_class = CategorySerializer


class VehicleViewSet(viewsets.ModelViewSet):
    queryset = Vehicle.objects.select_related("category", "recorded_by").all()
    serializer_class = VehicleSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(vehicle_no__icontains=q) | Q(receipt_serial__icontains=q))
        return qs

    @action(detail=True, methods=["post"])
    def depart(self, request, pk=None):
        vehicle = self.get_object()
        try:
            notify = False
            if request.user.is_authenticated:
                try:
                    notify = request.user.administrator.email_departure_notifications
                except Exception:
                    notify = False
            vehicle.mark_departed(end=timezone.now(), notify=notify)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(VehicleSerializer(vehicle).data)
