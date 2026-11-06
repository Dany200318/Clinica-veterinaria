import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('citas', '0001_initial'),
        ('pacientes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracionCorreo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('usar_esta_configuracion', models.BooleanField(default=False, help_text='Si está desactivado se usan los valores del archivo .env.', verbose_name='usar esta configuración')),
                ('servidor', models.CharField(default='smtp.gmail.com', max_length=150, verbose_name='servidor SMTP')),
                ('puerto', models.PositiveIntegerField(default=587, verbose_name='puerto')),
                ('usar_tls', models.BooleanField(default=True, verbose_name='usar TLS')),
                ('usar_ssl', models.BooleanField(default=False, verbose_name='usar SSL')),
                ('usuario', models.CharField(blank=True, max_length=150, verbose_name='usuario / correo')),
                ('contrasena', models.CharField(blank=True, help_text='Déjela vacía para usar EMAIL_PASSWORD del archivo .env (recomendado).', max_length=150, verbose_name='contraseña de aplicación')),
                ('remitente', models.CharField(blank=True, help_text='Ej.: Clínica Veterinaria <citas@clinica.com>', max_length=150, verbose_name='nombre del remitente')),
                ('dias_recordatorio_cita', models.PositiveSmallIntegerField(default=1, help_text='Se envía el recordatorio a las citas que ocurrirán dentro de este número de días.', verbose_name='días de anticipación (citas)')),
                ('dias_recordatorio_vacuna', models.PositiveSmallIntegerField(default=7, verbose_name='días de anticipación (vacunas)')),
                ('fecha_actualizacion', models.DateTimeField(auto_now=True, verbose_name='última modificación')),
            ],
            options={
                'verbose_name': 'configuración de correo',
                'verbose_name_plural': 'configuración de correo',
                'db_table': 'configuracion_correo',
            },
        ),
        migrations.CreateModel(
            name='Notificacion',
            fields=[
                ('id_notificacion', models.AutoField(primary_key=True, serialize=False)),
                ('tipo', models.CharField(choices=[('confirmacion', 'Confirmación de cita'), ('modificacion', 'Modificación de cita'), ('cancelacion', 'Cancelación de cita'), ('recordatorio_cita', 'Recordatorio de cita'), ('recordatorio_vacuna', 'Recordatorio de vacuna'), ('prueba', 'Correo de prueba')], max_length=25, verbose_name='tipo')),
                ('destinatario', models.EmailField(max_length=254, verbose_name='destinatario')),
                ('asunto', models.CharField(max_length=200, verbose_name='asunto')),
                ('estado', models.CharField(choices=[('enviado', 'Enviado'), ('error', 'Error')], max_length=10, verbose_name='estado')),
                ('detalle_error', models.TextField(blank=True, verbose_name='detalle del error')),
                ('fecha_envio', models.DateTimeField(auto_now_add=True, verbose_name='fecha de envío')),
                ('cita', models.ForeignKey(blank=True, db_column='id_cita', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notificaciones', to='citas.cita')),
                ('vacuna', models.ForeignKey(blank=True, db_column='id_vacuna', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='notificaciones', to='pacientes.vacuna')),
            ],
            options={
                'verbose_name': 'notificación',
                'verbose_name_plural': 'notificaciones',
                'db_table': 'notificacion',
                'ordering': ['-fecha_envio'],
                'indexes': [
                    models.Index(fields=['tipo', 'estado'], name='idx_notif_tipo_estado'),
                    models.Index(fields=['fecha_envio'], name='idx_notif_fecha'),
                ],
            },
        ),
    ]
