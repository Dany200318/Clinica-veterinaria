"""
Roles del sistema y control de acceso (RF-03, Tabla 5.7 — Matriz de permisos por rol).

Los roles se guardan como grupos de Django (tabla auth_group):
    Administrador, Veterinario y Recepcionista.

Matriz de permisos aplicada:
    Funcionalidad                             Admin  Veterinario  Recepcionista
    Gestionar usuarios y roles                 Sí     No           No
    Registrar y editar propietarios/pacientes  Sí     Sí           Sí (sin eliminar)
    Agendar, modificar y cancelar citas        Sí     Sí           Sí
    Consultar el panel principal               Sí     Sí           Sí
    Consultar reportes y estadísticas          Sí     Sí           No
"""
from functools import wraps

from django.core.exceptions import PermissionDenied

ADMINISTRADOR = 'Administrador'
VETERINARIO = 'Veterinario'
RECEPCIONISTA = 'Recepcionista'

ROLES = [ADMINISTRADOR, VETERINARIO, RECEPCIONISTA]
ROLES_CHOICES = [(r, r) for r in ROLES]


def obtener_rol(usuario):
    """Devuelve el nombre del rol del usuario. El superusuario siempre es Administrador."""
    if usuario is None or not usuario.is_authenticated:
        return None
    if usuario.is_superuser:
        return ADMINISTRADOR
    # Se usa la caché del objeto para no consultar la BD en cada plantilla
    if not hasattr(usuario, '_rol_cache'):
        nombres = set(usuario.groups.values_list('name', flat=True))
        usuario._rol_cache = next((r for r in ROLES if r in nombres), None)
    return usuario._rol_cache


def tiene_rol(usuario, *roles):
    return obtener_rol(usuario) in roles


def puede_administrar_usuarios(usuario):
    return tiene_rol(usuario, ADMINISTRADOR)


def puede_ver_reportes(usuario):
    return tiene_rol(usuario, ADMINISTRADOR, VETERINARIO)


def puede_eliminar_registros(usuario):
    return tiene_rol(usuario, ADMINISTRADOR, VETERINARIO)


def rol_requerido(*roles):
    """
    Decorador para vistas: permite el acceso solo a los roles indicados.
    Si el usuario no tiene el rol, Django muestra la página 403 (acceso denegado).
    """
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not tiene_rol(request.user, *roles):
                raise PermissionDenied('No tiene permiso para acceder a esta función.')
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


solo_administrador = rol_requerido(ADMINISTRADOR)
administrador_o_veterinario = rol_requerido(ADMINISTRADOR, VETERINARIO)
todo_el_personal = rol_requerido(ADMINISTRADOR, VETERINARIO, RECEPCIONISTA)
