from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group, User

from .roles import ROLES_CHOICES, VETERINARIO, obtener_rol


class LoginForm(AuthenticationForm):
    """Formulario de inicio de sesión (RF-01)."""

    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Nombre de usuario',
            'autofocus': True,
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
        }),
    )
    error_messages = {
        'invalid_login': 'Usuario o contraseña incorrectos.',
        'inactive': 'Esta cuenta está desactivada. Consulte con el administrador.',
    }


def _asignar_rol(usuario, rol):
    """Deja al usuario en un único grupo/rol."""
    usuario.groups.clear()
    grupo, _ = Group.objects.get_or_create(name=rol)
    usuario.groups.add(grupo)


class UsuarioCrearForm(UserCreationForm):
    """Alta de usuarios con rol (RF-02)."""

    rol = forms.ChoiceField(choices=ROLES_CHOICES, label='Rol')
    crear_veterinario = forms.BooleanField(
        required=False,
        initial=True,
        label='Registrar también como veterinario (aparecerá en la agenda de citas)',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
            'is_active': 'Activo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.is_staff = self.cleaned_data['rol'] == 'Administrador'
        if commit:
            usuario.save()
            _asignar_rol(usuario, self.cleaned_data['rol'])
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    """Edición y desactivación de usuarios (RF-02)."""

    rol = forms.ChoiceField(choices=ROLES_CHOICES, label='Rol')

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
            'is_active': 'Activo (puede iniciar sesión)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        if self.instance.pk:
            self.fields['rol'].initial = obtener_rol(self.instance)

    def save(self, commit=True):
        usuario = super().save(commit=False)
        if not usuario.is_superuser:
            usuario.is_staff = self.cleaned_data['rol'] == 'Administrador'
        if commit:
            usuario.save()
            _asignar_rol(usuario, self.cleaned_data['rol'])
        return usuario


def es_veterinario(cleaned_data):
    return cleaned_data.get('rol') == VETERINARIO
