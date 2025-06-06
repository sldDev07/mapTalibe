from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import secrets

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('serigne', 'Serigne Daara'),
        ('ndeye', 'Ndèye Daara'),
        ('parent', 'Parent'),
    ]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    téléphone = models.CharField(max_length=20, blank=False, null=True)
    email=models.EmailField(blank=False, null=True, max_length=254, verbose_name='Adresse éléctronique')
    first_name=models.CharField(blank=False, null=True, max_length=100, verbose_name="Prénom")
    last_name=models.CharField(blank=False, null=True, max_length=100, verbose_name="Nom")
    nom_daara=models.CharField(blank=False, null=True, max_length=100, verbose_name="Nom de votre Daara")

class Device(models.Model):
    esp_id = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.esp_id
class DeviceToken(models.Model):
    esp = models.OneToOneField('Device', on_delete=models.CASCADE, related_name='token')
    key = models.CharField(max_length=64, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = secrets.token_hex(32)  # Génère une clé unique de 64 caractères
        super().save(*args, **kwargs)




class Enfant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField()
    id_esp32 = models.CharField(max_length=100, unique=True, verbose_name="Id de l'appareil")
    provenance=models.CharField(max_length=100, blank=False, null=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enfants")
    parents = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enfants_parents', blank=True)
    parrains = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='enfants_parrains', blank=True)
    appareil = models.OneToOneField('Device', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"

class Meta:
    verbose_name = "Enfant"
    verbose_name_plural = "Enfants"

class DemandeAssociation(models.Model):
    ROLE_CHOIX = [
        ('parent', 'Parent'),
        ('ndeye', 'Ndèye Daara'),
    ]
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('accepte', 'Acceptée'),
        ('refuse', 'Refusée'),
    ]
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    enfant = models.ForeignKey(Enfant, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOIX, null=True)
    date = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    def __str__(self):
        return f"{self.utilisateur.username} demande à suivre {self.enfant.nom}"
