"""HTTP and transaction checks for the first waiter workflow."""

import base64
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .models import (
    ComposicionItemPedido,
    ComposicionPlato,
    Cuenta,
    Ingrediente,
    ItemPedido,
    Mesa,
    Pedido,
    Plato,
    Sesion,
    Usuario,
)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class FlujoMeseroTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.acceso = get_user_model().objects.create_user("mesero_api", password="clave-local-prueba")
        self.mesero = Usuario.objects.create(
            cuenta_acceso=self.acceso, nombre="Mesero API", rol=Usuario.Rol.MESERO
        )
        self.mesa = Mesa.objects.create(numero=10)
        self.ingrediente = Ingrediente.objects.create(
            nombre="Ingrediente compartido", cantidad_disponible=Decimal("5.000")
        )
        self.plato_a = Plato.objects.create(
            nombre="Plato A", precio=Decimal("12000.50")
        )
        self.plato_b = Plato.objects.create(
            nombre="Plato B", precio=Decimal("9000.00")
        )
        self.receta_a = ComposicionPlato.objects.create(
            plato=self.plato_a, ingrediente=self.ingrediente,
            cantidad_requerida=Decimal("1.250"),
        )
        ComposicionPlato.objects.create(
            plato=self.plato_b, ingrediente=self.ingrediente,
            cantidad_requerida=Decimal("0.750"),
        )
        self.autenticar()

    def autenticar(self, usuario="mesero_api", clave="clave-local-prueba"):
        token = base64.b64encode(f"{usuario}:{clave}".encode()).decode()
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {token}")

    def abrir(self):
        return self.client.post("/api/sesiones/", {"mesa_id": self.mesa.id}, format="json")

    def enviar(self, sesion_id, items, observaciones=""):
        return self.client.post(
            "/api/pedidos/",
            {"sesion_id": sesion_id, "items": items, "observaciones": observaciones},
            format="json",
        )

    def test_runner_uses_only_dedicated_test_database(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")

    def test_open_creates_session_and_account_for_authenticated_waiter(self):
        response = self.abrir()
        self.assertEqual(response.status_code, 201)
        sesion = Sesion.objects.get(pk=response.data["id"])
        self.assertEqual(sesion.mesero, self.mesero)
        self.assertEqual(sesion.mesa, self.mesa)
        self.assertEqual(sesion.cuenta.id, response.data["cuenta_id"])
        self.assertEqual(Cuenta.objects.count(), 1)

    def test_claimed_waiter_id_cannot_replace_authenticated_identity(self):
        otro_acceso = get_user_model().objects.create_user("otro", password="clave")
        otro = Usuario.objects.create(cuenta_acceso=otro_acceso, nombre="Otro", rol=Usuario.Rol.MESERO)
        response = self.client.post(
            "/api/sesiones/", {"mesa_id": self.mesa.id, "mesero_id": otro.id}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Sesion.objects.get().mesero, self.mesero)

    def test_second_active_session_is_rejected(self):
        self.assertEqual(self.abrir().status_code, 201)
        self.assertEqual(self.abrir().status_code, 409)
        self.assertEqual(Sesion.objects.count(), 1)
        self.assertEqual(Cuenta.objects.count(), 1)

    def test_account_failure_rolls_back_session(self):
        with patch("restaurant.services.Cuenta.objects.create", side_effect=RuntimeError("fallo simulado")):
            with self.assertRaisesMessage(RuntimeError, "fallo simulado"):
                self.abrir()
        self.assertFalse(Sesion.objects.exists())
        self.assertFalse(Cuenta.objects.exists())

    def test_missing_table_is_rejected(self):
        response = self.client.post("/api/sesiones/", {"mesa_id": 99999}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Sesion.objects.exists())

    def test_basic_authentication_and_role_are_required(self):
        self.client.credentials()
        self.assertEqual(self.abrir().status_code, 401)
        cocinero_acceso = get_user_model().objects.create_user("cocinero", password="clave")
        Usuario.objects.create(cuenta_acceso=cocinero_acceso, nombre="Cocinero", rol=Usuario.Rol.COCINERO)
        self.autenticar("cocinero", "clave")
        self.assertEqual(self.abrir().status_code, 403)
        self.acceso.is_active = False
        self.acceso.save(update_fields=["is_active"])
        self.autenticar()
        self.assertEqual(self.abrir().status_code, 401)
        self.assertFalse(Sesion.objects.exists())

    def test_catalogue_derives_availability(self):
        self.plato_b.activo = False
        self.plato_b.save(update_fields=["activo"])
        response = self.client.get("/api/platos/")
        self.assertEqual(response.status_code, 200)
        por_id = {plato["id"]: plato for plato in response.data}
        self.assertTrue(por_id[self.plato_a.id]["disponible"])
        self.assertFalse(por_id[self.plato_b.id]["disponible"])
        self.ingrediente.cantidad_disponible = Decimal("1.000")
        self.ingrediente.save(update_fields=["cantidad_disponible"])
        response = self.client.get("/api/platos/")
        self.assertFalse(next(p for p in response.data if p["id"] == self.plato_a.id)["disponible"])
        self.ingrediente.activo = False
        self.ingrediente.save(update_fields=["activo"])
        self.assertFalse(next(p for p in self.client.get("/api/platos/").data if p["id"] == self.plato_a.id)["disponible"])

    def test_empty_and_non_integer_or_non_positive_units_are_rejected(self):
        sesion_id = self.abrir().data["id"]
        self.assertEqual(self.enviar(sesion_id, []).status_code, 400)
        for cantidad in (0, -1, 1.5, "2", True):
            with self.subTest(cantidad=cantidad):
                response = self.enviar(sesion_id, [{"plato_id": self.plato_a.id, "cantidad": cantidad}])
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Pedido.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))

    def test_insufficient_combined_stock_rejects_whole_order(self):
        sesion_id = self.abrir().data["id"]
        response = self.enviar(sesion_id, [
            {"plato_id": self.plato_a.id, "cantidad": 3},
            {"plato_id": self.plato_b.id, "cantidad": 2},
        ])  # 3*1.250 + 2*0.750 = 5.250
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(ItemPedido.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))

    def test_send_uses_current_recipe_and_ingredient_activity(self):
        sesion_id = self.abrir().data["id"]
        self.receta_a.cantidad_requerida = Decimal("6.000")
        self.receta_a.save(update_fields=["cantidad_requerida"])
        linea = [{"plato_id": self.plato_a.id, "cantidad": 1}]
        self.assertEqual(self.enviar(sesion_id, linea).status_code, 409)
        self.receta_a.cantidad_requerida = Decimal("1.250")
        self.receta_a.save(update_fields=["cantidad_requerida"])
        self.ingrediente.activo = False
        self.ingrediente.save(update_fields=["activo"])
        self.assertEqual(self.enviar(sesion_id, linea).status_code, 409)
        self.assertFalse(Pedido.objects.exists())

    def test_shared_ingredient_is_deducted_once_for_all_units(self):
        sesion_id = self.abrir().data["id"]
        response = self.enviar(sesion_id, [
            {"plato_id": self.plato_a.id, "cantidad": 2},
            {"plato_id": self.plato_b.id, "cantidad": 1},
        ], "Sin sal")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["items"]), 3)
        self.assertEqual(Pedido.objects.get().observaciones, "Sin sal")
        self.assertEqual(ItemPedido.objects.count(), 3)
        self.assertEqual(ComposicionItemPedido.objects.count(), 3)
        self.assertTrue(all(item.estado == ItemPedido.Estado.EN_COLA for item in ItemPedido.objects.all()))
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("1.750"))

    def test_price_and_recipe_snapshots_survive_catalogue_edits(self):
        sesion_id = self.abrir().data["id"]
        response = self.enviar(sesion_id, [{"plato_id": self.plato_a.id, "cantidad": 1}])
        self.assertEqual(response.status_code, 201)
        self.plato_a.precio = Decimal("20000.00")
        self.plato_a.save(update_fields=["precio"])
        self.receta_a.cantidad_requerida = Decimal("2.000")
        self.receta_a.save(update_fields=["cantidad_requerida"])
        item = ItemPedido.objects.get()
        self.assertEqual(item.precio_unitario, Decimal("12000.50"))
        self.assertEqual(item.composicion.get().cantidad, Decimal("1.250"))

    def test_closed_or_foreign_session_cannot_receive_order(self):
        sesion_id = self.abrir().data["id"]
        otro_acceso = get_user_model().objects.create_user("otro", password="clave")
        Usuario.objects.create(cuenta_acceso=otro_acceso, nombre="Otro", rol=Usuario.Rol.MESERO)
        self.autenticar("otro", "clave")
        items = [{"plato_id": self.plato_a.id, "cantidad": 1}]
        self.assertEqual(self.enviar(sesion_id, items).status_code, 403)
        self.autenticar()
        sesion = Sesion.objects.get(pk=sesion_id)
        sesion.fecha_hora_fin = timezone.now()
        sesion.save(update_fields=["fecha_hora_fin"])
        self.assertEqual(self.enviar(sesion_id, items).status_code, 409)
        self.assertFalse(Pedido.objects.exists())

    def test_failure_during_item_snapshot_rolls_back_everything(self):
        sesion_id = self.abrir().data["id"]
        with patch("restaurant.services.ComposicionItemPedido.objects.create", side_effect=RuntimeError("fallo simulado")):
            with self.assertRaisesMessage(RuntimeError, "fallo simulado"):
                self.enviar(sesion_id, [{"plato_id": self.plato_a.id, "cantidad": 1}])
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(ItemPedido.objects.exists())
        self.assertFalse(ComposicionItemPedido.objects.exists())
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))

    def test_failure_after_first_stock_update_rolls_back_debit_and_order(self):
        segundo = Ingrediente.objects.create(nombre="Segundo", cantidad_disponible=Decimal("4.000"))
        ComposicionPlato.objects.create(
            plato=self.plato_a, ingrediente=segundo, cantidad_requerida=Decimal("1.000")
        )
        sesion_id = self.abrir().data["id"]
        guardar_original = Ingrediente.save
        llamadas = 0

        def guardar_con_fallo(instancia, *args, **kwargs):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise RuntimeError("fallo después del primer descuento")
            return guardar_original(instancia, *args, **kwargs)

        with patch.object(Ingrediente, "save", guardar_con_fallo):
            with self.assertRaisesMessage(RuntimeError, "fallo después del primer descuento"):
                self.enviar(sesion_id, [{"plato_id": self.plato_a.id, "cantidad": 1}])
        self.assertFalse(Pedido.objects.exists())
        self.assertFalse(ItemPedido.objects.exists())
        self.assertFalse(ComposicionItemPedido.objects.exists())
        self.ingrediente.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))
        self.assertEqual(segundo.cantidad_disponible, Decimal("4.000"))
