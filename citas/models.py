"""
Módulo de citas (RF-09 a RF-13).
Estructura según el diccionario de datos: Tabla 5.4 (VETERINARIO) y Tabla 5.5 (CITA).
"""
from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from pacientes.models import Paciente


class Veterinario(models.Model):
    """Tabla 5.4 — Entidad VETERINARIO."""

    id_veterinario = models.AutoField(primary_key=True)
    nombre_completo = models.CharField('nombre completo', max_length=150)
    activo = models.BooleanField('activo', default=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_usuario', related_name='veterinario',
        verbose_name='usuario del sistema',
        help_text='Opcional. Vincula al veterinario con su usuario para filtrar «mis citas».',
    )

    class Meta:
        db_table = 'veterinario'
        ordering = ['nombre_completo']
        verbose_name = 'veterinario'
        verbose_name_plural = 'veterinarios'

    def __str__(self):
        return self.nombre_completo


def sumar_minutos(hora, minutos):
    return (datetime.combine(date(2000, 1, 1), hora) + timedelta(minutes=minutos)).time()


class Cita(models.Model):
    """Tabla 5.5 — Entidad CITA."""

    PENDIENTE = 'pendiente'
    CONFIRMADA = 'confirmada'
    COMPLETADA = 'completada'
    CANCELADA = 'cancelada'
    ESTADO_CHOICES = [
        (PENDIENTE, 'Pendiente'),
        (CONFIRMADA, 'Confirmada'),
        (COMPLETADA, 'Completada'),
        (CANCELADA, 'Cancelada'),
    ]
    TIPO_CHOICES = [
        ('consulta', 'Consulta general'),
        ('vacunacion', 'Vacunación'),
        ('desparasitacion', 'Desparasitación'),
        ('cirugia', 'Cirugía menor'),
        ('control', 'Control / seguimiento'),
        ('emergencia', 'Emergencia'),
    ]

    id_cita = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.PROTECT, db_column='id_paciente',
        related_name='citas', verbose_name='paciente',
    )
    veterinario = models.ForeignKey(
        Veterinario, on_delete=models.PROTECT, db_column='id_veterinario',
        related_name='citas', verbose_name='veterinario',
    )
    fecha_cita = models.DateField('fecha de la cita')
    hora_inicio = models.TimeField('hora de inicio')
    hora_fin = models.TimeField('hora fin', null=True, blank=True)
    motivo = models.TextField('motivo de la consulta')
    tipo_cita = models.CharField('tipo de cita', max_length=20, choices=TIPO_CHOICES, blank=True)
    estado = models.CharField('estado', max_length=15, choices=ESTADO_CHOICES, default=PENDIENTE)
    notas = models.TextField('notas adicionales', blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_usuario_registro', related_name='citas_registradas',
        verbose_name='registrada por',
    )
    fecha_creacion = models.DateTimeField('fecha de registro', auto_now_add=True)
    fecha_actualizacion = models.DateTimeField('última modificación', auto_now=True)

    class Meta:
        db_table = 'cita'
        ordering = ['fecha_cita', 'hora_inicio']
        verbose_name = 'cita'
        verbose_name_plural = 'citas'
        indexes = [
            models.Index(fields=['veterinario', 'fecha_cita'], name='idx_cita_vet_fecha'),
            models.Index(fields=['fecha_cita', 'estado'], name='idx_cita_fecha_estado'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(hora_fin__isnull=True) | Q(hora_fin__gt=models.F('hora_inicio')),
                name='chk_cita_hora_fin_mayor',
            ),
        ]

    def __str__(self):
        return f'{self.paciente.nombre} — {self.fecha_cita:%d/%m/%Y} {self.hora_inicio:%H:%M}'

    def get_absolute_url(self):
        return reverse('detalle_cita', args=[self.pk])

    # ------------------------------------------------------------------ utilidades
    @property
    def hora_fin_efectiva(self):
        """Si la cita no tiene hora fin, se asume la duración configurada (30 min por defecto)."""
        if self.hora_fin:
            return self.hora_fin
        if self.hora_inicio:
            return sumar_minutos(self.hora_inicio, settings.CITA_DURACION_MINUTOS)
        return None

    @property
    def propietario(self):
        return self.paciente.propietario

    @property
    def es_editable(self):
        return self.estado not in (self.COMPLETADA, self.CANCELADA)

    @property
    def color_estado(self):
        return {
            self.PENDIENTE: 'warning',
            self.CONFIRMADA: 'primary',
            self.COMPLETADA: 'success',
            self.CANCELADA: 'secondary',
        }.get(self.estado, 'light')

    # ------------------------------------------------------------------ validaciones
    def clean(self):
        errores = {}
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            errores['hora_fin'] = 'La hora de fin debe ser posterior a la hora de inicio.'
        if self.hora_inicio and not self.hora_fin and \
                sumar_minutos(self.hora_inicio, settings.CITA_DURACION_MINUTOS) <= self.hora_inicio:
            errores['hora_inicio'] = 'La cita debe terminar el mismo día.'

        es_nueva = self._state.adding
        if es_nueva and self.fecha_cita and self.fecha_cita < timezone.localdate():
            errores['fecha_cita'] = 'No se pueden agendar citas en fechas pasadas.'

        if self.veterinario_id and not self.veterinario.activo and self.estado != self.CANCELADA:
            original = None if es_nueva else Cita.objects.filter(pk=self.pk).values_list(
                'veterinario_id', flat=True).first()
            if original != self.veterinario_id:
                errores['veterinario'] = 'El veterinario seleccionado no está activo.'

        if errores:
            raise ValidationError(errores)
        self.validar_disponibilidad()

    def citas_en_conflicto(self):
        """Citas activas que se traslapan con el horario de esta cita."""
        if not (self.fecha_cita and self.hora_inicio):
            return []
        if self.estado == self.CANCELADA:
            return []
        inicio, fin = self.hora_inicio, self.hora_fin_efectiva
        candidatas = (
            Cita.objects
            .filter(fecha_cita=self.fecha_cita)
            .filter(Q(veterinario_id=self.veterinario_id) | Q(paciente_id=self.paciente_id))
            .exclude(estado=self.CANCELADA)
            .select_related('paciente', 'veterinario')
        )
        if self.pk:
            candidatas = candidatas.exclude(pk=self.pk)
        return [c for c in candidatas if inicio < c.hora_fin_efectiva and c.hora_inicio < fin]

    def validar_disponibilidad(self):
        """
        Regla de negocio principal (RF-10, CU-05 flujo 3a): un veterinario no puede
        tener dos citas en el mismo horario. Tampoco se permite que un paciente
        tenga dos citas simultáneas. Las citas canceladas liberan el horario.
        """
        if not (self.veterinario_id and self.paciente_id):
            return
        mensajes = []
        for c in self.citas_en_conflicto():
            rango = f'{c.hora_inicio:%H:%M} a {c.hora_fin_efectiva:%H:%M}'
            if c.veterinario_id == self.veterinario_id:
                mensajes.append(
                    f'No se puede agendar porque {c.veterinario} ya tiene una cita el '
                    f'{c.fecha_cita:%d/%m/%Y} de {rango} (paciente: {c.paciente.nombre}).'
                )
            else:
                mensajes.append(
                    f'El paciente {c.paciente.nombre} ya tiene otra cita el '
                    f'{c.fecha_cita:%d/%m/%Y} de {rango} con {c.veterinario}.'
                )
        if mensajes:
            raise ValidationError(mensajes)

    # ------------------------------------------------------------------ notificaciones
    def enviar_notificacion_email(self, tipo='confirmacion'):
        """
        Envía el correo al propietario (RF-14). Devuelve True si se envió y
        False si falló; la cita queda guardada en ambos casos (RF-15, sección 5.2.3).
        """
        from notificaciones.servicios import enviar_correo_cita
        return enviar_correo_cita(self, tipo)

