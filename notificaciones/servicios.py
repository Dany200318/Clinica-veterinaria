"""
Servicio de envío de correos (sección 5.2.3).

- enviar_correo_cita(): confirmación / modificación / cancelación de una cita (RF-14).
- enviar_recordatorios(): recordatorios de citas próximas y vacunas por vencer (RF-16).
- Cada envío queda registrado en la tabla «notificacion» con su resultado (RF-15).
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

from .models import ConfiguracionCorreo, Notificacion

logger = logging.getLogger('notificaciones')

ASUNTOS = {
    'confirmacion': 'Confirmación de cita para {paciente}',
    'modificacion': 'Su cita para {paciente} fue modificada',
    'cancelacion': 'Su cita para {paciente} fue cancelada',
    'recordatorio_cita': 'Recordatorio: cita de {paciente} el {fecha}',
    'recordatorio_vacuna': 'Recordatorio de vacuna para {paciente}',
    'prueba': 'Correo de prueba del sistema',
}


# ---------------------------------------------------------------------------
# Conexión SMTP (RF-17)
# ---------------------------------------------------------------------------
def obtener_conexion_y_remitente():
    """
    Devuelve (conexión, remitente). Usa la configuración guardada en el sistema
    si está activada; si no, la del archivo .env (settings.py).
    """
    config = ConfiguracionCorreo.objects.filter(pk=1).first()
    if config and config.usar_esta_configuracion:
        conexion = get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=config.servidor,
            port=config.puerto,
            username=config.usuario or settings.EMAIL_HOST_USER,
            password=config.contrasena or settings.EMAIL_HOST_PASSWORD,
            use_tls=config.usar_tls and not config.usar_ssl,
            use_ssl=config.usar_ssl,
            timeout=settings.EMAIL_TIMEOUT,
        )
        cuenta = config.usuario or settings.EMAIL_HOST_USER
        remitente = config.remitente or cuenta or settings.DEFAULT_FROM_EMAIL
        if '@' not in remitente and cuenta:
            remitente = f'{remitente} <{cuenta}>'  # «Clínica Veterinaria» -> «Clínica Veterinaria <cuenta>»
    else:
        conexion = get_connection(timeout=settings.EMAIL_TIMEOUT)
        remitente = settings.DEFAULT_FROM_EMAIL
    return conexion, remitente


def estado_correo():
    """
    Indica cómo se están enviando los correos en este momento:
      * 'pantalla' -> SMTP configurado en Administración > Correo (SMTP)
      * 'env'      -> SMTP configurado en el archivo .env
      * 'consola'  -> MODO PRUEBA: los correos solo se muestran en la terminal
      * 'sin_configurar' -> falta usuario o contraseña SMTP
    """
    config = ConfiguracionCorreo.objects.filter(pk=1).first()
    if config and config.usar_esta_configuracion:
        usuario = config.usuario or settings.EMAIL_HOST_USER
        clave = config.contrasena or settings.EMAIL_HOST_PASSWORD
        if usuario and clave:
            return {'modo': 'pantalla', 'cuenta': usuario}
        return {'modo': 'sin_configurar', 'cuenta': usuario}
    if 'console' in settings.EMAIL_BACKEND:
        return {'modo': 'consola', 'cuenta': ''}
    if 'smtp' in settings.EMAIL_BACKEND and not (settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD):
        return {'modo': 'sin_configurar', 'cuenta': settings.EMAIL_HOST_USER}
    return {'modo': 'env', 'cuenta': settings.EMAIL_HOST_USER}


def es_modo_prueba():
    return estado_correo()['modo'] == 'consola'


def enviar_correo(destinatario, tipo, plantilla, contexto, asunto, cita=None, vacuna=None):
    """
    Envía un correo con versión de texto y HTML, y registra el resultado.
    Nunca lanza excepción: devuelve True (enviado) o False (error).
    """
    contexto = {
        **contexto,
        'clinica_nombre': settings.CLINICA_NOMBRE,
        'clinica_telefono': settings.CLINICA_TELEFONO,
        'clinica_direccion': settings.CLINICA_DIRECCION,
    }
    registro = Notificacion(
        tipo=tipo, cita=cita, vacuna=vacuna,
        destinatario=destinatario or '', asunto=asunto[:200],
    )
    try:
        if not destinatario:
            raise ValueError('El propietario no tiene correo electrónico registrado.')
        texto = render_to_string(f'notificaciones/correos/{plantilla}.txt', contexto)
        html = render_to_string(f'notificaciones/correos/{plantilla}.html', contexto)
        conexion, remitente = obtener_conexion_y_remitente()
        mensaje = EmailMultiAlternatives(
            subject=asunto, body=texto, from_email=remitente,
            to=[destinatario], connection=conexion,
        )
        mensaje.attach_alternative(html, 'text/html')
        if estado_correo()['modo'] == 'sin_configurar':
            raise ValueError('Falta configurar el usuario y la contraseña de aplicación del correo '
                             '(Administración > Correo SMTP).')
        mensaje.send(fail_silently=False)
        registro.estado = 'enviado'
        if es_modo_prueba():
            registro.detalle_error = 'Modo prueba: el correo se mostró en la terminal y no se envió.'
        logger.info('Correo %s enviado a %s', tipo, destinatario)
    except Exception as error:  # noqa: BLE001 — se registra cualquier fallo del servidor SMTP
        registro.estado = 'error'
        registro.detalle_error = f'{type(error).__name__}: {error}'[:2000]
        logger.warning('Error al enviar correo %s a %s: %s', tipo, destinatario, error)
    registro.save()
    return registro.estado == 'enviado'


# ---------------------------------------------------------------------------
# Correos de citas (RF-14, RF-15)
# ---------------------------------------------------------------------------
def enviar_correo_cita(cita, tipo='confirmacion'):
    propietario = cita.paciente.propietario
    asunto = ASUNTOS[tipo].format(paciente=cita.paciente.nombre, fecha=f'{cita.fecha_cita:%d/%m/%Y}')
    plantilla = 'recordatorio_cita' if tipo == 'recordatorio_cita' else 'cita'
    return enviar_correo(
        destinatario=propietario.email,
        tipo=tipo,
        plantilla=plantilla,
        contexto={'cita': cita, 'propietario': propietario, 'paciente': cita.paciente, 'tipo': tipo},
        asunto=asunto,
        cita=cita,
    )


def enviar_correo_vacuna(vacuna):
    propietario = vacuna.paciente.propietario
    return enviar_correo(
        destinatario=propietario.email,
        tipo='recordatorio_vacuna',
        plantilla='recordatorio_vacuna',
        contexto={'vacuna': vacuna, 'propietario': propietario, 'paciente': vacuna.paciente},
        asunto=ASUNTOS['recordatorio_vacuna'].format(paciente=vacuna.paciente.nombre),
        vacuna=vacuna,
    )


def enviar_correo_prueba(destinatario):
    return enviar_correo(
        destinatario=destinatario, tipo='prueba', plantilla='prueba',
        contexto={'fecha': timezone.localtime()}, asunto=ASUNTOS['prueba'],
    )


# ---------------------------------------------------------------------------
# Recordatorios automáticos (RF-16) — usados por el comando programado
# ---------------------------------------------------------------------------
def enviar_recordatorios(fecha_referencia=None):
    """
    Envía:
      * Recordatorios de citas pendientes o confirmadas que ocurren dentro de
        N días (por defecto mañana).
      * Recordatorios de vacunas cuya próxima dosis vence dentro de N días.
    No repite un recordatorio que ya se envió con éxito.
    Devuelve un diccionario con el resumen.
    """
    from citas.models import Cita
    from pacientes.models import Vacuna

    hoy = fecha_referencia or timezone.localdate()
    config = ConfiguracionCorreo.obtener()
    resumen = {'citas_enviadas': 0, 'citas_error': 0, 'vacunas_enviadas': 0, 'vacunas_error': 0}

    limite_citas = hoy + timedelta(days=config.dias_recordatorio_cita)
    ya_recordadas = Notificacion.objects.filter(
        tipo='recordatorio_cita', estado='enviado', cita__isnull=False,
    ).values_list('cita_id', flat=True)
    citas = (
        Cita.objects
        .filter(fecha_cita__gt=hoy, fecha_cita__lte=limite_citas,
                estado__in=[Cita.PENDIENTE, Cita.CONFIRMADA])
        .exclude(pk__in=ya_recordadas)
        .select_related('paciente__propietario', 'veterinario')
    )
    for cita in citas:
        if enviar_correo_cita(cita, 'recordatorio_cita'):
            resumen['citas_enviadas'] += 1
        else:
            resumen['citas_error'] += 1

    limite_vacunas = hoy + timedelta(days=config.dias_recordatorio_vacuna)
    ya_vacunas = Notificacion.objects.filter(
        tipo='recordatorio_vacuna', estado='enviado', vacuna__isnull=False,
    ).values_list('vacuna_id', flat=True)
    vacunas = (
        Vacuna.objects
        .filter(fecha_proxima__gte=hoy, fecha_proxima__lte=limite_vacunas)
        .exclude(pk__in=ya_vacunas)
        .select_related('paciente__propietario')
    )
    for vacuna in vacunas:
        if enviar_correo_vacuna(vacuna):
            resumen['vacunas_enviadas'] += 1
        else:
            resumen['vacunas_error'] += 1

    return resumen
