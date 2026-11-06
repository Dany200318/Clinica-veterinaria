"""
Migración de datos históricos (sección 6.1.8).

Carga propietarios y pacientes desde archivos CSV (guardados desde Excel con
«CSV UTF-8»). Usa las mismas validaciones de los formularios del sistema y,
si hay errores, no guarda nada y muestra la fila y el motivo.

Plantillas: database/plantillas_importacion/propietarios.csv y pacientes.csv

Uso:
    python manage.py importar_datos_csv --propietarios ruta/propietarios.csv
    python manage.py importar_datos_csv --pacientes ruta/pacientes.csv
    python manage.py importar_datos_csv --propietarios p.csv --pacientes m.csv --probar
"""
import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pacientes.forms import PacienteForm, PropietarioForm
from pacientes.models import Propietario


def leer_csv(ruta):
    try:
        with open(ruta, encoding='utf-8-sig', newline='') as archivo:
            muestra = archivo.read(2048)
            archivo.seek(0)
            dialecto = csv.Sniffer().sniff(muestra, delimiters=',;')
            return list(csv.DictReader(archivo, dialect=dialecto))
    except FileNotFoundError as exc:
        raise CommandError(f'No se encontró el archivo: {ruta}') from exc


def convertir_fecha(valor):
    valor = (valor or '').strip()
    for formato in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue
    return valor


class Command(BaseCommand):
    help = 'Importa propietarios y pacientes desde archivos CSV (migración de datos históricos).'

    def add_arguments(self, parser):
        parser.add_argument('--propietarios', help='Ruta del CSV de propietarios.')
        parser.add_argument('--pacientes', help='Ruta del CSV de pacientes.')
        parser.add_argument('--probar', action='store_true', help='Valida sin guardar.')

    def handle(self, *args, **op):
        if not op['propietarios'] and not op['pacientes']:
            raise CommandError('Indique --propietarios y/o --pacientes.')
        errores = []
        creados = {'propietarios': 0, 'pacientes': 0}

        with transaction.atomic():
            if op['propietarios']:
                for n, fila in enumerate(leer_csv(op['propietarios']), start=2):
                    datos = {k.strip().lower(): (v or '').strip() for k, v in fila.items() if k}
                    form = PropietarioForm(datos)
                    if form.is_valid():
                        form.save()
                        creados['propietarios'] += 1
                    else:
                        errores.append(f'propietarios.csv fila {n}: {form.errors.as_text()}')

            if op['pacientes']:
                for n, fila in enumerate(leer_csv(op['pacientes']), start=2):
                    datos = {k.strip().lower(): (v or '').strip() for k, v in fila.items() if k}
                    correo = datos.pop('email_propietario', '').lower()
                    propietario = Propietario.objects.filter(email__iexact=correo).first()
                    if not propietario:
                        errores.append(f'pacientes.csv fila {n}: no existe un propietario con el correo «{correo}».')
                        continue
                    datos['propietario'] = propietario.pk
                    datos['fecha_nacimiento'] = convertir_fecha(datos.get('fecha_nacimiento'))
                    datos['peso'] = datos.get('peso', '').replace(',', '.')
                    if datos.get('esterilizado', '').lower() in ('si', 'sí', 's', '1', 'true', 'x'):
                        datos['esterilizado'] = 'on'
                    else:
                        datos.pop('esterilizado', None)
                    form = PacienteForm(datos)
                    if form.is_valid():
                        form.save()
                        creados['pacientes'] += 1
                    else:
                        errores.append(f'pacientes.csv fila {n}: {form.errors.as_text()}')

            if errores:
                for e in errores:
                    self.stdout.write(self.style.ERROR(e))
                transaction.set_rollback(True)
                raise CommandError(f'Se encontraron {len(errores)} errores. No se guardó ningún registro.')

            if op['probar']:
                transaction.set_rollback(True)
                self.stdout.write(self.style.WARNING(
                    f"Validación correcta (modo prueba, nada guardado): {creados['propietarios']} propietarios, "
                    f"{creados['pacientes']} pacientes."))
                return

        self.stdout.write(self.style.SUCCESS(
            f"Importación completada: {creados['propietarios']} propietarios y {creados['pacientes']} pacientes."))
