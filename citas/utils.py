"""Utilidades para construir calendarios mensuales (RF-13)."""
import calendar
from datetime import date, timedelta

MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
         'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
DIAS_SEMANA = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']


def mes_desde_parametro(valor, por_defecto):
    """Convierte 'AAAA-MM' en date(AAAA, MM, 1)."""
    try:
        anio, mes = (int(x) for x in valor.split('-')[:2])
        return date(anio, mes, 1)
    except (AttributeError, ValueError):
        return por_defecto.replace(day=1)


def mes_anterior(primero):
    return (primero.replace(day=1) - timedelta(days=1)).replace(day=1)


def mes_siguiente(primero):
    return (primero.replace(day=28) + timedelta(days=4)).replace(day=1)


def ultimo_dia_mes(primero):
    return primero.replace(day=calendar.monthrange(primero.year, primero.month)[1])


def semanas_del_mes(primero, citas_por_dia):
    """
    Devuelve una lista de semanas; cada día es un dict con la fecha, si pertenece
    al mes y la lista de citas de ese día. La semana inicia en domingo.
    """
    cal = calendar.Calendar(firstweekday=6)
    semanas = []
    for semana in cal.monthdatescalendar(primero.year, primero.month):
        semanas.append([
            {
                'fecha': dia,
                'del_mes': dia.month == primero.month,
                'citas': citas_por_dia.get(dia, []),
            }
            for dia in semana
        ])
    return semanas


def nombre_mes(primero):
    return f'{MESES[primero.month]} {primero.year}'
