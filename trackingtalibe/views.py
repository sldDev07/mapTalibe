from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from .forms import EnfantForm,InscriptionForm, AssocierEnfantViaESP32Form
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Enfant, Device, DeviceToken, DemandeAssociation, CustomUser
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json, os



def accueil(request):
    return render(request, 'trackingtalibe/accueil.html')
def a_propos(request):
    return render(request, 'trackingtalibe/a_propos.html')

def register(request):
    role_selected = request.POST.get('role_selection', None)

    if request.method == 'POST':
        form = InscriptionForm(request.POST, role_selected=role_selected)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = role_selected
            user.save()
            login(request, user)
            return redirect('redirection_espace')
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
        return redirect('accueil')
@login_required
def espace_serigne(request):
    if request.user.role != 'serigne':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    enfants = Enfant.objects.filter(responsable=request.user)
    return render(request, 'trackingtalibe/espace_serigne.html', {'enfants': enfants})

@login_required
def espace_ndeye(request):
    if request.user.role != 'ndeye':
        return HttpResponse("<h3>Accès non autorisé </h3>")
    
    enfants = request.user.enfants_parrains.all()
    demandes_en_attente = DemandeAssociation.objects.filter(utilisateur=request.user)
    
    return render(request, 'trackingtalibe/espace_ndeye.html', {'enfants': enfants})

@login_required
def espace_parent(request):
    if request.user.role != 'parent':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    enfants = request.user.enfants_parents.all()
    demandes_en_attente = DemandeAssociation.objects.filter(utilisateur=request.user)
    
    return render(request, 'trackingtalibe/espace_parent.html', {'enfants': enfants})
@login_required
def ajouter_enfant(request):
    if request.user.role != 'serigne':
        return HttpResponse("<h3>Accès non autorisé </h3>")

    if request.method == 'POST':
        form = EnfantForm(request.POST)
        if form.is_valid():
            enfant = form.save(commit=False)
            enfant.responsable = request.user
            enfant.save()
            return redirect('espace_serigne')
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
                return redirect('redirection_espace')
            except Enfant.DoesNotExist:
                messages.error(request, "Aucun enfant avec cet ID ESP32 n’a été trouvé.")
    else:
        form = AssocierEnfantViaESP32Form()

    demandes_existantes = DemandeAssociation.objects.filter(utilisateur=request.user, statut='en_attente').select_related('enfant').order_by('date')
    return render(request, 'trackingtalibe/associer_par_code.html', {
    'form': form,
    'demandes_existantes': demandes_existantes,
})



@csrf_exempt
def enregistrer_position(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            esp_id = data.get('esp_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if not esp_id or latitude is None or longitude is None:
                return JsonResponse({'error': 'esp_id, latitude et longitude requis'}, status=400)

            # Vérifier que l'ESP32 est enregistré (optionnel)
            if not Device.objects.filter(esp_id=esp_id).exists():
                Device.objects.create(esp_id=esp_id)

            # Chemin vers le fichier positions.json
            json_path = os.path.join(settings.MEDIA_ROOT, 'positions.json')

            # Lire le fichier existant ou créer un nouveau dictionnaire
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    positions = json.load(f)
            else:
                positions = {}

            # Mettre à jour ou ajouter la position de l'appareil
            positions[esp_id] = {
                'latitude': latitude,
                'longitude': longitude
            }

            # Écrire dans le fichier
            with open(json_path, 'w') as f:
                json.dump(positions, f, indent=4)

            return JsonResponse({'message': 'Coordonnées enregistrées avec succès'})
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Données JSON invalides'}, status=400)

    return JsonResponse({'error': 'Méthode non autorisée'}, status=405)


@login_required
def suivre_enfant(request, enfant_id):
    enfant = get_object_or_404(Enfant, id=enfant_id)

    if (
        enfant.responsable == request.user
        or request.user in enfant.parents.all()
        or request.user in enfant.parrains.all()
    ):
        # La carte s'affichera quoi qu’il arrive, les coordonnées seront mises à jour via JS
        return render(request, 'trackingtalibe/suivre_enfant.html', {
            'enfant': enfant,
        })
    else:
        return render(request, 'trackingtalibe/erreur.html', {
            'message': "Vous n’êtes pas autorisé à suivre cet enfant."
        })

@login_required
def get_position_enfant(request, enfant_id):
    enfant = get_object_or_404(Enfant, id=enfant_id)

    # Vérification de l’autorisation
    if request.user != enfant.responsable and \
       request.user not in enfant.parents.all() and \
       request.user not in enfant.parrains.all():
        return JsonResponse({'error': 'Accès refusé'}, status=403)

    # Fichier JSON avec les positions GPS
    json_path = os.path.join(settings.MEDIA_ROOT, 'positions.json')

    try:
        with open(json_path, 'r') as f:
            positions = json.load(f)

        esp_id = enfant.id_esp32  # Clé utilisée dans le JSON

        if esp_id not in positions:
            return JsonResponse({'error': 'Pas de position trouvée'}, status=404)

        pos = positions[esp_id]
        return JsonResponse({
            'latitude': pos['latitude'],
            'longitude': pos['longitude'],
        })

    except FileNotFoundError:
        return JsonResponse({'error': 'Fichier de positions introuvable'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Fichier JSON mal formé'}, status=500)

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


def recevoir_contacts(request, esp_id):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Token '):
        return JsonResponse({'error': 'Token manquant ou invalide'}, status=401)

    token_key = auth_header.split(' ')[1]
    try:
        token = DeviceToken.objects.get(key=token_key, esp__esp_id=esp_id)
    except DeviceToken.DoesNotExist:
        return JsonResponse({'error': 'Token invalide ou non associé à cet ESP32'}, status=403)

    try:
        enfant = Enfant.objects.get(id_esp32=esp_id)
    except Enfant.DoesNotExist:
        return JsonResponse({'error': 'Aucun enfant associé à cet ESP32'}, status=404)

    contacts = {
        'serigne': enfant.responsable.téléphone,
        'parents': list(enfant.parents.values_list('téléphone', flat=True)),
        'parrains': list(enfant.parrains.values_list('téléphone', flat=True)),
    }
    return JsonResponse(contacts)


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

