from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView
from .views import (
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
)

urlpatterns = [
    path('accueil/', views.accueil, name='accueil'),
    path('a_propos/', views.a_propos, name='a_propos'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('redirection_espace/', views.redirection_espace, name='redirection_espace'),
    path('espace_serigne/', views.espace_serigne, name='espace_serigne'),
    path('espace_ndeye/', views.espace_ndeye, name='espace_ndeye'),
    path('espace_parent/', views.espace_parent, name='espace_parent'),
    path('logout/', LogoutView.as_view(next_page='accueil'), name='logout'),
    path('enfants/ajouter/', views.ajouter_enfant, name='ajouter_enfant'),
    path('associer_par_code/', views.associer_par_code, name='associer_par_code'),
    path('api/enregistrer_position/', views.enregistrer_position, name='enregistrer_position'),
    path('enfant/<int:enfant_id>/suivre/', views.suivre_enfant, name='suivre_enfant'),
    path('enfant/<int:enfant_id>/position/', views.get_position_enfant, name='get_position_enfant'),
    path('logout/', views.deconnexion_view, name='deconnexion'),
    path('enfants/<int:pk>/modifier/', views.modifier_enfant, name='modifier_enfant'),
    path('enfants/<int:pk>/supprimer/', views.supprimer_enfant, name='supprimer_enfant'),
    path('mot-de-passe/reinitialiser/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('mot-de-passe/reinitialiser/envoye/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('mot-de-passe/reinitialiser/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('mot-de-passe/reinitialiser/complet/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('api/coordonnees/', views.recevoir_contacts, name='recevoir_coordonnees'),
    path('register_device/', views.registrer_appareil, name='register_device'),
    path('gestion-associations/', views.gestion_associations, name='gestion_associations'),
    path('demande/<int:demande_id>/accepter/', views.accepter_demande, name='accepter_demande'),
    path('demande/<int:demande_id>/refuser/', views.refuser_demande, name='refuser_demande'),
    path('dissocier/<int:enfant_id>/<int:utilisateur_id>/', views.dissocier_utilisateur, name='dissocier_utilisateur'),

]
