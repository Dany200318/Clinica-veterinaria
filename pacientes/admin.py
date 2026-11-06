from django.contrib import admin

from .models import Paciente, Propietario, Vacuna


class PacienteInline(admin.TabularInline):
    model = Paciente
    extra = 0
    fields = ('nombre', 'especie', 'raza', 'sexo', 'fecha_nacimiento')
    show_change_link = True


@admin.register(Propietario)
class PropietarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'dpi', 'zona')
    search_fields = ('nombre', 'telefono', 'email', 'dpi')
    inlines = [PacienteInline]


class VacunaInline(admin.TabularInline):
    model = Vacuna
    extra = 0


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'raza', 'sexo', 'propietario', 'fecha_registro')
    list_filter = ('especie', 'sexo', 'esterilizado')
    search_fields = ('nombre', 'raza', 'microchip', 'propietario__nombre')
    autocomplete_fields = ('propietario',)
    inlines = [VacunaInline]


@admin.register(Vacuna)
class VacunaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nombre', 'fecha_aplicacion', 'fecha_proxima')
    list_filter = ('nombre',)
    search_fields = ('paciente__nombre', 'nombre')
    date_hierarchy = 'fecha_aplicacion'
