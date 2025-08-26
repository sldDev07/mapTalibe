from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .forms import EnfantForm,InscriptionForm, AssocierEnfantViaESP32Form
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from .models import Enfant, Device, DeviceToken, DemandeAssociation, CustomUser
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json, os, traceback
from datetime import datetime
from twilio.rest import Client
from math import radians, cos, sin, asin, sqrt
from geopy.distance import distance  
from django.contrib.auth import update_session_auth_hash
from django.core.mail import send_mail


def accueil(request):
    return render(request, 'trackingtalibe/accueil.html')

def register(request):
    role_selected = request.GET.get('role_selection', 'parent')

    if request.method == 'POST':
        form = InscriptionForm(request.POST, role_selected=role_selected)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = request.POST.get('role', role_selected)
            user.save()
            return redirect('login')  # Correction ici
    else:
        form = InscriptionForm(role_selected=role_selected)

    return render(request, 'trackingtalibe/register.html', {
        'form': form,
        'role_selected': role_selected,
    })



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('redirection_espace')
    else:
        form = AuthenticationForm()
    return render(request, 'trackingtalibe/login.html', {'form': form})

def deconnexion_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('accueil')

@login_required
def redirection_espace(request):
    if request.user.role == 'serigne':
        return redirect('espace_serigne')
    elif request.user.role == 'ndeye':
        return redirect('espace_ndeye')
    elif request.user.role == 'parent':
        return redirect('espace_parent')
    else:
        return redirect('login_view')
@login_required
def espace_serigne(request):
    if request.user.role != 'serigne':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    enfants = Enfant.objects.filter(responsable=request.user)
    return render(request, 'trackingtalibe/espace_serigne.html', {'enfants': enfants,'active_page': 'dashboard'})

@login_required
def espace_ndeye(request):
    if request.user.role != 'ndeye':
        return HttpResponse("<h3>Accès non autorisé </h3>")
    
    enfants = request.user.enfants_parrains.all()
    demandes_en_attente = DemandeAssociation.objects.filter(utilisateur=request.user)
    
    return render(request, 'trackingtalibe/espace_ndeye.html', {'enfants': enfants, 'active_page': 'dashboard'})

@login_required
def espace_parent(request):
    if request.user.role != 'parent':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    enfants = request.user.enfants_parents.all()
    demandes_en_attente = DemandeAssociation.objects.filter(utilisateur=request.user)
    
    return render(request, 'trackingtalibe/espace_parent.html', {'enfants': enfants, 'active_page': 'dashboard'})
@login_required
def ajouter_enfant(request):
    if request.user.role != 'serigne':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    if request.method == 'POST':
        form = EnfantForm(request.POST)
        if form.is_valid():
            enfant = form.save(commit=False)
            enfant.responsable = request.user
            # Associe automatiquement le Daara du Serigne
            enfant.daara = request.user.daaras.first()
            enfant.save()
            return redirect('ajouter_enfant')
    else:
        form = EnfantForm()

    return render(request, 'trackingtalibe/ajouter_enfant.html', {'form': form})

@login_required
def associer_par_code(request):
    if request.user.role == 'serigne':
        return HttpResponse("<h3>Accès non autorisé </h3>")
    
    if request.method == 'POST':
        form = AssocierEnfantViaESP32Form(request.POST)
        if form.is_valid():
            id_esp32 = form.cleaned_data['id_esp32']
            try:
                enfant = Enfant.objects.get(id_esp32=id_esp32)
                # Créer une demande d’association
                DemandeAssociation.objects.get_or_create(
                    utilisateur=request.user,
                    enfant=enfant,
                    role=request.user.role
                )
                messages.success(request, "Votre demande a été envoyée au Serigne Daara.")
                return redirect('associer_par_code')
            except Enfant.DoesNotExist:
                messages.error(request, "Aucun enfant avec cet ID ESP32 n’a été trouvé.")
    else:
        form = AssocierEnfantViaESP32Form()

    demandes_existantes = DemandeAssociation.objects.filter(utilisateur=request.user, statut='en_attente').select_related('enfant').order_by('date')
    return render(request, 'trackingtalibe/associer_par_code.html', {
    'form': form,
    'demandes_existantes': demandes_existantes,
})


# Config Twilio
Twilio_SID = settings.TWILIO_SID
Twilio_TOKEN = settings.TWILIO_TOKEN
Twilio_NUMERO = settings.TWILIO_NUMERO

# Position du Daara
# LAT = settings.DAARA_LAT
# LON = settings.DAARA_LON
# RAYON = settings.RAYON_SECURITE


def envoyer_alerte_sms(enfant, lat, lon):
    url_suivi = f"https://maptalibe.com/enfant/{enfant.id}/suivre/"
    
    msg = (
        f"Alerte : {enfant.nom} {enfant.prenom} a quitté le périmètre du Daara. Veuillez vous connecter pour le suivre immédiatement.\n"
    )

    client = Client(Twilio_SID, Twilio_TOKEN)

    contacts = set()
    if enfant.responsable and enfant.responsable.téléphone:
        contacts.add(enfant.responsable.téléphone)
    contacts.update(enfant.parents.values_list('téléphone', flat=True))
    contacts.update(enfant.parrains.values_list('téléphone', flat=True))

    for numero in contacts:
        if numero:  # Vérifie que le numéro existe
            client.messages.create(
                body=msg,
                from_=Twilio_NUMERO,
                to=numero
            )

def envoyer_alerte_email(enfant, lat, lon):
    url_suivi = f"https://maptalibe.com/enfant/{enfant.id}/suivre/"
    
    sujet = f"Alerte – {enfant.nom} {enfant.prenom} a quitté le Daara"
    message = (
        f"Bonjour,\n\n"
        f"⚠️ Alerte : {enfant.nom} {enfant.prenom} a quitté le périmètre de sécurité du Daara.\n"
        f"Suivez sa position en temps réel ici : {url_suivi}\n\n"
        f"Coordonnées :\nLatitude : {lat}\nLongitude : {lon}\n\n"
        f"– MapTalibé"
    )

    destinataires = set()
    if enfant.responsable and enfant.responsable.email:
        destinataires.add(enfant.responsable.email)
    destinataires.update(enfant.parents.values_list('email', flat=True))
    destinataires.update(enfant.parrains.values_list('email', flat=True))

    for email in destinataires:
        if email:
            send_mail(
                sujet,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )


@csrf_exempt
def enregistrer_position(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            id_esp32 = data.get('id_esp32')
            lat = data.get('latitude')
            lon = data.get('longitude')

            if not id_esp32 or lat is None or lon is None:
                return JsonResponse({'error': 'id_esp32, latitude et longitude requis'}, status=400)

            json_path = os.path.join('data', 'latlng.json')
            os.makedirs('data', exist_ok=True)

            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    try:
                        content = f.read().strip()
                        positions = json.loads(content) if content else {}
                    except json.JSONDecodeError:
                        positions = {}
            else:
                positions = {}

            ancienne = positions.get(id_esp32, {})
            alert_deja_envoyee = ancienne.get('alert_sent', False)

            enfant = Enfant.objects.filter(id_esp32=id_esp32).first()
            if enfant:
                lat = enfant.daara.latitude
                lon = enfant.daara.longitude
                rayon = enfant.daara.rayon_securite_metres

                distance_metres = distance((lat, lon), (LAT, LON)).m
                en_dehors = distance_metres > RAYON_SECURITE

                if en_dehors and not alert_deja_envoyee:
                    envoyer_alerte_email(enfant, lat, lon)
                    envoyer_alerte_sms(enfant, lat, lon)
                    alert_deja_envoyee = True

                if not en_dehors:
                    alert_deja_envoyee = False

            positions[id_esp32] = {
                'latitude': round(lat, 8),
                'longitude': round(lon, 8),
                'timestamp': datetime.now().isoformat(),
                'alert_sent': alert_deja_envoyee
            }

            with open(json_path, 'w') as f:
                json.dump(positions, f, indent=2)

            return JsonResponse({'message': 'Position enregistrée'})

        except Exception as e:
            print("Erreur:", e)
            print(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)



@login_required
def get_position_enfant(request, enfant_id):
    enfant = get_object_or_404(Enfant, id=enfant_id)

    # Vérifie les droits d’accès
    if request.user != enfant.responsable and \
       request.user not in enfant.parents.all() and \
       request.user not in enfant.parrains.all():
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    json_path = os.path.join('data', 'latlng.json')

    try:
        with open(json_path, 'r') as f:
            positions = json.load(f)

        esp_id = enfant.id_esp32

        if esp_id not in positions:
            return JsonResponse({'error': 'Position non trouvée'}, status=404)

        pos = positions[esp_id]
        return JsonResponse({
            'latitude': pos['latitude'],
            'longitude': pos['longitude'],
            'timestamp': pos.get('timestamp')
        })

    except FileNotFoundError:
        return JsonResponse({'error': 'Fichier introuvable'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Fichier mal formé'}, status=500)



@login_required
def suivre_enfant(request, enfant_id):
    enfant = get_object_or_404(Enfant, id=enfant_id)
    id_esp32 = enfant.id_esp32

    file_path = os.path.join(settings.BASE_DIR, 'data', 'latlng.json')
    latitude = None
    longitude = None
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            positions = json.load(f)
        if id_esp32 in positions:
            latitude = float(positions[id_esp32]['latitude'])
            longitude = float(positions[id_esp32]['longitude'])

    # Correction : passe les coordonnées du Daara comme chaîne formatée
    daara_latitude = str(enfant.daara.latitude) if enfant.daara and enfant.daara.latitude is not None else ""
    daara_longitude = str(enfant.daara.longitude) if enfant.daara and enfant.daara.longitude is not None else ""

    context = {
        'enfant': enfant,
        'MAPBOX_TOKEN': settings.MAPBOX_TOKEN,
        'latitude': latitude,
        'longitude': longitude,
        'daara_latitude': daara_latitude,
        'daara_longitude': daara_longitude,
    }
    return render(request, 'trackingtalibe/suivre_enfant.html', context)
    
@login_required
def modifier_enfant(request, pk):
    enfant = get_object_or_404(Enfant, pk=pk, responsable=request.user)
    if request.method == 'POST':
        form = EnfantForm(request.POST, instance=enfant)
        if form.is_valid():
            form.save()
            messages.success(request, "Enfant modifié avec succès.")
            return redirect('espace_serigne')
    else:
        form = EnfantForm(instance=enfant)
    return render(request, 'trackingtalibe/ajouter_enfant.html', {'form': form})

@login_required
def supprimer_enfant(request, pk):
    enfant = get_object_or_404(Enfant, pk=pk, responsable=request.user)
    enfant.delete()
    messages.success(request, "Enfant supprimé.")
    return redirect('espace_serigne')

class CustomPasswordResetView(PasswordResetView):
    template_name = 'trackingtalibe/password_reset.html'
    email_template_name = 'trackingtalibe/password_reset_email.html'
    subject_template_name = 'trackingtalibe/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'trackingtalibe/password_reset_done.html'

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'trackingtalibe/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'trackingtalibe/password_reset_complete.html'



@csrf_exempt
def registrer_appareil(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            esp_id = data.get('esp_id')
            if not esp_id:
                return JsonResponse({'error': 'esp_id requis'}, status=400)

            # Crée ou récupère l’appareil
            device, created = Device.objects.get_or_create(esp_id=esp_id)
    
            # Crée ou récupère le token
            token, _ = DeviceToken.objects.get_or_create(esp=device)
            status_code = 201 if created else 200
            return JsonResponse({'token': token.key}, status=status_code)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)

@login_required
def gestion_associations(request):
    if request.user.role != 'serigne':
        return HttpResponse("Accès interdit")
    enfants = Enfant.objects.filter(responsable=request.user)
    demandes = DemandeAssociation.objects.filter(enfant__in=enfants, statut='en_attente')
    associations = []
    for enfant in enfants:
        for parent in enfant.parents.all():
            associations.append({'enfant': enfant, 'utilisateur': parent})
        for nd in enfant.parrains.all():
            associations.append({'enfant': enfant, 'utilisateur': nd})

    context = {
        'demandes': demandes,
        'associations': associations,
    }
    return render(request, 'trackingtalibe/gestion_associations.html', context)

@login_required
def accepter_demande(request, demande_id):
    demande = get_object_or_404(DemandeAssociation, id=demande_id)

    if demande.enfant.responsable != request.user:
        return HttpResponse("Action non autorisée")
    
    if demande.utilisateur.role == 'parent':
        demande.enfant.parents.add(demande.utilisateur)

    elif demande.utilisateur.role == 'ndeye':
        demande.enfant.parrains.add(demande.utilisateur)

    demande.statut = 'accepte'
    demande.save()
    messages.success(request, "Demande acceptée.")
    return redirect('gestion_associations')


@login_required
def refuser_demande(request, demande_id):
    demande = get_object_or_404(DemandeAssociation, id=demande_id)

    if demande.enfant.responsable != request.user:
        return HttpResponse("Action non autorisée")

    demande.statut = 'refuse'
    demande.save()
    messages.info(request, "Demande refusée.")
    return redirect('gestion_associations')


@require_POST
@login_required
def dissocier_utilisateur(request, enfant_id, utilisateur_id):
    enfant = get_object_or_404(Enfant, id=enfant_id, responsable=request.user)
    utilisateur = get_object_or_404(CustomUser, id=utilisateur_id)

    if utilisateur.role == 'parent':
        enfant.parents.remove(utilisateur)
    elif utilisateur.role == 'ndeye':
        enfant.parrains.remove(utilisateur)

    messages.success(request, "L'utilisateur a été dissocié avec succès.")
    return redirect('gestion_associations')

@login_required
def changer_mot_de_passe(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Garde l'utilisateur connecté
            messages.success(request, "Votre mot de passe a été modifié avec succès.")
            return redirect('redirection_espace')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'trackingtalibe/changer_mot_de_passe.html', {'form': form})


