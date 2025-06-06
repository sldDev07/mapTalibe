from .models import DemandeAssociation

def demandes_non_lues(request):
    if request.user.is_authenticated and request.user.role == 'serigne':
        nb = DemandeAssociation.objects.filter(enfant__responsable=request.user).count()
        return {'nb_demandes': nb}
    return {}