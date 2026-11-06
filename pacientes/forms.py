from django import forms

from .models import Paciente, Propietario, Vacuna


class PropietarioForm(forms.ModelForm):
    """Formulario de propietario (RF-05): nombre, teléfono, correo, dirección, DPI y zona."""

    class Meta:
        model = Propietario
        fields = ['nombre', 'telefono', 'email', 'direccion', 'dpi', 'zona']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombres y apellidos'}),
            'telefono': forms.TextInput(attrs={'placeholder': '5555-5555'}),
            'email': forms.EmailInput(attrs={'placeholder': 'correo@ejemplo.com'}),
            'dpi': forms.TextInput(attrs={'placeholder': '13 dígitos', 'inputmode': 'numeric'}),
            'zona': forms.TextInput(attrs={'placeholder': 'Ej.: Zona 1, Amatitlán'}),
        }

    def clean_nombre(self):
        return ' '.join(self.cleaned_data['nombre'].split()).title()

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()


class PacienteForm(forms.ModelForm):
    """Formulario de paciente (RF-06), siempre asociado a un propietario."""

    class Meta:
        model = Paciente
        fields = [
            'propietario', 'nombre', 'especie', 'raza', 'sexo', 'color',
            'fecha_nacimiento', 'peso', 'microchip', 'esterilizado',
            'alergias', 'observaciones',
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'alergias': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej.: Penicilina, pollo...'}),
            'observaciones': forms.Textarea(attrs={'rows': 3}),
            'peso': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['propietario'].queryset = Propietario.objects.order_by('nombre')
        self.fields['propietario'].empty_label = '— Seleccione el propietario —'

    def clean_fecha_nacimiento(self):
        from django.utils import timezone
        fecha = self.cleaned_data.get('fecha_nacimiento')
        if fecha and fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de nacimiento no puede ser futura.')
        return fecha


class VacunaForm(forms.ModelForm):
    class Meta:
        model = Vacuna
        fields = ['nombre', 'fecha_aplicacion', 'fecha_proxima', 'lote', 'observaciones']
        widgets = {
            'fecha_aplicacion': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha_proxima': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'observaciones': forms.Textarea(attrs={'rows': 2}),
        }
