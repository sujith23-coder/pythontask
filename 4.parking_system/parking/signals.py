from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Administrator


@receiver(post_save, sender=User)
def create_administrator_profile(sender, instance, created, **kwargs):
    if not created:
        return
    if instance.is_staff or instance.is_superuser:
        Administrator.objects.get_or_create(
            user=instance,
            defaults={"name": instance.get_full_name() or instance.username},
        )
