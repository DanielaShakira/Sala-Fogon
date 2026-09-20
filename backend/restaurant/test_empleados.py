"""Employee management and initial administrator checks."""

import base64
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Cuenta, Mesa, Sesion, Usuario


def autenticar(cliente, username, password="ClavePersonal2026!"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    cliente.credentials(HTTP_AUTHORIZATION=f"Basic {token}")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class EmpleadosTests(TestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        self.client = APIClient()
        self.admin_acceso = get_user_model().objects.create_user(
            "admin_restaurante", password="ClavePersonal2026!"
        )
        self.admin = Usuario.objects.create(
            cuenta_acceso=self.admin_acceso, nombre="Administradora", rol=Usuario.Rol.ADMIN
        )
        self.mesero_acceso = get_user_model().objects.create_user(
            "mesero_existente", password="ClavePersonal2026!"
        )
        self.mesero = Usuario.objects.create(
            cuenta_acceso=self.mesero_acceso, nombre="Mesero", rol=Usuario.Rol.MESERO
        )
        autenticar(self.client, "admin_restaurante")

    def crear(self, **cambios):
        datos = {
            "username": "cocinero_nuevo", "nombre": "Cocinero Nuevo",
            "password": "ClaveNueva2026!", "rol": "COCINERO",
        }
        datos.update(cambios)
        return self.client.post("/api/empleados/", datos, format="json")

    def test_admin_creates_account_and_profile_without_django_privileges(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, 201)
        self.assertNotIn("password", respuesta.data)
        self.assertEqual(respuesta.data["rol"], "COCINERO")
        acceso = get_user_model().objects.get(username="cocinero_nuevo")
        self.assertTrue(acceso.check_password("ClaveNueva2026!"))
        self.assertNotEqual(acceso.password, "ClaveNueva2026!")
        self.assertFalse(acceso.is_staff)
        self.assertFalse(acceso.is_superuser)
        self.assertEqual(acceso.usuario_restaurante.id, respuesta.data["id"])
        autenticar(self.client, "cocinero_nuevo", "ClaveNueva2026!")
        self.assertEqual(self.client.get("/api/me/").data["rol"], "COCINERO")

    def test_list_contains_only_employees_and_no_credentials(self):
        respuesta = self.client.get("/api/empleados/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila["username"] for fila in respuesta.data], ["mesero_existente"])
        self.assertEqual(set(respuesta.data[0]), {"id", "username", "nombre", "rol", "activo"})

    def test_cannot_create_admin_or_set_privilege_fields(self):
        for cambios in ({"rol": "ADMIN"}, {"is_staff": True}, {"is_superuser": True}, {"activo": False}):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.crear(**cambios).status_code, 400)
        self.assertFalse(get_user_model().objects.filter(username="cocinero_nuevo").exists())

    def test_duplicate_username_and_weak_password_are_rejected(self):
        self.assertEqual(self.crear(username="mesero_existente").status_code, 400)
        self.assertEqual(self.crear(password="123").status_code, 400)
        self.assertEqual(Usuario.objects.count(), 2)

    def test_profile_failure_rolls_back_access_account(self):
        with patch("restaurant.personal.Usuario.objects.create", side_effect=RuntimeError("fallo simulado")):
            with self.assertRaisesMessage(RuntimeError, "fallo simulado"):
                self.crear()
        self.assertFalse(get_user_model().objects.filter(username="cocinero_nuevo").exists())

    def test_activate_and_deactivate_employee_controls_basic_login(self):
        ruta = f"/api/empleados/{self.mesero.id}/"
        self.assertEqual(self.client.patch(ruta, {"activo": False}, format="json").status_code, 200)
        self.mesero_acceso.refresh_from_db()
        self.assertFalse(self.mesero_acceso.is_active)
        autenticar(self.client, "mesero_existente")
        self.assertEqual(self.client.get("/api/me/").status_code, 401)
        autenticar(self.client, "admin_restaurante")
        self.assertEqual(self.client.patch(ruta, {"activo": True}, format="json").status_code, 200)
        self.mesero_acceso.refresh_from_db()
        self.assertTrue(self.mesero_acceso.is_active)

    def test_waiter_with_open_session_cannot_be_deactivated(self):
        mesa = Mesa.objects.create(numero=808)
        sesion = Sesion.objects.create(mesa=mesa, mesero=self.mesero)
        Cuenta.objects.create(sesion=sesion)
        ruta = f"/api/empleados/{self.mesero.id}/"
        respuesta = self.client.patch(ruta, {"activo": False}, format="json")
        self.assertEqual(respuesta.status_code, 409)
        self.mesero_acceso.refresh_from_db()
        self.assertTrue(self.mesero_acceso.is_active)
        sesion.fecha_hora_fin = timezone.now()
        sesion.save(update_fields=["fecha_hora_fin"])
        self.assertEqual(self.client.patch(ruta, {"activo": False}, format="json").status_code, 200)

    def test_only_active_restaurant_admin_can_manage_employees(self):
        autenticar(self.client, "mesero_existente")
        self.assertEqual(self.client.get("/api/empleados/").status_code, 403)
        self.assertEqual(self.crear().status_code, 403)
        self.assertEqual(self.client.patch(
            f"/api/empleados/{self.mesero.id}/", {"activo": False}, format="json"
        ).status_code, 403)
        tecnico = get_user_model().objects.create_superuser(
            "superusuario_sin_perfil", password="ClavePersonal2026!"
        )
        autenticar(self.client, tecnico.username)
        self.assertEqual(self.client.get("/api/empleados/").status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/empleados/").status_code, 401)
        self.admin_acceso.is_active = False
        self.admin_acceso.save(update_fields=["is_active"])
        autenticar(self.client, "admin_restaurante")
        self.assertEqual(self.client.get("/api/empleados/").status_code, 401)

    def test_cannot_modify_admin_or_unexpected_fields(self):
        self.assertEqual(self.client.patch(
            f"/api/empleados/{self.admin.id}/", {"activo": False}, format="json"
        ).status_code, 404)
        self.assertEqual(self.client.patch(
            f"/api/empleados/{self.mesero.id}/", {"activo": False, "rol": "ADMIN"}, format="json"
        ).status_code, 400)
        self.mesero_acceso.refresh_from_db()
        self.assertTrue(self.mesero_acceso.is_active)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AdministradorInicialTests(TestCase):
    def test_command_creates_initial_admin_without_superuser_privileges(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        with patch("builtins.input", side_effect=["admin_inicial", "Administradora"]), patch(
            "restaurant.management.commands.crear_administrador.getpass",
            side_effect=["ClavePersonal2026!", "ClavePersonal2026!"],
        ):
            call_command("crear_administrador", stdout=StringIO())
        cuenta = get_user_model().objects.get(username="admin_inicial")
        self.assertTrue(cuenta.check_password("ClavePersonal2026!"))
        self.assertFalse(cuenta.is_staff)
        self.assertFalse(cuenta.is_superuser)
        self.assertEqual(cuenta.usuario_restaurante.rol, Usuario.Rol.ADMIN)
        with self.assertRaises(CommandError):
            call_command("crear_administrador", stdout=StringIO())


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class DesactivacionConcurrenteTests(TransactionTestCase):
    def test_open_and_deactivate_cannot_leave_inactive_waiter_with_open_session(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        admin_cuenta = get_user_model().objects.create_user("admin_carrera", password="ClavePersonal2026!")
        Usuario.objects.create(cuenta_acceso=admin_cuenta, nombre="Admin", rol=Usuario.Rol.ADMIN)
        mesero_cuenta = get_user_model().objects.create_user("mesero_carrera", password="ClavePersonal2026!")
        mesero = Usuario.objects.create(cuenta_acceso=mesero_cuenta, nombre="Mesero", rol=Usuario.Rol.MESERO)
        mesa = Mesa.objects.create(numero=809)
        inicio = Barrier(3, timeout=10)

        def solicitar(username, ruta, datos, metodo):
            cliente = APIClient()
            autenticar(cliente, username)
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT current_database(), pg_backend_pid()")
                    base, proceso = cursor.fetchone()
                inicio.wait()
                respuesta = getattr(cliente, metodo)(ruta, datos, format="json")
                return base, proceso, respuesta.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            apertura = ejecutor.submit(solicitar, "mesero_carrera", "/api/sesiones/", {"mesa_id": mesa.id}, "post")
            desactivacion = ejecutor.submit(
                solicitar, "admin_carrera", f"/api/empleados/{mesero.id}/", {"activo": False}, "patch"
            )
            inicio.wait()
            resultados = [apertura.result(timeout=15), desactivacion.result(timeout=15)]

        self.assertEqual({base for base, _, _ in resultados}, {"test_sala_fogon"})
        self.assertEqual(len({proceso for _, proceso, _ in resultados}), 2)
        self.assertIn(resultados[0][2], (201, 401, 403))
        self.assertIn(resultados[1][2], (200, 409))
        mesero_cuenta.refresh_from_db()
        abiertas = Sesion.objects.filter(mesero=mesero, fecha_hora_fin__isnull=True)
        self.assertFalse(not mesero_cuenta.is_active and abiertas.exists())
        self.assertEqual(Cuenta.objects.count(), abiertas.count())
