import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Propietario',
            fields=[
                ('id_propietario', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=150, verbose_name='nombre completo')),
                ('telefono', models.CharField(max_length=20, validators=[django.core.validators.RegexValidator('^\\+?[0-9\\s\\-]{8,20}$', 'Ingrese un teléfono válido (solo números, espacios o guiones; mínimo 8 dígitos).')], verbose_name='teléfono')),
                ('email', models.EmailField(help_text='Se usa para enviar confirmaciones y recordatorios.', max_length=254, verbose_name='correo electrónico')),
                ('direccion', models.CharField(blank=True, max_length=255, verbose_name='dirección')),
                ('dpi', models.CharField(blank=True, max_length=13, null=True, unique=True, validators=[django.core.validators.RegexValidator('^\\d{13}$', 'El DPI debe tener exactamente 13 dígitos.')], verbose_name='DPI')),
                ('zona', models.CharField(blank=True, max_length=50, verbose_name='zona')),
            ],
            options={
                'verbose_name': 'propietario',
                'verbose_name_plural': 'propietarios',
                'db_table': 'propietario',
                'ordering': ['nombre'],
            },
        ),
        migrations.CreateModel(
            name='Paciente',
            fields=[
                ('id_paciente', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(max_length=100, verbose_name='nombre')),
                ('especie', models.CharField(choices=[('Perro', 'Perro'), ('Gato', 'Gato'), ('Otro', 'Otro')], max_length=20, verbose_name='especie')),
                ('raza', models.CharField(max_length=100, verbose_name='raza')),
                ('sexo', models.CharField(choices=[('M', 'Macho'), ('H', 'Hembra')], max_length=1, verbose_name='sexo')),
                ('color', models.CharField(blank=True, max_length=50, verbose_name='color')),
                ('fecha_nacimiento', models.DateField(blank=True, null=True, verbose_name='fecha de nacimiento')),
                ('peso', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='peso (lb)')),
                ('microchip', models.CharField(blank=True, max_length=30, verbose_name='microchip')),
                ('esterilizado', models.BooleanField(default=False, verbose_name='esterilizado')),
                ('alergias', models.TextField(blank=True, help_text='Se mostrarán en el carnet del paciente.', verbose_name='alergias conocidas')),
                ('observaciones', models.TextField(blank=True, verbose_name='observaciones')),
                ('fecha_registro', models.DateField(auto_now_add=True, verbose_name='fecha de registro')),
                ('propietario', models.ForeignKey(db_column='id_propietario', on_delete=django.db.models.deletion.PROTECT, related_name='pacientes', to='pacientes.propietario', verbose_name='propietario')),
            ],
            options={
                'verbose_name': 'paciente',
                'verbose_name_plural': 'pacientes',
                'db_table': 'paciente',
                'ordering': ['nombre'],
                'indexes': [models.Index(fields=['nombre'], name='idx_paciente_nombre')],
            },
        ),
        migrations.CreateModel(
            name='Vacuna',
            fields=[
                ('id_vacuna', models.AutoField(primary_key=True, serialize=False)),
                ('nombre', models.CharField(help_text='Ej.: Rabia, Parvovirus, Triple felina, Desparasitación.', max_length=100, verbose_name='vacuna')),
                ('fecha_aplicacion', models.DateField(verbose_name='fecha de aplicación')),
                ('fecha_proxima', models.DateField(blank=True, null=True, verbose_name='próxima dosis')),
                ('lote', models.CharField(blank=True, max_length=50, verbose_name='lote')),
                ('observaciones', models.TextField(blank=True, verbose_name='observaciones')),
                ('paciente', models.ForeignKey(db_column='id_paciente', on_delete=django.db.models.deletion.CASCADE, related_name='vacunas', to='pacientes.paciente', verbose_name='paciente')),
            ],
            options={
                'verbose_name': 'vacuna',
                'verbose_name_plural': 'vacunas',
                'db_table': 'vacuna',
                'ordering': ['-fecha_aplicacion'],
                'indexes': [models.Index(fields=['fecha_proxima'], name='idx_vacuna_fecha_proxima')],
            },
        ),
    ]
