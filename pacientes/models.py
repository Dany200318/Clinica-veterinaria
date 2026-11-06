"""
Módulo de propietarios y pacientes (RF-05 a RF-08).
Estructura según el diccionario de datos: Tabla 5.2 (PROPIETARIO) y Tabla 5.3 (PACIENTE).
"""
from datetime import timedelta

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

validador_telefono = RegexValidator(
    r'^\+?[0-9\s\-]{8,20}$',
    'Ingrese un teléfono válido (solo números, espacios o guiones; mínimo 8 dígitos).',
)
validador_dpi = RegexValidator(r'^\d{13}$', 'El DPI debe tener exactamente 13 dígitos.')


class Propietario(models.Model):
    """Tabla 5.2 — Entidad PROPIETARIO."""

    id_propietario = models.AutoField(primary_key=True)
    nombre = models.CharField('nombre completo', max_length=150)
    telefono = models.CharField('teléfono', max_length=20, validators=[validador_telefono])
    email = models.EmailField('correo electrónico', max_length=254,
                              help_text='Se usa para enviar confirmaciones y recordatorios.')
    direccion = models.CharField('dirección', max_length=255, blank=True)
    dpi = models.CharField('DPI', max_length=13, unique=True, null=True, blank=True,
                           validators=[validador_dpi])
    zona = models.CharField('zona', max_length=50, blank=True)

    class Meta:
        db_table = 'propietario'
        ordering = ['nombre']
        verbose_name = 'propietario'
        verbose_name_plural = 'propietarios'

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse('detalle_propietario', args=[self.pk])


class Paciente(models.Model):
    """Tabla 5.3 — Entidad PACIENTE (la mascota)."""

    ESPECIE_CHOICES = [
        ('Perro', 'Perro'),
        ('Gato', 'Gato'),
        ('Otro', 'Otro'),
    ]
    SEXO_CHOICES = [
        ('M', 'Macho'),
        ('H', 'Hembra'),
    ]

    id_paciente = models.AutoField(primary_key=True)
    propietario = models.ForeignKey(
        Propietario, on_delete=models.PROTECT, db_column='id_propietario',
        related_name='pacientes', verbose_name='propietario',
    )
    nombre = models.CharField('nombre', max_length=100)
    especie = models.CharField('especie', max_length=20, choices=ESPECIE_CHOICES)
    raza = models.CharField('raza', max_length=100)
    sexo = models.CharField('sexo', max_length=1, choices=SEXO_CHOICES)
    color = models.CharField('color', max_length=50, blank=True)
    fecha_nacimiento = models.DateField('fecha de nacimiento', null=True, blank=True)
    peso = models.DecimalField('peso (lb)', max_digits=6, decimal_places=2, null=True, blank=True,
                               validators=[MinValueValidator(0)])
    microchip = models.CharField('microchip', max_length=30, blank=True)
    esterilizado = models.BooleanField('esterilizado', default=False)
    alergias = models.TextField('alergias conocidas', blank=True,
                                help_text='Se mostrarán en el carnet del paciente.')
    observaciones = models.TextField('observaciones', blank=True)
    fecha_registro = models.DateField('fecha de registro', auto_now_add=True)

    class Meta:
        db_table = 'paciente'
        ordering = ['nombre']
        verbose_name = 'paciente'
        verbose_name_plural = 'pacientes'
        indexes = [
            models.Index(fields=['nombre'], name='idx_paciente_nombre'),
        ]

    def __str__(self):
        return f'{self.nombre} ({self.especie}) — {self.propietario.nombre}'

    def get_absolute_url(self):
        return reverse('ficha_paciente', args=[self.pk])

    @property
    def edad(self):
        """Edad en texto (años y meses) calculada desde la fecha de nacimiento."""
        if not self.fecha_nacimiento:
            return None
        hoy = timezone.localdate()
        meses = (hoy.year - self.fecha_nacimiento.year) * 12 + hoy.month - self.fecha_nacimiento.month
        if hoy.day < self.fecha_nacimiento.day:
            meses -= 1
        meses = max(meses, 0)
        anios, meses = divmod(meses, 12)
        partes = []
        if anios:
            partes.append(f'{anios} año{"s" if anios != 1 else ""}')
        if meses or not anios:
            partes.append(f'{meses} mes{"es" if meses != 1 else ""}')
        return ' y '.join(partes)

    @property
    def tiene_alergias(self):
        return bool(self.alergias and self.alergias.strip())


class Vacuna(models.Model):
    """
    Registro de vacunas aplicadas y próximas dosis (objetivo específico 4 y
    proceso «Control de vacunas» de la Tabla 6.5). Permite enviar recordatorios
    de vacunas próximas a vencer.
    """

    id_vacuna = models.AutoField(primary_key=True)
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE, db_column='id_paciente',
        related_name='vacunas', verbose_name='paciente',
    )
    nombre = models.CharField('vacuna', max_length=100,
                              help_text='Ej.: Rabia, Parvovirus, Triple felina, Desparasitación.')
    fecha_aplicacion = models.DateField('fecha de aplicación')
    fecha_proxima = models.DateField('próxima dosis', null=True, blank=True)
    lote = models.CharField('lote', max_length=50, blank=True)
    observaciones = models.TextField('observaciones', blank=True)

    class Meta:
        db_table = 'vacuna'
        ordering = ['-fecha_aplicacion']
        verbose_name = 'vacuna'
        verbose_name_plural = 'vacunas'
        indexes = [
            models.Index(fields=['fecha_proxima'], name='idx_vacuna_fecha_proxima'),
        ]

    def __str__(self):
        return f'{self.nombre} — {self.paciente.nombre} ({self.fecha_aplicacion:%d/%m/%Y})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.fecha_proxima and self.fecha_aplicacion and self.fecha_proxima <= self.fecha_aplicacion:
            raise ValidationError({'fecha_proxima': 'La próxima dosis debe ser posterior a la fecha de aplicación.'})

    @property
    def estado(self):
        """'vencida', 'proxima' (en 30 días o menos) o 'al_dia'."""
        if not self.fecha_proxima:
            return 'al_dia'
        hoy = timezone.localdate()
        if self.fecha_proxima < hoy:
            return 'vencida'
        if self.fecha_proxima <= hoy + timedelta(days=30):
            return 'proxima'
        return 'al_dia'
