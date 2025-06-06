from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Device, DeviceToken

@receiver(post_save, sender=Device)
def create_token_for_device(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'token'):
        DeviceToken.objects.create(esp=instance)
