from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from usuarios.roles import solo_administrador

from .forms import ConfiguracionCorreoForm, CorreoPruebaForm
from .models import ConfiguracionCorreo, Notificacion
from .servicios import (
    enviar_correo_cita,
    enviar_correo_prueba,
    enviar_correo_vacuna,
    enviar_recordatorios,
    es_modo_prueba,
    estado_correo,
)


def explicar_error(detalle):
    """Traduce los errores SMTP más comunes a una indicación clara."""
    if 'SMTPAuthenticationError' in detalle or '535' in detalle:
        return ('Gmail rechazó el usuario o la contraseña. Use una CONTRASEÑA DE APLICACIÓN de 16 letras '
                '(no la contraseña normal) y verifique que el correo esté bien escrito.')
    if 'getaddrinfo' in detalle or 'timed out' in detalle or 'ConnectionRefused' in detalle:
        return 'No hay conexión con el servidor de correo. Revise el internet, el servidor y el puerto (587).'
    if 'SSL' in detalle or 'WRONG_VERSION' in detalle:
        return 'Error de cifrado: con el puerto 587 active solo TLS; con el puerto 465 active solo SSL.'
    return detalle


@solo_administrador
def configuracion_correo(request):
    """Configuración del servidor SMTP desde el sistema (RF-17, HU-16)."""
    config = ConfiguracionCorreo.obtener()
    form = ConfiguracionCorreoForm(instance=config)
    form_prueba = CorreoPruebaForm(initial={'destinatario': request.user.email})

    if request.method == 'POST':
        if 'probar' in request.POST:
            form_prueba = CorreoPruebaForm(request.POST)
            if form_prueba.is_valid():
                destino = form_prueba.cleaned_data['destinatario']
                ok = enviar_correo_prueba(destino)
                if ok and es_modo_prueba():
                    messages.warning(request, 'MODO PRUEBA: el correo NO se envió, solo se mostró en la terminal. '
                                              'Marque «Usar esta configuración», complete el correo y la '
                                              'contraseña de aplicación y guarde.')
                elif ok:
                    messages.success(request, f'Correo de prueba enviado a {destino}. Revise la bandeja de '
                                              'entrada (y la carpeta de spam).')
                else:
                    ultimo = Notificacion.objects.filter(tipo='prueba').first()
                    messages.error(request, 'No se pudo enviar el correo de prueba. '
                                            + explicar_error(ultimo.detalle_error if ultimo else ''))
                return redirect('configuracion_correo')
        else:
            form = ConfiguracionCorreoForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, 'Configuración de correo guardada.')
                return redirect('configuracion_correo')

    return render(request, 'notificaciones/configuracion.html', {
        'form': form, 'form_prueba': form_prueba, 'config': config, 'estado': estado_correo(),
    })


@solo_administrador
def historial_notificaciones(request):
    """Bitácora de correos enviados con su resultado (RF-15)."""
    notificaciones = Notificacion.objects.select_related('cita__paciente', 'vacuna__paciente')
    tipo = request.GET.get('tipo', '')
    estado = request.GET.get('estado', '')
    if tipo:
        notificaciones = notificaciones.filter(tipo=tipo)
    if estado:
        notificaciones = notificaciones.filter(estado=estado)

    total = Notificacion.objects.count()
    enviadas = Notificacion.objects.filter(estado='enviado').count()
    porcentaje = round(enviadas * 100 / total, 1) if total else 0

    pagina = Paginator(notificaciones, 20).get_page(request.GET.get('page'))
    return render(request, 'notificaciones/historial.html', {
        'pagina': pagina,
        'tipos': Notificacion.TIPO_CHOICES,
        'tipo': tipo,
        'estado': estado,
        'total': total,
        'enviadas': enviadas,
        'errores': total - enviadas,
        'porcentaje': porcentaje,
    })


@solo_administrador
@require_POST
def ejecutar_recordatorios(request):
    """Ejecuta manualmente la tarea de recordatorios (la misma que corre programada)."""
    r = enviar_recordatorios()
    enviados = r['citas_enviadas'] + r['vacunas_enviadas']
    errores = r['citas_error'] + r['vacunas_error']
    if es_modo_prueba() and enviados:
        messages.warning(request, f'MODO PRUEBA: {enviados} recordatorio(s) se mostraron en la terminal pero NO '
                                  'se enviaron. Configure el correo en Administración → Correo (SMTP).')
    elif enviados == 0 and errores == 0:
        messages.info(request, 'No hay recordatorios pendientes de enviar.')
    else:
        nivel = messages.warning if errores else messages.success
        nivel(request, f'Recordatorios enviados: {enviados}. Con error: {errores}.')
    return redirect('historial_notificaciones')


@solo_administrador
@require_POST
def reenviar_notificacion(request, pk):
    notificacion = get_object_or_404(Notificacion, pk=pk)
    ok = False
    if notificacion.cita_id:
        ok = enviar_correo_cita(notificacion.cita, notificacion.tipo)
    elif notificacion.vacuna_id:
        ok = enviar_correo_vacuna(notificacion.vacuna)
    elif notificacion.tipo == 'prueba':
        ok = enviar_correo_prueba(notificacion.destinatario)
    if ok:
        messages.success(request, 'Correo reenviado correctamente.')
    else:
        messages.error(request, 'No se pudo reenviar el correo. Revise la configuración SMTP.')
    return redirect('historial_notificaciones')
