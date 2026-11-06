"""
Carga datos de prueba para demostrar el sistema (propietarios, pacientes,
veterinarios, citas y vacunas). Las fechas se calculan a partir de HOY para
que el panel principal siempre muestre información.

Uso:
    python manage.py cargar_datos_demo
    python manage.py cargar_datos_demo --usuarios     (crea también usuarios de prueba por rol)
    python manage.py cargar_datos_demo --borrar       (elimina antes los datos de prueba)
"""
from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from citas.models import Cita, Veterinario
from pacientes.models import Paciente, Propietario, Vacuna

PROPIETARIOS = [
    ('María Fernanda López García', '5512-3456', 'maria.lopez@ejemplo.com', '1234567890101', 'Zona 1, Amatitlán', 'Barrio El Calvario, 3a. calle 4-15'),
    ('José Antonio Pérez Ramírez', '4423-7788', 'jose.perez@ejemplo.com', '2345678901201', 'Zona 2, Amatitlán', 'Colonia San Antonio, lote 12'),
    ('Ana Lucía Hernández Ruiz', '3301-2299', 'ana.hernandez@ejemplo.com', '3456789012301', 'Villa Canales', '5a. avenida 2-30'),
    ('Carlos Eduardo Gómez Díaz', '5590-1122', 'carlos.gomez@ejemplo.com', None, 'Zona 4, Amatitlán', 'Residenciales Las Flores, casa 8'),
    ('Sofía Alejandra Castillo Mejía', '4788-6655', 'sofia.castillo@ejemplo.com', '4567890123401', 'Palín, Escuintla', 'Calle principal 10-20'),
]

# (índice propietario, nombre, especie, raza, sexo, color, años, peso (lb), microchip, esterilizado, alergias)
PACIENTES = [
    (0, 'Max', 'Perro', 'Labrador Retriever', 'M', 'Dorado', 4, '62.83', '985112003456781', True, ''),
    (0, 'Luna', 'Gato', 'Siamés', 'H', 'Crema', 2, '9.26', '', True, 'Penicilina'),
    (1, 'Rocky', 'Perro', 'Pastor Alemán', 'M', 'Negro y fuego', 6, '74.96', '985112003456782', False, ''),
    (2, 'Mía', 'Gato', 'Doméstico de pelo corto', 'H', 'Atigrado', 1, '6.83', '', False, ''),
    (2, 'Toby', 'Perro', 'Beagle', 'M', 'Tricolor', 3, '28.22', '', True, 'Pollo (alergia alimentaria)'),
    (3, 'Canela', 'Perro', 'Mestizo', 'H', 'Café', 5, '33.73', '', True, ''),
    (4, 'Simba', 'Gato', 'Persa', 'M', 'Naranja', 7, '12.35', '985112003456783', True, 'Sulfas'),
]


class Command(BaseCommand):
    help = 'Carga datos de prueba para demostrar el sistema.'

    def add_arguments(self, parser):
        parser.add_argument('--usuarios', action='store_true', help='Crear usuarios de prueba por rol.')
        parser.add_argument('--borrar', action='store_true', help='Eliminar antes los datos de prueba.')

    @transaction.atomic
    def handle(self, *args, **opciones):
        hoy = timezone.localdate()

        if opciones['borrar']:
            correos = [p[2] for p in PROPIETARIOS]
            Cita.objects.filter(paciente__propietario__email__in=correos).delete()
            Paciente.objects.filter(propietario__email__in=correos).delete()
            Propietario.objects.filter(email__in=correos).delete()
            self.stdout.write('Datos de prueba anteriores eliminados.')

        if Propietario.objects.filter(email=PROPIETARIOS[0][2]).exists():
            self.stdout.write(self.style.WARNING('Los datos de prueba ya existen. Use --borrar para recargarlos.'))
            return

        # Veterinarios
        vet1, _ = Veterinario.objects.get_or_create(nombre_completo='Dra. Ana Lucía Morales')
        vet2, _ = Veterinario.objects.get_or_create(nombre_completo='Dr. Luis Fernando Ortiz')

        # Usuarios de prueba (opcional)
        if opciones['usuarios']:
            usuarios = [
                ('veterinaria', 'Ana Lucía', 'Morales', 'Veterinario', vet1),
                ('recepcion', 'Karla', 'Méndez', 'Recepcionista', None),
            ]
            for username, nombre, apellido, rol, vet in usuarios:
                usuario, creado = User.objects.get_or_create(
                    username=username, defaults={'first_name': nombre, 'last_name': apellido})
                if creado:
                    usuario.set_password('Clinica2026!')
                    usuario.save()
                usuario.groups.set([Group.objects.get_or_create(name=rol)[0]])
                if vet and not vet.usuario_id:
                    vet.usuario = usuario
                    vet.save()
            self.stdout.write(self.style.SUCCESS(
                'Usuarios de prueba: "veterinaria" y "recepcion" (contraseña: Clinica2026!). '
                'Cámbielas antes de usar el sistema en producción.'))

        # Propietarios y pacientes
        propietarios = [
            Propietario.objects.create(nombre=n, telefono=t, email=e, dpi=d, zona=z, direccion=di)
            for n, t, e, d, z, di in PROPIETARIOS
        ]
        pacientes = []
        for i, nombre, especie, raza, sexo, color, anios, peso, chip, est, alergias in PACIENTES:
            pacientes.append(Paciente.objects.create(
                propietario=propietarios[i], nombre=nombre, especie=especie, raza=raza, sexo=sexo,
                color=color, fecha_nacimiento=hoy - timedelta(days=365 * anios + 40),
                peso=Decimal(peso), microchip=chip, esterilizado=est, alergias=alergias,
            ))
        max_, luna, rocky, mia, toby, canela, simba = pacientes

        # Citas: (paciente, vet, días desde hoy, hora inicio, hora fin, motivo, tipo, estado)
        citas = [
            (rocky, vet1, -150, time(9, 0), time(9, 30), 'Control de cadera', 'control', 'completada'),
            (max_, vet1, -120, time(10, 0), time(10, 30), 'Vacuna antirrábica anual', 'vacunacion', 'completada'),
            (luna, vet2, -95, time(11, 0), time(11, 30), 'Revisión general', 'consulta', 'completada'),
            (toby, vet2, -70, time(15, 0), time(15, 30), 'Desparasitación interna', 'desparasitacion', 'completada'),
            (canela, vet1, -60, time(8, 30), time(9, 30), 'Esterilización', 'cirugia', 'completada'),
            (mia, vet2, -45, time(14, 0), time(14, 30), 'Primera vacuna triple felina', 'vacunacion', 'completada'),
            (simba, vet1, -30, time(16, 0), time(16, 30), 'Dermatitis', 'consulta', 'cancelada'),
            (rocky, vet2, -20, time(9, 0), time(9, 30), 'Vómitos frecuentes', 'consulta', 'completada'),
            (max_, vet1, -7, time(10, 0), time(10, 30), 'Cojera pata trasera', 'consulta', 'completada'),
            (toby, vet1, -3, time(11, 0), time(11, 30), 'Control de alergia alimentaria', 'control', 'pendiente'),
            (luna, vet1, 0, time(9, 0), time(9, 30), 'Control post vacuna', 'control', 'confirmada'),
            (rocky, vet2, 0, time(10, 0), time(10, 45), 'Limpieza dental', 'consulta', 'pendiente'),
            (mia, vet1, 0, time(15, 0), time(15, 30), 'Refuerzo triple felina', 'vacunacion', 'completada'),
            (canela, vet2, 1, time(8, 30), time(9, 0), 'Retiro de puntos', 'control', 'confirmada'),
            (simba, vet1, 2, time(11, 0), time(11, 30), 'Revisión de piel', 'consulta', 'pendiente'),
            (max_, vet2, 4, time(14, 0), time(14, 30), 'Desparasitación', 'desparasitacion', 'pendiente'),
            (toby, vet1, 6, time(16, 0), time(16, 30), 'Vacuna antirrábica', 'vacunacion', 'pendiente'),
            (luna, vet2, 12, time(9, 30), time(10, 0), 'Chequeo general', 'consulta', 'pendiente'),
        ]
        for paciente, vet, dias, hi, hf, motivo, tipo, estado in citas:
            cita = Cita(paciente=paciente, veterinario=vet, fecha_cita=hoy + timedelta(days=dias),
                        hora_inicio=hi, hora_fin=hf, motivo=motivo, tipo_cita=tipo, estado=estado)
            cita.save()  # Se omite full_clean() para poder registrar citas pasadas de ejemplo

        # Vacunas: (paciente, nombre, días desde hoy aplicada, días hasta próxima)
        vacunas = [
            (max_, 'Rabia', -120, 245),
            (max_, 'Parvovirus + Moquillo (Quíntuple)', -200, 5),
            (luna, 'Triple felina', -95, 270),
            (rocky, 'Rabia', -380, -15),
            (mia, 'Triple felina', -45, 3),
            (toby, 'Desparasitación', -70, 20),
            (canela, 'Rabia', -300, 65),
            (simba, 'Leucemia felina', -340, 25),
        ]
        for paciente, nombre, aplicada, proxima in vacunas:
            Vacuna.objects.create(paciente=paciente, nombre=nombre,
                                  fecha_aplicacion=hoy + timedelta(days=aplicada),
                                  fecha_proxima=hoy + timedelta(days=proxima))

        self.stdout.write(self.style.SUCCESS(
            f'Datos de prueba cargados: {len(propietarios)} propietarios, {len(pacientes)} pacientes, '
            f'2 veterinarios, {len(citas)} citas y {len(vacunas)} vacunas.'))
