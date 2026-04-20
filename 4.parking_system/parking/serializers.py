from rest_framework import serializers

from .models import Category, Vehicle


class CategorySerializer(serializers.ModelSerializer):
    parked_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "parking_area_no",
            "vehicle_type",
            "vehicle_limit",
            "parking_charge",
            "status",
            "doc",
            "parked_count",
        ]
        read_only_fields = ["doc", "parked_count"]

    def get_parked_count(self, obj):
        return obj.parked_count()


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id",
            "receipt_serial",
            "vehicle_no",
            "parking_area_no",
            "category",
            "vehicle_type",
            "parking_charge",
            "status",
            "arrival_time",
            "departure_time",
            "total_fee",
            "recorded_by",
        ]
        read_only_fields = [
            "receipt_serial",
            "arrival_time",
            "departure_time",
            "total_fee",
            "recorded_by",
            "status",
        ]

    def validate(self, attrs):
        if self.instance is None:
            vehicle_no = attrs.get("vehicle_no", "")
            if Vehicle.active_plate(vehicle_no):
                raise serializers.ValidationError({"vehicle_no": "Vehicle already parked."})
            cat = attrs.get("category")
            if cat and not cat.can_accept_vehicle():
                raise serializers.ValidationError({"category": "Category at capacity or inactive."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        cat = validated_data["category"]
        validated_data["parking_area_no"] = cat.parking_area_no
        validated_data["vehicle_type"] = cat.vehicle_type
        validated_data["parking_charge"] = cat.parking_charge
        validated_data["status"] = Vehicle.Status.PARKED
        if request and request.user.is_authenticated:
            validated_data["recorded_by"] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        cat = validated_data.get("category", instance.category)
        if "category" in validated_data:
            validated_data["parking_area_no"] = cat.parking_area_no
            validated_data["vehicle_type"] = cat.vehicle_type
            validated_data["parking_charge"] = cat.parking_charge
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        return instance
