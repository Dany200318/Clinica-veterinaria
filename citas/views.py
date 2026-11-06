from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from pacientes.models import Paciente, Propietario
from usuarios.roles import (
    VETERINARIO,
    administrador_o_veterinario,
    obtener_rol,
    solo_administrador,
    todo_el_personal,
)

from .forms import CitaForm, VeterinarioForm
from .models import Cita, Veterinario
from .utils import (
    DIAS_SEMANA,
    mes_anterior,
    mes_desde_parametro,
    mes_siguiente,
    nombre_mes,
    semanas_del_mes,
    ultimo_dia_mes,
)

ESTADOS_ACTIVOS = [Cita.PENDIENTE, Cita.CONFIRMADA]


def _veterinario_del_usuario(usuario):
    return Veterinario.objects.filter(usuario=usuario).first()


def _citas_por_dia(desde, hasta, veterinario=None):
    citas = (Cita.objects.filter(fecha_cita__range=[desde, hasta])
             .exclude(estado=Cita.CANCELADA)
             .select_related('paciente', 'veterinario'))
    if veterinario:
        citas = citas.filter(veterinario=veterinario)
    agrupadas = defaultdict(list)
    for c in citas:
        agrupadas[c.fecha_cita].append(c)
    return agrupadas


# ---------------------------------------------------------------------------
# Panel principal (RF-18, RF-13, CU-07)
# ---------------------------------------------------------------------------
@todo_el_personal
def dashboard(request):
    hoy = timezone.localdate()
    primero_mes = hoy.replace(day=1)
    fin_mes = ultimo_dia_mes(primero_mes)

    citas_hoy = (Cita.objects.filter(fecha_cita=hoy).select_related('paciente__propietario', 'veterinario')
                 .order_by('hora_inicio'))
    proximas = (Cita.objects
                .filter(fecha_cita__gt=hoy, fecha_cita__lte=hoy + timedelta(days=7), estado__in=ESTADOS_ACTIVOS)
                .select_related('paciente__propietario', 'veterinario')
                .order_by('fecha_cita', 'hora_inicio')[:10])

    # Filtro opcional «solo mis citas» para el veterinario (HU-09)
    mi_vet = _veterinario_del_usuario(request.user) if obtener_rol(request.user) == VETERINARIO else None
    solo_mias = bool(mi_vet and request.GET.get('mias') == '1')
    if solo_mias:
        citas_hoy = citas_hoy.filter(veterinario=mi_vet)
        proximas = (Cita.objects
                    .filter(fecha_cita__gt=hoy, fecha_cita__lte=hoy + timedelta(days=7),
                            estado__in=ESTADOS_ACTIVOS, veterinario=mi_vet)
                    .select_related('paciente__propietario', 'veterinario')
                    .order_by('fecha_cita', 'hora_inicio')[:10])

    citas_mes = Cita.objects.filter(fecha_cita__range=[primero_mes, fin_mes])
    contexto = {
        'hoy': hoy,
        'citas_hoy': citas_hoy,
        'proximas': proximas,
        'mi_vet': mi_vet,
        'solo_mias': solo_mias,
        # Tarjetas principales
        'total_citas_hoy': citas_hoy.exclude(estado=Cita.CANCELADA).count(),
        'total_pacientes': Paciente.objects.count(),
        'pacientes_mes': Paciente.objects.filter(fecha_registro__gte=primero_mes).count(),
        'citas_pendientes': Cita.objects.filter(estado=Cita.PENDIENTE, fecha_cita__gte=hoy).count(),
        'citas_mes': citas_mes.exclude(estado=Cita.CANCELADA).count(),
        # Estadísticas secundarias
        'total_propietarios': Propietario.objects.count(),
        'veterinarios_activos': Veterinario.objects.filter(activo=True).count(),
        'completadas_hoy': Cita.objects.filter(fecha_cita=hoy, estado=Cita.COMPLETADA).count(),
        'canceladas_mes': citas_mes.filter(estado=Cita.CANCELADA).count(),
        # Mini calendario del mes
        'mes_nombre': nombre_mes(primero_mes),
        'dias_semana': DIAS_SEMANA,
        'semanas': semanas_del_mes(primero_mes, _citas_por_dia(primero_mes, fin_mes)),
    }
    return render(request, 'citas/dashboard.html', contexto)


# ---------------------------------------------------------------------------
# Listado y calendario (RF-13, HU-09)
# ---------------------------------------------------------------------------
@todo_el_personal
def lista_citas(request):
    hoy = timezone.localdate()
    citas = Cita.objects.select_related('paciente__propietario', 'veterinario')

    periodo = request.GET.get('periodo', 'proximas')
    fecha = request.GET.get('fecha', '')
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    vet = request.GET.get('veterinario', '')

    if fecha:
        try:
            citas = citas.filter(fecha_cita=date.fromisoformat(fecha))
            periodo = 'fecha'
        except ValueError:
            fecha = ''
    if not fecha:
        if periodo == 'hoy':
            citas = citas.filter(fecha_cita=hoy)
        elif periodo == '7dias':
            citas = citas.filter(fecha_cita__range=[hoy, hoy + timedelta(days=7)])
        elif periodo == 'pasadas':
            citas = citas.filter(fecha_cita__lt=hoy)
        elif periodo == 'proximas':
            citas = citas.filter(fecha_cita__gte=hoy)

    if q:
        citas = citas.filter(Q(paciente__nombre__icontains=q) | Q(paciente__propietario__nombre__icontains=q)
                             | Q(motivo__icontains=q))
    if estado:
        citas = citas.filter(estado=estado)
    if tipo:
        citas = citas.filter(tipo_cita=tipo)
    if vet == 'mias':
        mi_vet = _veterinario_del_usuario(request.user)
        citas = citas.filter(veterinario=mi_vet) if mi_vet else citas.none()
    elif vet.isdigit():
        citas = citas.filter(veterinario_id=int(vet))

    orden = ['-fecha_cita', '-hora_inicio'] if periodo in ('pasadas', 'todas') else ['fecha_cita', 'hora_inicio']
    pagina = Paginator(citas.order_by(*orden), 15).get_page(request.GET.get('page'))
    return render(request, 'citas/lista.html', {
        'pagina': pagina,
        'periodo': periodo, 'fecha': fecha, 'q': q, 'estado': estado, 'tipo': tipo, 'vet': vet,
        'estados': Cita.ESTADO_CHOICES,
        'tipos': Cita.TIPO_CHOICES,
        'veterinarios': Veterinario.objects.order_by('-activo', 'nombre_completo'),
        'tiene_vet_propio': _veterinario_del_usuario(request.user) is not None,
    })


@todo_el_personal
def calendario_citas(request):
    hoy = timezone.localdate()
    primero = mes_desde_parametro(request.GET.get('mes'), hoy)
    vet_id = request.GET.get('veterinario', '')
    veterinario = Veterinario.objects.filter(pk=vet_id).first() if vet_id.isdigit() else None
    citas = _citas_por_dia(primero, ultimo_dia_mes(primero), veterinario)
    return render(request, 'citas/calendario.html', {
        'hoy': hoy,
        'mes_nombre': nombre_mes(primero),
        'mes_actual': primero.strftime('%Y-%m'),
        'mes_anterior': mes_anterior(primero).strftime('%Y-%m'),
        'mes_siguiente': mes_siguiente(primero).strftime('%Y-%m'),
        'dias_semana': DIAS_SEMANA,
        'semanas': semanas_del_mes(primero, citas),
        'veterinarios': Veterinario.objects.filter(activo=True),
        'vet_id': vet_id,
        'total_mes': sum(len(v) for v in citas.values()),
    })


# ---------------------------------------------------------------------------
# Alta, modificación y cancelación (RF-09 a RF-12, CU-05)
# ---------------------------------------------------------------------------
def _guardar_cita(request, form):
    """
    Guarda la cita dentro de una transacción, bloqueando el registro del
    veterinario para que dos recepcionistas no reserven el mismo horario al
    mismo tiempo. Devuelve la cita o None si hubo conflicto.
    """
    try:
        with transaction.atomic():
            veterinario = form.cleaned_data['veterinario']
            Veterinario.objects.select_for_update().filter(pk=veterinario.pk).first()
            cita = form.save(commit=False)
            if cita.creado_por_id is None and request.user.is_authenticated:
                cita.creado_por = request.user
            cita.validar_disponibilidad()  # Segunda verificación ya con el bloqueo
            cita.save()
            return cita
    except ValidationError as error:
        form.add_error(None, error)
    except DatabaseError:
        # El trigger de MySQL (si está instalado) también rechaza los traslapes
        form.add_error(None, 'No se puede agendar porque ya existe una cita en ese día y hora.')
    return None


def _notificar(request, cita, tipo, texto_ok):
    """Envía el correo y comunica el resultado al usuario (RF-15, CU-05 flujo 5a)."""
    from notificaciones.servicios import es_modo_prueba
    if es_modo_prueba():
        cita.enviar_notificacion_email(tipo)
        messages.info(request, f'{texto_ok}. MODO PRUEBA: el correo no se envió (solo se mostró en la '
                               'terminal). Configúrelo en Administración → Correo (SMTP).')
        return
    if cita.enviar_notificacion_email(tipo):
        messages.success(request, f'{texto_ok} y correo enviado a {cita.propietario.email}.')
    else:
        messages.warning(request, f'{texto_ok}, pero el correo no pudo enviarse. '
                                  'Revise la configuración de correo o el historial de notificaciones.')


@todo_el_personal
def crear_cita(request):
    if request.method == 'POST':
        form = CitaForm(request.POST)
        if form.is_valid():
            cita = _guardar_cita(request, form)
            if cita:
                if form.cleaned_data.get('notificar'):
                    _notificar(request, cita, 'confirmacion', 'Cita registrada')
                else:
                    messages.success(request, 'Cita registrada correctamente.')
                return redirect('detalle_cita', pk=cita.pk)
    else:
        inicial = {'estado': Cita.PENDIENTE}
        for campo in ('paciente', 'veterinario'):
            valor = request.GET.get(campo, '')
            if valor.isdigit():
                inicial[campo] = valor
        fecha = request.GET.get('fecha', '')
        try:
            inicial['fecha_cita'] = date.fromisoformat(fecha) if fecha else timezone.localdate()
        except ValueError:
            inicial['fecha_cita'] = timezone.localdate()
        if 'veterinario' not in inicial:
            mi_vet = _veterinario_del_usuario(request.user)
            if mi_vet and mi_vet.activo:
                inicial['veterinario'] = mi_vet.pk
        form = CitaForm(initial=inicial)
    return render(request, 'citas/form.html', {'form': form, 'titulo': 'Crear nueva cita'})


@todo_el_personal
def editar_cita(request, pk):
    cita = get_object_or_404(Cita, pk=pk)
    if request.method == 'POST':
        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            cambios = [c for c in form.changed_data if c != 'notificar']
            guardada = _guardar_cita(request, form)
            if guardada:
                tipo = 'cancelacion' if guardada.estado == Cita.CANCELADA else 'modificacion'
                if form.cleaned_data.get('notificar') and cambios:
                    _notificar(request, guardada, tipo, 'Cita actualizada')
                else:
                    messages.success(request, 'Cita actualizada correctamente.')
                return redirect('detalle_cita', pk=guardada.pk)
    else:
        form = CitaForm(instance=cita)
    return render(request, 'citas/form.html', {'form': form, 'titulo': 'Editar cita', 'cita': cita})


@todo_el_personal
def detalle_cita(request, pk):
    cita = get_object_or_404(Cita.objects.select_related('paciente__propietario', 'veterinario', 'creado_por'),
                             pk=pk)
    return render(request, 'citas/detalle.html', {
        'cita': cita,
        'notificaciones': cita.notificaciones.all()[:10],
        'estados': Cita.ESTADO_CHOICES,
    })


@todo_el_personal
@require_POST
def cambiar_estado_cita(request, pk):
    """Cambio rápido de estado: confirmar, completar o cancelar (RF-11, RF-12)."""
    cita = get_object_or_404(Cita, pk=pk)
    nuevo = request.POST.get('estado')
    if nuevo not in dict(Cita.ESTADO_CHOICES):
        messages.error(request, 'Estado no válido.')
        return redirect('detalle_cita', pk=pk)
    if nuevo == cita.estado:
        return redirect('detalle_cita', pk=pk)

    anterior = cita.estado
    cita.estado = nuevo
    try:
        with transaction.atomic():
            Veterinario.objects.select_for_update().filter(pk=cita.veterinario_id).first()
            if anterior == Cita.CANCELADA:
                cita.validar_disponibilidad()  # Reactivar una cita exige que el horario esté libre
            cita.save(update_fields=['estado', 'fecha_actualizacion'])
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
        return redirect('detalle_cita', pk=pk)
    except DatabaseError:
        messages.error(request, 'No se puede reactivar: el horario ya está ocupado.')
        return redirect('detalle_cita', pk=pk)

    texto = f'Estado cambiado a «{cita.get_estado_display()}»'
    if nuevo == Cita.CANCELADA:
        _notificar(request, cita, 'cancelacion', texto)
    elif nuevo == Cita.CONFIRMADA:
        _notificar(request, cita, 'modificacion', texto)
    else:
        messages.success(request, texto + '.')
    siguiente = request.POST.get('next')
    if siguiente and siguiente.startswith('/'):
        return redirect(siguiente)
    return redirect('detalle_cita', pk=pk)


@administrador_o_veterinario
def eliminar_cita(request, pk):
    """Eliminación definitiva (solo errores de registro). Para el uso normal se recomienda cancelar."""
    cita = get_object_or_404(Cita, pk=pk)
    if request.method == 'POST':
        cita.delete()
        messages.success(request, 'Cita eliminada definitivamente.')
        return redirect('lista_citas')
    return render(request, 'citas/eliminar.html', {'cita': cita})


@require_GET
@todo_el_personal
def disponibilidad(request):
    """
    Devuelve en JSON los horarios ocupados de un veterinario en una fecha.
    El formulario lo usa para advertir conflictos antes de guardar (HU-07).
    """
    vet = request.GET.get('veterinario', '')
    fecha = request.GET.get('fecha', '')
    excluir = request.GET.get('excluir', '')
    try:
        fecha = date.fromisoformat(fecha)
    except ValueError:
        return JsonResponse({'ocupados': []})
    if not vet.isdigit():
        return JsonResponse({'ocupados': []})
    citas = (Cita.objects.filter(veterinario_id=int(vet), fecha_cita=fecha)
             .exclude(estado=Cita.CANCELADA).select_related('paciente').order_by('hora_inicio'))
    if excluir.isdigit():
        citas = citas.exclude(pk=int(excluir))
    return JsonResponse({'ocupados': [
        {
            'inicio': c.hora_inicio.strftime('%H:%M'),
            'fin': c.hora_fin_efectiva.strftime('%H:%M'),
            'paciente': c.paciente.nombre,
            'estado': c.get_estado_display(),
        }
        for c in citas
    ]})


# ---------------------------------------------------------------------------
# Veterinarios (Tabla 5.4) — administración
# ---------------------------------------------------------------------------
@solo_administrador
def lista_veterinarios(request):
    hoy = timezone.localdate()
    veterinarios = Veterinario.objects.select_related('usuario').order_by('-activo', 'nombre_completo')
    for v in veterinarios:
        v.citas_proximas = v.citas.filter(fecha_cita__gte=hoy, estado__in=ESTADOS_ACTIVOS).count()
    return render(request, 'citas/veterinarios/lista.html', {'veterinarios': veterinarios})


@solo_administrador
def crear_veterinario(request):
    form = VeterinarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Veterinario registrado.')
        return redirect('lista_veterinarios')
    return render(request, 'citas/veterinarios/form.html', {'form': form, 'titulo': 'Nuevo veterinario'})


@solo_administrador
def editar_veterinario(request, pk):
    veterinario = get_object_or_404(Veterinario, pk=pk)
    form = VeterinarioForm(request.POST or None, instance=veterinario)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Veterinario actualizado.')
        return redirect('lista_veterinarios')
    return render(request, 'citas/veterinarios/form.html', {
        'form': form, 'titulo': f'Editar veterinario: {veterinario}',
    })
