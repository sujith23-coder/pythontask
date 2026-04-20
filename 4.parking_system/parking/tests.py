from datetime import timedelta
from decimal import Decimal

from django.test import TestCase

from .models import Category, Vehicle


class ParkingModelTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(
            parking_area_no="2",
            vehicle_type="Car",
            vehicle_limit=2,
            parking_charge=Decimal("4.00"),
        )

    def test_capacity_and_exit_fee(self):
        self.assertTrue(self.cat.can_accept_vehicle())
        Vehicle.objects.create(
            vehicle_no="ABC-1",
            parking_area_no=self.cat.parking_area_no,
            category=self.cat,
            vehicle_type=self.cat.vehicle_type,
            parking_charge=self.cat.parking_charge,
        )
        Vehicle.objects.create(
            vehicle_no="ABC-2",
            parking_area_no=self.cat.parking_area_no,
            category=self.cat,
            vehicle_type=self.cat.vehicle_type,
            parking_charge=self.cat.parking_charge,
        )
        self.assertFalse(self.cat.can_accept_vehicle())
        v = Vehicle.objects.get(vehicle_no="ABC-1")
        v.mark_departed(end=v.arrival_time + timedelta(hours=2))
        self.assertEqual(v.status, Vehicle.Status.LEAVED)
        self.assertEqual(v.total_fee, Decimal("8.00"))
