"""
Módulo de notificaciones por correo electrónico (RF-14 a RF-17).
"""
from django.db import models


class ConfiguracionCorreo(models.Model):
    """
    Configuración del servidor SMTP editable desde el sistema (RF-17, HU-16).
    Existe un único registro (id = 1). Si «usar_esta_configuracion» está
    desactivado, el sistema usa los valores del archivo .env.
    """

    usar_esta_configuracion = models.BooleanField(
        'usar esta configuración', default=False,
        help_text='Si está desactivado se usan los valores del archivo .env.',
    )
    servidor = models.CharField('servidor SMTP', max_length=150, default='smtp.gmail.com')
    puerto = models.PositiveIntegerField('puerto', default=587)
    usar_tls = models.BooleanField('usar TLS', default=True)
    usar_ssl = models.BooleanField('usar SSL', default=False)
    usuario = models.CharField('usuario / correo', max_length=150, blank=True)
    contrasena = models.CharField(
        'contraseña de aplicación', max_length=150, blank=True,
        help_text='Déjela vacía para usar EMAIL_PASSWORD del archivo .env (recomendado).',
    )
    remitente = models.CharField(
        'nombre del remitente', max_length=150, blank=True,
        help_text='Ej.: Clínica Veterinaria <citas@clinica.com>',
    )
    dias_recordatorio_cita = models.PositiveSmallIntegerField(
        'días de anticipación (citas)', default=1,
        help_text='Se envía el recordatorio a las citas que ocurrirán dentro de este número de días.',
    )
    dias_recordatorio_vacuna = models.PositiveSmallIntegerField(
        'días de anticipación (vacunas)', default=7,
    )
    fecha_actualizacion = models.DateTimeField('última modificación', auto_now=True)

    class Meta:
        db_table = 'configuracion_correo'
        verbose_name = 'configuración de correo'
        verbose_name_plural = 'configuración de correo'

    def __str__(self):
        return f'SMTP {self.servidor}:{self.puerto}'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Notificacion(models.Model):
    """Bitácora de correos enviados. Fuente del indicador «notificaciones entregadas» (Tabla 6.4)."""

    TIPO_CHOICES = [
        ('confirmacion', 'Confirmación de cita'),
        ('modificacion', 'Modificación de cita'),
        ('cancelacion', 'Cancelación de cita'),
        ('recordatorio_cita', 'Recordatorio de cita'),
        ('recordatorio_vacuna', 'Recordatorio de vacuna'),
        ('prueba', 'Correo de prueba'),
    ]
    ESTADO_CHOICES = [
        ('enviado', 'Enviado'),
        ('error', 'Error'),
    ]

    id_notificacion = models.AutoField(primary_key=True)
    tipo = models.CharField('tipo', max_length=25, choices=TIPO_CHOICES)
    cita = models.ForeignKey(
        'citas.Cita', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_cita', related_name='notificaciones',
    )
    vacuna = models.ForeignKey(
        'pacientes.Vacuna', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_vacuna', related_name='notificaciones',
    )
    destinatario = models.EmailField('destinatario', max_length=254)
    asunto = models.CharField('asunto', max_length=200)
    estado = models.CharField('estado', max_length=10, choices=ESTADO_CHOICES)
    detalle_error = models.TextField('detalle del error', blank=True)
    fecha_envio = models.DateTimeField('fecha de envío', auto_now_add=True)

    class Meta:
        db_table = 'notificacion'
        ordering = ['-fecha_envio']
        verbose_name = 'notificación'
        verbose_name_plural = 'notificaciones'
        indexes = [
            models.Index(fields=['tipo', 'estado'], name='idx_notif_tipo_estado'),
            models.Index(fields=['fecha_envio'], name='idx_notif_fecha'),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} → {self.destinatario} ({self.estado})'
