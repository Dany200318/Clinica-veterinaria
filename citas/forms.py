from django import forms
from django.contrib.auth.models import User

from pacientes.models import Paciente

from .models import Cita, Veterinario


class PacienteChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f'{obj.nombre} ({obj.especie}) — {obj.propietario.nombre}'


class CitaForm(forms.ModelForm):
    """Formulario de cita (RF-09): paciente, veterinario, fecha, horas, motivo, tipo, estado y notas."""

    paciente = PacienteChoiceField(
        queryset=Paciente.objects.select_related('propietario').order_by('nombre'),
        empty_label='— Seleccione el paciente —',
        label='Paciente',
    )
    notificar = forms.BooleanField(
        required=False, initial=True,
        label='Enviar correo de confirmación al propietario',
    )

    class Meta:
        model = Cita
        fields = ['paciente', 'veterinario', 'fecha_cita', 'hora_inicio', 'hora_fin',
                  'motivo', 'tipo_cita', 'estado', 'notas']
        widgets = {
            'fecha_cita': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'step': 300}, format='%H:%M'),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'step': 300}, format='%H:%M'),
            'motivo': forms.Textarea(attrs={'rows': 3}),
            'notas': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vets = Veterinario.objects.filter(activo=True)
        if self.instance.pk and self.instance.veterinario_id:
            vets = Veterinario.objects.filter(pk=self.instance.veterinario_id) | vets
        self.fields['veterinario'].queryset = vets.distinct().order_by('nombre_completo')
        self.fields['veterinario'].empty_label = '— Seleccione el veterinario —'
        self.fields['tipo_cita'].choices = [('', '— Seleccione el tipo —')] + list(Cita.TIPO_CHOICES)
        if self.instance.pk:
            self.fields['notificar'].label = 'Enviar correo al propietario informando el cambio'


class VeterinarioForm(forms.ModelForm):
    class Meta:
        model = Veterinario
        fields = ['nombre_completo', 'activo', 'usuario']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        libres = User.objects.filter(veterinario__isnull=True, is_active=True)
        if self.instance.pk and self.instance.usuario_id:
            libres = libres | User.objects.filter(pk=self.instance.usuario_id)
        self.fields['usuario'].queryset = libres.distinct().order_by('username')
        self.fields['usuario'].required = False
