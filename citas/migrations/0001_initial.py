import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('pacientes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Veterinario',
            fields=[
                ('id_veterinario', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_completo', models.CharField(max_length=150, verbose_name='nombre completo')),
                ('activo', models.BooleanField(default=True, verbose_name='activo')),
                ('usuario', models.OneToOneField(blank=True, db_column='id_usuario', help_text='Opcional. Vincula al veterinario con su usuario para filtrar «mis citas».', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='veterinario', to=settings.AUTH_USER_MODEL, verbose_name='usuario del sistema')),
            ],
            options={
                'verbose_name': 'veterinario',
                'verbose_name_plural': 'veterinarios',
                'db_table': 'veterinario',
                'ordering': ['nombre_completo'],
            },
        ),
        migrations.CreateModel(
            name='Cita',
            fields=[
                ('id_cita', models.AutoField(primary_key=True, serialize=False)),
                ('fecha_cita', models.DateField(verbose_name='fecha de la cita')),
                ('hora_inicio', models.TimeField(verbose_name='hora de inicio')),
                ('hora_fin', models.TimeField(blank=True, null=True, verbose_name='hora fin')),
                ('motivo', models.TextField(verbose_name='motivo de la consulta')),
                ('tipo_cita', models.CharField(blank=True, choices=[('consulta', 'Consulta general'), ('vacunacion', 'Vacunación'), ('desparasitacion', 'Desparasitación'), ('cirugia', 'Cirugía menor'), ('control', 'Control / seguimiento'), ('emergencia', 'Emergencia')], max_length=20, verbose_name='tipo de cita')),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('confirmada', 'Confirmada'), ('completada', 'Completada'), ('cancelada', 'Cancelada')], default='pendiente', max_length=15, verbose_name='estado')),
                ('notas', models.TextField(blank=True, verbose_name='notas adicionales')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True, verbose_name='fecha de registro')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='última modificación')),
                ('creado_por', models.ForeignKey(blank=True, db_column='id_usuario_registro', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='citas_registradas', to=settings.AUTH_USER_MODEL, verbose_name='registrada por')),
                ('paciente', models.ForeignKey(db_column='id_paciente', on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='pacientes.paciente', verbose_name='paciente')),
                ('veterinario', models.ForeignKey(db_column='id_veterinario', on_delete=django.db.models.deletion.PROTECT, related_name='citas', to='citas.veterinario', verbose_name='veterinario')),
            ],
            options={
                'verbose_name': 'cita',
                'verbose_name_plural': 'citas',
                'db_table': 'cita',
                'ordering': ['fecha_cita', 'hora_inicio'],
                'indexes': [
                    models.Index(fields=['veterinario', 'fecha_cita'], name='idx_cita_vet_fecha'),
                    models.Index(fields=['fecha_cita', 'estado'], name='idx_cita_fecha_estado'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(('hora_fin__isnull', True), ('hora_fin__gt', models.F('hora_inicio')), _connector='OR'), name='chk_cita_hora_fin_mayor'),
                ],
            },
        ),
    ]
