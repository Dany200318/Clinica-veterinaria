"""Pruebas del módulo de propietarios y pacientes (CP-04, CP-05, CP-06)."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Paciente, Propietario


class PacientesTests(TestCase):
    def setUp(self):
        usuario = User.objects.create_user('recep', password='ClaveSegura123')
        usuario.groups.add(Group.objects.get(name='Recepcionista'))
        self.client.login(username='recep', password='ClaveSegura123')

    def crear_propietario(self):
        return Propietario.objects.create(nombre='Ana Ruiz', telefono='5555-0000', email='ana@ejemplo.com')

    def test_registrar_propietario(self):
        r = self.client.post(reverse('crear_propietario'), {
            'nombre': 'carlos  gómez', 'telefono': '4444-1111', 'email': 'Carlos@Ejemplo.com',
            'direccion': 'Zona 1', 'dpi': '1234567890123', 'zona': 'Amatitlán',
        })
        self.assertEqual(r.status_code, 302)
        p = Propietario.objects.get()
        self.assertEqual(p.nombre, 'Carlos Gómez')
        self.assertEqual(p.email, 'carlos@ejemplo.com')  # CP-04

    def test_dpi_invalido(self):
        r = self.client.post(reverse('crear_propietario'), {
            'nombre': 'X', 'telefono': '4444-1111', 'email': 'x@x.com', 'dpi': '123'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Propietario.objects.exists())

    def test_dpi_vacio_permite_varios(self):
        for i in range(2):
            Propietario.objects.create(nombre=f'P{i}', telefono='5555-0000', email=f'p{i}@x.com', dpi=None)
        self.assertEqual(Propietario.objects.count(), 2)

    def test_registrar_paciente_asociado(self):
        propietario = self.crear_propietario()
        r = self.client.post(reverse('crear_paciente'), {
            'propietario': propietario.pk, 'nombre': 'Bobby', 'especie': 'Perro', 'raza': 'Pug', 'sexo': 'M',
            'alergias': 'Penicilina',
        })
        self.assertEqual(r.status_code, 302)
        paciente = Paciente.objects.get()
        self.assertEqual(paciente.propietario, propietario)  # CP-05
        r = self.client.get(reverse('ficha_paciente', args=[paciente.pk]))
        self.assertContains(r, 'ALERGIAS CONOCIDAS')

    def test_buscar_paciente(self):
        propietario = self.crear_propietario()
        Paciente.objects.create(propietario=propietario, nombre='Pelusa', especie='Gato', raza='Persa', sexo='H')
        r = self.client.get(reverse('buscar'), {'q': 'pelu'})
        self.assertContains(r, 'Pelusa')  # CP-06

    def test_recepcionista_no_elimina(self):
        propietario = self.crear_propietario()
        r = self.client.post(reverse('eliminar_propietario', args=[propietario.pk]))
        self.assertEqual(r.status_code, 403)
