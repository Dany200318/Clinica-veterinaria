from django.contrib import admin

from .models import Cita, Veterinario


@admin.register(Veterinario)
class VeterinarioAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'activo', 'usuario')
    list_filter = ('activo',)
    search_fields = ('nombre_completo',)


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('fecha_cita', 'hora_inicio', 'hora_fin', 'paciente', 'veterinario', 'tipo_cita', 'estado')
    list_filter = ('estado', 'tipo_cita', 'veterinario', 'fecha_cita')
    search_fields = ('paciente__nombre', 'paciente__propietario__nombre', 'motivo')
    date_hierarchy = 'fecha_cita'
    autocomplete_fields = ('paciente',)
    readonly_fields = ('creado_por', 'fecha_creacion', 'fecha_actualizacion')
