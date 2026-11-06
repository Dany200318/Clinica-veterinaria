from django.contrib import admin

from .models import ConfiguracionCorreo, Notificacion


@admin.register(ConfiguracionCorreo)
class ConfiguracionCorreoAdmin(admin.ModelAdmin):
    list_display = ('servidor', 'puerto', 'usuario', 'usar_esta_configuracion', 'fecha_actualizacion')


@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('fecha_envio', 'tipo', 'destinatario', 'estado', 'cita', 'vacuna')
    list_filter = ('tipo', 'estado', 'fecha_envio')
    search_fields = ('destinatario', 'asunto')
    date_hierarchy = 'fecha_envio'
    readonly_fields = [f.name for f in Notificacion._meta.fields]
