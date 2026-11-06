from django.conf import settings

from usuarios.roles import (
    obtener_rol,
    puede_administrar_usuarios,
    puede_eliminar_registros,
    puede_ver_reportes,
)


def datos_generales(request):
    """Variables disponibles en todas las plantillas (nombre de la clínica y permisos del rol)."""
    usuario = getattr(request, 'user', None)
    autenticado = bool(usuario and usuario.is_authenticated)
    parametros = request.GET.copy()
    parametros.pop('page', None)
    return {
        'parametros_get': parametros.urlencode(),
        'CLINICA_NOMBRE': settings.CLINICA_NOMBRE,
        'CITA_DURACION_MINUTOS': settings.CITA_DURACION_MINUTOS,
        'rol_usuario': obtener_rol(usuario) if autenticado else None,
        'puede_admin': autenticado and puede_administrar_usuarios(usuario),
        'puede_reportes': autenticado and puede_ver_reportes(usuario),
        'puede_eliminar': autenticado and puede_eliminar_registros(usuario),
    }
