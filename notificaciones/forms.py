from django import forms

from .models import ConfiguracionCorreo


class ConfiguracionCorreoForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionCorreo
        fields = [
            'usar_esta_configuracion', 'servidor', 'puerto', 'usar_tls', 'usar_ssl',
            'usuario', 'contrasena', 'remitente',
            'dias_recordatorio_cita', 'dias_recordatorio_vacuna',
        ]
        widgets = {
            'contrasena': forms.PasswordInput(render_value=True),
            'usuario': forms.EmailInput(attrs={'placeholder': 'clinica.veterinaria@gmail.com'}),
        }
        help_texts = {
            'usar_esta_configuracion': 'Márquelo para enviar los correos con los datos de esta pantalla.',
            'usuario': 'Cuenta de Gmail desde la que saldrán los correos.',
            'contrasena': 'Las 16 letras que genera Google en «Contraseñas de aplicaciones» (los espacios se quitan solos).',
            'remitente': 'Opcional. Ej.: Clínica Veterinaria <clinica.veterinaria@gmail.com>',
        }

    def clean(self):
        datos = super().clean()
        if datos.get('usar_tls') and datos.get('usar_ssl'):
            raise forms.ValidationError('Seleccione TLS o SSL, no ambos (Gmail usa TLS en el puerto 587).')
        if datos.get('usar_esta_configuracion'):
            from django.conf import settings
            if not (datos.get('usuario') or settings.EMAIL_HOST_USER):
                self.add_error('usuario', 'Escriba el correo de Gmail desde el que se enviarán los mensajes.')
            if not (datos.get('contrasena') or (self.instance and self.instance.contrasena)
                    or settings.EMAIL_HOST_PASSWORD):
                self.add_error('contrasena', 'Escriba la contraseña de aplicación de 16 letras de Gmail.')
        clave = (datos.get('contrasena') or '').replace(' ', '')
        datos['contrasena'] = clave  # Gmail la muestra con espacios: se quitan
        return datos


class CorreoPruebaForm(forms.Form):
    destinatario = forms.EmailField(label='Enviar correo de prueba a')
