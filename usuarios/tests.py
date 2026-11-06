"""Pruebas del módulo de usuarios y control de acceso (CP-01, CP-02, CP-03, CP-15)."""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class AutenticacionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin1', password='ClaveSegura123')
        self.admin.groups.add(Group.objects.get(name='Administrador'))
        self.recep = User.objects.create_user('recep1', password='ClaveSegura123')
        self.recep.groups.add(Group.objects.get(name='Recepcionista'))

    def test_roles_creados_por_migracion(self):
        nombres = set(Group.objects.values_list('name', flat=True))
        self.assertTrue({'Administrador', 'Veterinario', 'Recepcionista'} <= nombres)

    def test_login_valido_redirige_al_panel(self):
        r = self.client.post(reverse('login'), {'username': 'admin1', 'password': 'ClaveSegura123'})
        self.assertRedirects(r, reverse('dashboard'))  # CP-01

    def test_login_invalido_muestra_error(self):
        r = self.client.post(reverse('login'), {'username': 'admin1', 'password': 'incorrecta'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Usuario o contraseña incorrectos')  # CP-02

    def test_pagina_sin_sesion_redirige_a_login(self):
        r = self.client.get(reverse('lista_pacientes'))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r.url)  # CP-15

    def test_recepcionista_no_accede_a_usuarios(self):
        self.client.login(username='recep1', password='ClaveSegura123')
        self.assertEqual(self.client.get(reverse('lista_usuarios')).status_code, 403)  # CP-03

    def test_admin_crea_usuario_con_rol(self):
        self.client.login(username='admin1', password='ClaveSegura123')
        r = self.client.post(reverse('crear_usuario'), {
            'username': 'vet1', 'first_name': 'Laura', 'last_name': 'García', 'email': 'l@g.com',
            'is_active': 'on', 'rol': 'Veterinario', 'crear_veterinario': 'on',
            'password1': 'OtraClave#2026', 'password2': 'OtraClave#2026',
        })
        self.assertEqual(r.status_code, 302)
        nuevo = User.objects.get(username='vet1')
        self.assertTrue(nuevo.groups.filter(name='Veterinario').exists())
        self.assertTrue(hasattr(nuevo, 'veterinario'))
        self.assertTrue(nuevo.password.startswith('pbkdf2_sha256$'))  # RF-04

    def test_admin_desactiva_usuario(self):
        self.client.login(username='admin1', password='ClaveSegura123')
        self.client.post(reverse('cambiar_estado_usuario', args=[self.recep.pk]))
        self.recep.refresh_from_db()
        self.assertFalse(self.recep.is_active)
