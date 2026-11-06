"""
Reportes y estadísticas (RF-19 a RF-21, CU-08).
Acceso: Administrador y Veterinario (Tabla 5.7).
"""
import csv
from datetime import date, datetime, time, timedelta

from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from citas.models import Cita, Veterinario
from citas.utils import MESES, mes_anterior, mes_siguiente
from notificaciones.models import Notificacion
from pacientes.models import Paciente, Propietario, Vacuna
from usuarios.roles import administrador_o_veterinario


def _periodo(request):
    """Lee el período del filtro (RF-21). Por defecto: últimos 6 meses hasta fin del mes actual."""
    hoy = timezone.localdate()
    inicio_defecto = hoy.replace(day=1)
    for _ in range(5):
        inicio_defecto = mes_anterior(inicio_defecto)
    fin_defecto = mes_siguiente(hoy.replace(day=1)) - timedelta(days=1)

    def leer(nombre, defecto):
        try:
            return date.fromisoformat(request.GET.get(nombre, ''))
        except ValueError:
            return defecto

    inicio = leer('fecha_inicio', inicio_defecto)
    fin = leer('fecha_fin', fin_defecto)
    if fin < inicio:
        inicio, fin = fin, inicio
    return inicio, fin


def _distribucion(queryset, campo, etiquetas=None):
    """Lista de dicts {etiqueta, total, porcentaje} para dibujar barras de progreso."""
    filas = queryset.values(campo).annotate(total=Count('pk')).order_by('-total')
    total = sum(f['total'] for f in filas) or 1
    etiquetas = etiquetas or {}
    return [
        {
            'clave': f[campo],
            'etiqueta': etiquetas.get(f[campo], f[campo] or 'Sin especificar'),
            'total': f['total'],
            'porcentaje': round(f['total'] * 100 / total, 1),
        }
        for f in filas
    ]


def _tendencia_mensual(citas, inicio, fin):
    """Cantidad de citas por mes dentro del período (RF-20)."""
    meses = []
    actual = inicio.replace(day=1)
    while actual <= fin:
        siguiente = mes_siguiente(actual)
        del_mes = citas.filter(fecha_cita__gte=actual, fecha_cita__lt=siguiente)
        meses.append({
            'etiqueta': f'{MESES[actual.month][:3]} {actual.year}',
            'total': del_mes.count(),
            'completadas': del_mes.filter(estado=Cita.COMPLETADA).count(),
            'canceladas': del_mes.filter(estado=Cita.CANCELADA).count(),
        })
        actual = siguiente
    maximo = max([m['total'] for m in meses] + [1])
    for m in meses:
        m['porcentaje'] = round(m['total'] * 100 / maximo, 1)
    return meses


@administrador_o_veterinario
def reportes(request):
    hoy = timezone.localdate()
    inicio, fin = _periodo(request)
    citas = Cita.objects.filter(fecha_cita__range=[inicio, fin])
    vet_id = request.GET.get('veterinario', '')
    if vet_id.isdigit():
        citas = citas.filter(veterinario_id=int(vet_id))

    total_citas = citas.count()
    completadas = citas.filter(estado=Cita.COMPLETADA).count()
    canceladas = citas.filter(estado=Cita.CANCELADA).count()
    # Citas de fechas ya pasadas que no se completaron ni cancelaron = inasistencias
    no_atendidas = citas.filter(fecha_cita__lt=hoy, estado__in=[Cita.PENDIENTE, Cita.CONFIRMADA]).count()
    base_asistencia = completadas + no_atendidas
    tasa_asistencia = round(completadas * 100 / base_asistencia, 1) if base_asistencia else None
    tasa_cancelacion = round(canceladas * 100 / total_citas, 1) if total_citas else 0

    # Pacientes (se reportan todos los registrados; los nuevos del período aparte)
    pacientes = Paciente.objects.all()

    # Vacunas
    vacunas_periodo = Vacuna.objects.filter(fecha_aplicacion__range=[inicio, fin])
    vacunas_proximas = Vacuna.objects.filter(fecha_proxima__range=[hoy, hoy + timedelta(days=30)]).count()
    vacunas_vencidas = Vacuna.objects.filter(fecha_proxima__lt=hoy).count()

    # Notificaciones (indicador: % de correos entregados sin error, Tabla 6.4)
    desde = timezone.make_aware(datetime.combine(inicio, time.min))
    hasta = timezone.make_aware(datetime.combine(fin + timedelta(days=1), time.min))
    notif = Notificacion.objects.filter(fecha_envio__gte=desde, fecha_envio__lt=hasta)
    notif_total = notif.count()
    notif_ok = notif.filter(estado='enviado').count()

    por_vet = (citas.values('veterinario__nombre_completo')
               .annotate(total=Count('pk')).order_by('-total'))
    total_vet = sum(v['total'] for v in por_vet) or 1

    contexto = {
        'inicio': inicio,
        'fin': fin,
        'vet_id': vet_id,
        'veterinarios': Veterinario.objects.order_by('-activo', 'nombre_completo'),
        # Tarjetas
        'total_citas': total_citas,
        'total_pacientes': pacientes.count(),
        'pacientes_nuevos': pacientes.filter(fecha_registro__range=[inicio, fin]).count(),
        'completadas': completadas,
        'total_propietarios': Propietario.objects.count(),
        'tasa_asistencia': tasa_asistencia,
        'no_atendidas': no_atendidas,
        'tasa_cancelacion': tasa_cancelacion,
        # Distribuciones (RF-19)
        'por_estado': _distribucion(citas, 'estado', dict(Cita.ESTADO_CHOICES)),
        'por_tipo': _distribucion(citas, 'tipo_cita', dict(Cita.TIPO_CHOICES)),
        'por_veterinario': [
            {'etiqueta': v['veterinario__nombre_completo'], 'total': v['total'],
             'porcentaje': round(v['total'] * 100 / total_vet, 1)}
            for v in por_vet
        ],
        'por_especie': _distribucion(pacientes, 'especie', dict(Paciente.ESPECIE_CHOICES)),
        'por_sexo': _distribucion(pacientes, 'sexo', dict(Paciente.SEXO_CHOICES)),
        # Tendencia (RF-20)
        'tendencia': _tendencia_mensual(citas, inicio, fin),
        # Vacunación
        'vacunas_aplicadas': vacunas_periodo.count(),
        'vacunas_por_nombre': _distribucion(vacunas_periodo, 'nombre')[:8],
        'vacunas_proximas': vacunas_proximas,
        'vacunas_vencidas': vacunas_vencidas,
        # Notificaciones
        'notif_total': notif_total,
        'notif_ok': notif_ok,
        'notif_porcentaje': round(notif_ok * 100 / notif_total, 1) if notif_total else None,
        'generado': timezone.localtime(),
    }
    return render(request, 'reportes/reportes.html', contexto)


def _respuesta_csv(nombre):
    respuesta = HttpResponse(content_type='text/csv; charset=utf-8')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}"'
    respuesta.write('﻿')  # BOM para que Excel muestre bien las tildes
    return respuesta


@administrador_o_veterinario
def exportar_citas_csv(request):
    inicio, fin = _periodo(request)
    citas = (Cita.objects.filter(fecha_cita__range=[inicio, fin])
             .select_related('paciente__propietario', 'veterinario').order_by('fecha_cita', 'hora_inicio'))
    respuesta = _respuesta_csv(f'citas_{inicio}_{fin}.csv')
    escritor = csv.writer(respuesta)
    escritor.writerow(['ID', 'Fecha', 'Hora inicio', 'Hora fin', 'Paciente', 'Especie', 'Propietario',
                       'Teléfono', 'Veterinario', 'Tipo', 'Estado', 'Motivo'])
    for c in citas:
        escritor.writerow([
            c.pk, c.fecha_cita.strftime('%d/%m/%Y'), c.hora_inicio.strftime('%H:%M'),
            c.hora_fin.strftime('%H:%M') if c.hora_fin else '', c.paciente.nombre, c.paciente.especie,
            c.paciente.propietario.nombre, c.paciente.propietario.telefono, c.veterinario.nombre_completo,
            c.get_tipo_cita_display(), c.get_estado_display(), c.motivo,
        ])
    return respuesta


@administrador_o_veterinario
def exportar_pacientes_csv(request):
    pacientes = Paciente.objects.select_related('propietario').order_by('nombre')
    respuesta = _respuesta_csv('pacientes.csv')
    escritor = csv.writer(respuesta)
    escritor.writerow(['ID', 'Nombre', 'Especie', 'Raza', 'Sexo', 'Fecha nacimiento', 'Peso (lb)',
                       'Esterilizado', 'Alergias', 'Propietario', 'Teléfono', 'Correo', 'Registro'])
    for p in pacientes:
        escritor.writerow([
            p.pk, p.nombre, p.especie, p.raza, p.get_sexo_display(),
            p.fecha_nacimiento.strftime('%d/%m/%Y') if p.fecha_nacimiento else '',
            p.peso or '', 'Sí' if p.esterilizado else 'No', p.alergias,
            p.propietario.nombre, p.propietario.telefono, p.propietario.email,
            p.fecha_registro.strftime('%d/%m/%Y'),
        ])
    return respuesta
