from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from .models import Category, Vehicle


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["parking_area_no", "vehicle_type", "vehicle_limit", "parking_charge", "status"]
        widgets = {
            "parking_area_no": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_type": forms.TextInput(attrs={"class": "form-control"}),
            "vehicle_limit": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "parking_charge": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": 0}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class VehicleEntryForm(forms.Form):
    vehicle_no = forms.CharField(max_length=200, widget=forms.TextInput(attrs={"class": "form-control"}))
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(status=Category.Status.ACTIVATED),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_vehicle_no(self):
        v = self.cleaned_data["vehicle_no"].strip()
        if Vehicle.active_plate(v):
            raise forms.ValidationError("This vehicle is already parked.")
        return v

    def clean_category(self):
        cat = self.cleaned_data["category"]
        if not cat.can_accept_vehicle():
            raise forms.ValidationError("Parking limit reached for this category.")
        return cat


class AccountPasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].widget.attrs.update({"class": "form-control"})
