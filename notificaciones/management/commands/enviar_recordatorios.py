"""
Tarea programada de recordatorios (RF-16).

Uso:
    python manage.py enviar_recordatorios
    python manage.py enviar_recordatorios --fecha 2026-11-20   (simula otra fecha)

En Windows se programa con el Programador de tareas usando scripts/enviar_recordatorios.bat
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from notificaciones.servicios import enviar_recordatorios


class Command(BaseCommand):
    help = 'Envía por correo los recordatorios de citas próximas y vacunas por vencer.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha', help='Fecha de referencia AAAA-MM-DD (por defecto, hoy).')

    def handle(self, *args, **opciones):
        fecha = None
        if opciones.get('fecha'):
            try:
                fecha = date.fromisoformat(opciones['fecha'])
            except ValueError as exc:
                raise CommandError('Formato de fecha inválido. Use AAAA-MM-DD.') from exc

        self.stdout.write('Enviando recordatorios...')
        r = enviar_recordatorios(fecha)
        self.stdout.write(self.style.SUCCESS(
            f"Citas: {r['citas_enviadas']} enviados, {r['citas_error']} con error. "
            f"Vacunas: {r['vacunas_enviadas']} enviados, {r['vacunas_error']} con error."
        ))
        if r['citas_error'] or r['vacunas_error']:
            self.stdout.write(self.style.WARNING(
                'Revise el historial de notificaciones en el sistema para ver el detalle de los errores.'
            ))
