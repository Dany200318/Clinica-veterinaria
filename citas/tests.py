"""
Pruebas unitarias y de integración del módulo de citas (Tabla 6.2 y 6.3).
Ejecutar con:  python manage.py test
"""
from datetime import time, timedelta

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.mail.backends.base import BaseEmailBackend
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from notificaciones.models import Notificacion
from pacientes.models import Paciente, Propietario

from .models import Cita, Veterinario


class BackendQueFalla(BaseEmailBackend):
    """Simula un servidor SMTP mal configurado (CP-12)."""

    def send_messages(self, email_messages):
        raise ConnectionRefusedError('Servidor SMTP no disponible')


class BaseCitas(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.hoy = timezone.localdate()
        cls.manana = cls.hoy + timedelta(days=1)
        cls.propietario = Propietario.objects.create(
            nombre='Juan Pérez', telefono='5555-1234', email='juan@ejemplo.com')
        cls.paciente = Paciente.objects.create(
            propietario=cls.propietario, nombre='Firulais', especie='Perro', raza='Mestizo', sexo='M')
        cls.paciente2 = Paciente.objects.create(
            propietario=cls.propietario, nombre='Michi', especie='Gato', raza='Siamés', sexo='H')
        cls.vet = Veterinario.objects.create(nombre_completo='Dra. Prueba')
        cls.vet2 = Veterinario.objects.create(nombre_completo='Dr. Segundo')

    def nueva_cita(self, **kwargs):
        datos = {
            'paciente': self.paciente, 'veterinario': self.vet, 'fecha_cita': self.manana,
            'hora_inicio': time(9, 0), 'hora_fin': time(9, 30), 'motivo': 'Consulta',
        }
        datos.update(kwargs)
        return Cita(**datos)


class ValidacionDisponibilidadTests(BaseCitas):
    """Pruebas unitarias de la regla de negocio RF-10."""

    def test_cita_en_horario_libre_es_valida(self):
        cita = self.nueva_cita()
        cita.full_clean()
        cita.save()
        self.assertEqual(cita.estado, Cita.PENDIENTE)  # CP-07

    def test_rechaza_traslape_mismo_veterinario(self):
        self.nueva_cita().save()
        conflicto = self.nueva_cita(paciente=self.paciente2, hora_inicio=time(9, 15), hora_fin=time(9, 45))
        with self.assertRaises(ValidationError) as ctx:
            conflicto.full_clean()  # CP-08
        self.assertIn('ya tiene una cita', str(ctx.exception))

    def test_permite_mismo_horario_con_otro_veterinario(self):
        self.nueva_cita().save()
        otra = self.nueva_cita(paciente=self.paciente2, veterinario=self.vet2)
        otra.full_clean()

    def test_permite_citas_consecutivas(self):
        self.nueva_cita().save()
        siguiente = self.nueva_cita(paciente=self.paciente2, hora_inicio=time(9, 30), hora_fin=time(10, 0))
        siguiente.full_clean()

    def test_cita_cancelada_libera_horario(self):
        cita = self.nueva_cita()
        cita.save()
        cita.estado = Cita.CANCELADA
        cita.save()  # CP-09
        nueva = self.nueva_cita(paciente=self.paciente2)
        nueva.full_clean()

    def test_sin_hora_fin_usa_duracion_por_defecto(self):
        self.nueva_cita(hora_fin=None).save()  # 09:00 a 09:30 asumido
        conflicto = self.nueva_cita(paciente=self.paciente2, hora_inicio=time(9, 20), hora_fin=None)
        with self.assertRaises(ValidationError):
            conflicto.full_clean()

    def test_paciente_no_puede_tener_dos_citas_simultaneas(self):
        self.nueva_cita().save()
        with self.assertRaises(ValidationError):
            self.nueva_cita(veterinario=self.vet2).full_clean()

    def test_hora_fin_debe_ser_mayor(self):
        with self.assertRaises(ValidationError):
            self.nueva_cita(hora_inicio=time(10, 0), hora_fin=time(9, 0)).full_clean()

    def test_no_permite_fechas_pasadas(self):
        with self.assertRaises(ValidationError):
            self.nueva_cita(fecha_cita=self.hoy - timedelta(days=1)).full_clean()

    def test_veterinario_inactivo(self):
        self.vet2.activo = False
        self.vet2.save()
        with self.assertRaises(ValidationError):
            self.nueva_cita(veterinario=self.vet2).full_clean()


class VistasCitasTests(BaseCitas):
    """Pruebas de integración y funcionales desde la interfaz."""

    def setUp(self):
        self.usuario = User.objects.create_user('recep', password='ClaveSegura123')
        self.usuario.groups.add(Group.objects.get_or_create(name='Recepcionista')[0])
        self.client.login(username='recep', password='ClaveSegura123')

    def datos_post(self, **kwargs):
        datos = {
            'paciente': self.paciente.pk, 'veterinario': self.vet.pk,
            'fecha_cita': self.manana.isoformat(), 'hora_inicio': '09:00', 'hora_fin': '09:30',
            'motivo': 'Vacunación anual', 'tipo_cita': 'vacunacion', 'estado': 'pendiente',
            'notas': '', 'notificar': 'on',
        }
        datos.update(kwargs)
        return datos

    def test_crear_cita_envia_correo(self):
        r = self.client.post(reverse('crear_cita'), self.datos_post())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Cita.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)  # CP-11
        self.assertIn('juan@ejemplo.com', mail.outbox[0].to)
        self.assertTrue(Notificacion.objects.filter(estado='enviado', tipo='confirmacion').exists())

    def test_crear_cita_en_horario_ocupado_muestra_error(self):
        self.nueva_cita().save()
        r = self.client.post(reverse('crear_cita'), self.datos_post(paciente=self.paciente2.pk))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'ya tiene una cita')
        self.assertEqual(Cita.objects.count(), 1)

    @override_settings(EMAIL_BACKEND='citas.tests.BackendQueFalla')
    def test_si_el_correo_falla_la_cita_se_guarda_con_advertencia(self):
        r = self.client.post(reverse('crear_cita'), self.datos_post(), follow=True)
        self.assertEqual(Cita.objects.count(), 1)  # CP-12
        self.assertContains(r, 'el correo no pudo enviarse')
        self.assertTrue(Notificacion.objects.filter(estado='error').exists())

    def test_cancelar_cita(self):
        cita = self.nueva_cita()
        cita.save()
        self.client.post(reverse('cambiar_estado_cita', args=[cita.pk]), {'estado': 'cancelada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CANCELADA)

    def test_confirmar_cita(self):
        cita = self.nueva_cita()
        cita.save()
        self.client.post(reverse('cambiar_estado_cita', args=[cita.pk]), {'estado': 'confirmada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.CONFIRMADA)  # CP-10

    def test_dashboard_muestra_totales(self):
        self.nueva_cita(fecha_cita=self.hoy, hora_inicio=time(23, 0), hora_fin=time(23, 30)).save()
        r = self.client.get(reverse('dashboard'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['total_citas_hoy'], 1)  # CP-13
        self.assertEqual(r.context['total_pacientes'], 2)

    def test_disponibilidad_json(self):
        self.nueva_cita().save()
        r = self.client.get(reverse('disponibilidad_citas'),
                            {'veterinario': self.vet.pk, 'fecha': self.manana.isoformat()})
        self.assertEqual(r.json()['ocupados'][0]['inicio'], '09:00')

    def test_recepcionista_no_puede_eliminar_citas(self):
        cita = self.nueva_cita()
        cita.save()
        r = self.client.post(reverse('eliminar_cita', args=[cita.pk]))
        self.assertEqual(r.status_code, 403)
        self.assertTrue(Cita.objects.filter(pk=cita.pk).exists())

    def test_recepcionista_no_ve_reportes(self):
        self.assertEqual(self.client.get(reverse('reportes')).status_code, 403)

    def test_calendario_y_lista_cargan(self):
        self.nueva_cita().save()
        self.assertEqual(self.client.get(reverse('calendario_citas')).status_code, 200)
        self.assertEqual(self.client.get(reverse('lista_citas')).status_code, 200)
        self.assertEqual(self.client.get(reverse('crear_cita')).status_code, 200)
