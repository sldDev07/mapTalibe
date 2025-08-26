from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser
from .models import Enfant

class InscriptionForm(UserCreationForm):
    # Ajoute le champ role pour le POST
    role = forms.ChoiceField(
        choices=CustomUser.ROLE_CHOICES,
        required=True,
        widget=forms.HiddenInput()
    )
    nom_daara = forms.CharField(
        label="Nom du Daara",
        max_length=100,
        required=False
    )

    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'nom_daara', 'email', 'telephone', 'role', 'password1', 'password2']
        widgets = {
            'password1': forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
            'password2': forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        }
        help_texts = {
            'username': None,
            'password1': None,
            'password2': None,
        }

    def __init__(self, *args, **kwargs):
        role_selected = kwargs.pop('role_selected', None)
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''
        # Préremplit le champ role avec la sélection
        if role_selected:
            self.fields['role'].initial = role_selected
        if role_selected != 'serigne':
            self.fields.pop('nom_daara')

class EnfantForm(forms.ModelForm):
    class Meta:
        model = Enfant
        fields = ['id_esp32', 'nom', 'prenom', 'date_naissance', 'provenance']
        # Retire 'daara' des champs



class AssocierEnfantViaESP32Form(forms.Form):
    id_esp32 = forms.CharField(label="ID de l'enfant", max_length=100)
