from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.views import PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .forms import UsuarioCrearForm, UsuarioEditarForm, es_veterinario
from .roles import obtener_rol, solo_administrador


@solo_administrador
def lista_usuarios(request):
    """Listado de usuarios del personal (CU-02)."""
    q = request.GET.get('q', '').strip()
    usuarios = User.objects.prefetch_related('groups').order_by('-is_active', 'username')
    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q)
            | Q(last_name__icontains=q) | Q(email__icontains=q)
        )
    pagina = Paginator(usuarios, 15).get_page(request.GET.get('page'))
    for u in pagina:
        u.rol = obtener_rol(u) or 'Sin rol'
    return render(request, 'usuarios/lista.html', {'pagina': pagina, 'q': q})


@solo_administrador
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioCrearForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            if es_veterinario(form.cleaned_data) and form.cleaned_data.get('crear_veterinario'):
                from citas.models import Veterinario
                Veterinario.objects.get_or_create(
                    usuario=usuario,
                    defaults={'nombre_completo': usuario.get_full_name() or usuario.username},
                )
            messages.success(request, f'Usuario "{usuario.username}" creado correctamente.')
            return redirect('lista_usuarios')
    else:
        form = UsuarioCrearForm()
    return render(request, 'usuarios/form.html', {'form': form, 'titulo': 'Nuevo usuario'})


@solo_administrador
def editar_usuario(request, pk):
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UsuarioEditarForm(request.POST, instance=usuario)
        if form.is_valid():
            if usuario == request.user and not form.cleaned_data['is_active']:
                form.add_error('is_active', 'No puede desactivar su propia cuenta.')
            else:
                form.save()
                messages.success(request, 'Usuario actualizado correctamente.')
                return redirect('lista_usuarios')
    else:
        form = UsuarioEditarForm(instance=usuario)
    return render(request, 'usuarios/form.html', {
        'form': form, 'titulo': f'Editar usuario: {usuario.username}', 'usuario_obj': usuario,
    })


@solo_administrador
@require_POST
def cambiar_estado_usuario(request, pk):
    """Activa o desactiva un usuario (RF-02). No se eliminan usuarios para conservar la trazabilidad."""
    usuario = get_object_or_404(User, pk=pk)
    if usuario == request.user:
        messages.error(request, 'No puede desactivar su propia cuenta.')
    else:
        usuario.is_active = not usuario.is_active
        usuario.save(update_fields=['is_active'])
        estado = 'activado' if usuario.is_active else 'desactivado'
        messages.success(request, f'Usuario "{usuario.username}" {estado}.')
    return redirect('lista_usuarios')


@solo_administrador
def restablecer_password(request, pk):
    """El administrador asigna una nueva contraseña a un usuario."""
    usuario = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = SetPasswordForm(usuario, request.POST)
        if form.is_valid():
            form.save()
            if usuario == request.user:
                update_session_auth_hash(request, usuario)
            messages.success(request, f'Contraseña de "{usuario.username}" actualizada.')
            return redirect('lista_usuarios')
    else:
        form = SetPasswordForm(usuario)
    return render(request, 'usuarios/password.html', {
        'form': form, 'titulo': f'Nueva contraseña para {usuario.username}',
    })


class CambiarMiPasswordView(SuccessMessageMixin, PasswordChangeView):
    """Cualquier usuario puede cambiar su propia contraseña."""

    template_name = 'usuarios/password.html'
    success_url = reverse_lazy('dashboard')
    success_message = 'Su contraseña fue cambiada correctamente.'
    extra_context = {'titulo': 'Cambiar mi contraseña'}
