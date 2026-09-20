"""Kitchen, cancellation and real PostgreSQL concurrency checks."""

import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
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


def autenticar(cliente, usuario, clave="clave-prueba"):
    token = base64.b64encode(f"{usuario}:{clave}".encode()).decode()
    cliente.credentials(HTTP_AUTHORIZATION=f"Basic {token}")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CocinaYCancelacionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.mesero = self.crear_usuario("mesero_cocina", Usuario.Rol.MESERO)
        self.cocinero = self.crear_usuario("cocinero_api", Usuario.Rol.COCINERO)
        self.otro_mesero = self.crear_usuario("otro_mesero", Usuario.Rol.MESERO)
        self.mesa = Mesa.objects.create(numero=31)
        self.sesion = Sesion.objects.create(mesa=self.mesa, mesero=self.mesero)
        Cuenta.objects.create(sesion=self.sesion)
        self.ingrediente = Ingrediente.objects.create(
            nombre="Ingrediente histórico", cantidad_disponible=Decimal("10.000")
        )
        self.plato = Plato.objects.create(
            nombre="Plato de cocina", precio=Decimal("10000.00")
        )
        self.receta = ComposicionPlato.objects.create(
            plato=self.plato, ingrediente=self.ingrediente, cantidad_requerida=Decimal("1.250")
        )
        autenticar(self.client, "mesero_cocina")

    def crear_usuario(self, nombre, rol):
        acceso = get_user_model().objects.create_user(nombre, password="clave-prueba")
        return Usuario.objects.create(cuenta_acceso=acceso, nombre=nombre, rol=rol)

    def enviar(self, cantidad=1):
        response = self.client.post(
            "/api/pedidos/",
            {"sesion_id": self.sesion.id, "items": [{"plato_id": self.plato.id, "cantidad": cantidad}]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        return Pedido.objects.get(pk=response.data["id"])

    def test_queue_orders_by_date_then_id_and_groups_only_pending_items(self):
        primero = self.enviar(4)
        segundo = self.enviar(1)
        tercero = self.enviar(1)
        sin_pendientes = self.enviar(1)
        ahora = timezone.now()
        Pedido.objects.filter(pk=primero.id).update(fecha_hora_creacion=ahora)
        Pedido.objects.filter(pk=segundo.id).update(fecha_hora_creacion=ahora)
        Pedido.objects.filter(pk=tercero.id).update(fecha_hora_creacion=ahora - timedelta(minutes=2))
        items_primero = list(primero.items.order_by("id"))
        items_primero[1].estado = ItemPedido.Estado.EN_PREPARACION
        items_primero[1].save(update_fields=["estado"])
        items_primero[2].estado = ItemPedido.Estado.LISTO
        items_primero[2].save(update_fields=["estado"])
        items_primero[3].estado = ItemPedido.Estado.CANCELADO
        items_primero[3].save(update_fields=["estado"])
        item_final = sin_pendientes.items.get()
        item_final.estado = ItemPedido.Estado.LISTO
        item_final.save(update_fields=["estado"])

        autenticar(self.client, "cocinero_api")
        response = self.client.get("/api/cocina/cola/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p["id"] for p in response.data], [tercero.id, primero.id, segundo.id])
        agrupado = response.data[1]
        self.assertEqual(agrupado["mesa_numero"], 31)
        self.assertEqual([i["id"] for i in agrupado["items"]], [items_primero[0].id, items_primero[1].id])
        self.assertEqual([i["estado"] for i in agrupado["items"]], ["EN_COLA", "EN_PREPARACION"])
        self.assertTrue(all(p["items"] for p in response.data))

    def test_waiter_sees_local_numbers_and_derived_states_while_kitchen_hides_finished_orders(self):
        primero = self.enviar()
        otra_mesa = Mesa.objects.create(numero=32)
        otra_sesion = Sesion.objects.create(mesa=otra_mesa, mesero=self.mesero)
        Cuenta.objects.create(sesion=otra_sesion)
        ajeno_a_la_sesion = self.client.post(
            "/api/pedidos/",
            {"sesion_id": otra_sesion.id, "items": [{"plato_id": self.plato.id, "cantidad": 1}]},
            format="json",
        )
        self.assertEqual(ajeno_a_la_sesion.status_code, 201)
        segundo = self.enviar()
        tercero = self.enviar(2)
        cuarto = self.enviar()
        quinto = self.enviar(2)

        ItemPedido.objects.filter(pedido=segundo).update(estado=ItemPedido.Estado.EN_PREPARACION)
        listo_tercero, cancelado_tercero = list(tercero.items.order_by("id"))
        listo_tercero.estado = ItemPedido.Estado.LISTO
        listo_tercero.save(update_fields=["estado"])
        self.assertEqual(self.client.post(f"/api/items/{cancelado_tercero.id}/cancelar/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/items/{cuarto.items.get().id}/cancelar/").status_code, 200)
        primero_quinto = quinto.items.order_by("id").first()
        primero_quinto.estado = ItemPedido.Estado.LISTO
        primero_quinto.save(update_fields=["estado"])

        respuesta_mesero = self.client.get(f"/api/sesiones/{self.sesion.id}/pedidos/")
        self.assertEqual(respuesta_mesero.status_code, 200)
        pedidos = respuesta_mesero.data
        self.assertEqual([p["id"] for p in pedidos], [primero.id, segundo.id, tercero.id, cuarto.id, quinto.id])
        self.assertGreater(segundo.id - primero.id, 1)  # Another session uses a global ID.
        self.assertEqual([p["numero_en_sesion"] for p in pedidos], [1, 2, 3, 4, 5])
        self.assertEqual(
            [p["estado_general"] for p in pedidos],
            ["EN_COLA", "EN_CURSO", "COMPLETO", "CANCELADO", "EN_CURSO"],
        )
        self.assertEqual(len(pedidos[2]["items"]), 2)  # Completed orders keep their item history.
        self.assertEqual(pedidos[3]["items"][0]["estado"], "CANCELADO")

        autenticar(self.client, "cocinero_api")
        respuesta_cocina = self.client.get("/api/cocina/cola/")
        self.assertEqual(respuesta_cocina.status_code, 200)
        self.assertEqual([p["id"] for p in respuesta_cocina.data if p["sesion_id"] == self.sesion.id],
                         [primero.id, segundo.id, quinto.id])
        self.assertEqual(
            [p["estado_general"] for p in respuesta_cocina.data if p["sesion_id"] == self.sesion.id],
            ["EN_COLA", "EN_CURSO", "EN_CURSO"],
        )

    def test_units_advance_independently_and_invalid_jumps_are_rejected(self):
        pedido = self.enviar(2)
        primero, segundo = list(pedido.items.order_by("id"))
        autenticar(self.client, "cocinero_api")
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/listo/").status_code, 409)
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/iniciar/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/iniciar/").status_code, 409)
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/listo/").status_code, 200)
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/listo/").status_code, 409)
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/iniciar/").status_code, 409)
        primero.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(primero.estado, ItemPedido.Estado.LISTO)
        self.assertEqual(segundo.estado, ItemPedido.Estado.EN_COLA)
        cola = self.client.get("/api/cocina/cola/").data
        self.assertEqual([i["id"] for i in cola[0]["items"]], [segundo.id])

    def test_cancellation_returns_historical_recipe_once_and_keeps_item(self):
        pedido = self.enviar(2)
        primero, segundo = list(pedido.items.order_by("id"))
        self.receta.cantidad_requerida = Decimal("4.000")
        self.receta.save(update_fields=["cantidad_requerida"])
        respuesta = self.client.post(f"/api/items/{primero.id}/cancelar/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["estado"], "CANCELADO")
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("8.750"))
        self.assertEqual(self.client.post(f"/api/items/{primero.id}/cancelar/").status_code, 409)
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("8.750"))
        self.assertEqual(ComposicionItemPedido.objects.get(item_pedido=primero).cantidad, Decimal("1.250"))
        self.assertEqual(ItemPedido.objects.count(), 2)
        segundo.refresh_from_db()
        self.assertEqual(segundo.estado, ItemPedido.Estado.EN_COLA)

    def test_cannot_cancel_after_preparation_starts_or_after_ready(self):
        pedido = self.enviar(1)
        item = pedido.items.get()
        autenticar(self.client, "cocinero_api")
        self.client.post(f"/api/items/{item.id}/iniciar/")
        autenticar(self.client, "mesero_cocina")
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 409)
        autenticar(self.client, "cocinero_api")
        self.client.post(f"/api/items/{item.id}/listo/")
        autenticar(self.client, "mesero_cocina")
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 409)
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("8.750"))

    def test_cancelled_item_cannot_reenter_preparation(self):
        item = self.enviar().items.get()
        self.client.post(f"/api/items/{item.id}/cancelar/")
        autenticar(self.client, "cocinero_api")
        self.assertEqual(self.client.post(f"/api/items/{item.id}/iniciar/").status_code, 409)
        self.assertEqual(self.client.post(f"/api/items/{item.id}/listo/").status_code, 409)
        self.assertEqual(self.client.get("/api/cocina/cola/").data, [])

    def test_permissions_and_ownership_are_checked_on_backend(self):
        item = self.enviar().items.get()
        self.assertEqual(self.client.get(f"/api/sesiones/{self.sesion.id}/pedidos/").status_code, 200)
        self.assertEqual(self.client.get("/api/cocina/cola/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/items/{item.id}/iniciar/").status_code, 403)
        autenticar(self.client, "otro_mesero")
        self.assertEqual(self.client.get(f"/api/sesiones/{self.sesion.id}/pedidos/").status_code, 403)
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 403)
        autenticar(self.client, "cocinero_api")
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 403)
        self.assertEqual(self.client.get("/api/me/").data["rol"], "COCINERO")
        self.client.credentials()
        self.assertEqual(self.client.get("/api/cocina/cola/").status_code, 401)
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 401)

    def test_failed_refund_rolls_back_stock_and_state(self):
        segundo = Ingrediente.objects.create(nombre="Segundo", cantidad_disponible=Decimal("5.000"))
        ComposicionPlato.objects.create(
            plato=self.plato, ingrediente=segundo, cantidad_requerida=Decimal("0.500")
        )
        item = self.enviar().items.get()
        guardar_original = Ingrediente.save
        llamadas = 0

        def guardar_con_fallo(instancia, *args, **kwargs):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise RuntimeError("fallo simulado al devolver")
            return guardar_original(instancia, *args, **kwargs)

        with patch.object(Ingrediente, "save", guardar_con_fallo):
            with self.assertRaisesMessage(RuntimeError, "fallo simulado al devolver"):
                self.client.post(f"/api/items/{item.id}/cancelar/")
        item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(item.estado, ItemPedido.Estado.EN_COLA)
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("8.750"))
        self.assertEqual(segundo.cantidad_disponible, Decimal("4.500"))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CarreraCancelacionPreparacionTests(TransactionTestCase):
    """Concurrent HTTP requests use separate PostgreSQL backend processes."""

    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        acceso_mesero = get_user_model().objects.create_user("mesero_carrera", password="clave-prueba")
        mesero = Usuario.objects.create(
            cuenta_acceso=acceso_mesero, nombre="Mesero", rol=Usuario.Rol.MESERO
        )
        acceso_cocinero = get_user_model().objects.create_user("cocinero_carrera", password="clave-prueba")
        Usuario.objects.create(
            cuenta_acceso=acceso_cocinero, nombre="Cocinero", rol=Usuario.Rol.COCINERO
        )
        mesa = Mesa.objects.create(numero=90)
        sesion = Sesion.objects.create(mesa=mesa, mesero=mesero)
        Cuenta.objects.create(sesion=sesion)
        pedido = Pedido.objects.create(sesion=sesion)
        plato = Plato.objects.create(nombre="Plato", precio=Decimal("1.00"))
        self.ingrediente = Ingrediente.objects.create(
            nombre="Ingrediente", cantidad_disponible=Decimal("3.750")
        )
        self.segundo = Ingrediente.objects.create(
            nombre="Segundo ingrediente", cantidad_disponible=Decimal("4.500")
        )
        self.item = ItemPedido.objects.create(pedido=pedido, plato=plato, precio_unitario=plato.precio)
        ComposicionItemPedido.objects.create(
            item_pedido=self.item, ingrediente=self.ingrediente, cantidad=Decimal("1.250")
        )
        ComposicionItemPedido.objects.create(
            item_pedido=self.item, ingrediente=self.segundo, cantidad=Decimal("0.500")
        )

    def correr_carrera(self, operaciones):
        inicio = Barrier(3, timeout=10)

        def solicitar(usuario, accion):
            cliente = APIClient()
            autenticar(cliente, usuario)
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT current_database(), pg_backend_pid()")
                    base, proceso = cursor.fetchone()
                inicio.wait()
                respuesta = cliente.post(f"/api/items/{self.item.id}/{accion}/")
                return base, proceso, respuesta.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            tareas = [ejecutor.submit(solicitar, usuario, accion) for usuario, accion in operaciones]
            inicio.wait()
            resultados = [tarea.result(timeout=15) for tarea in tareas]

        self.assertTrue(all(base == "test_sala_fogon" for base, _, _ in resultados))
        self.assertEqual(len({proceso for _, proceso, _ in resultados}), 2)
        return sorted(codigo for _, _, codigo in resultados)

    def test_only_one_competing_preparation_or_cancellation_wins(self):
        resultados = self.correr_carrera([
            ("cocinero_carrera", "iniciar"),
            ("mesero_carrera", "cancelar"),
        ])
        self.assertEqual(resultados, [200, 409])
        self.item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.segundo.refresh_from_db()
        if self.item.estado == ItemPedido.Estado.CANCELADO:
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))
            self.assertEqual(self.segundo.cantidad_disponible, Decimal("5.000"))
        else:
            self.assertEqual(self.item.estado, ItemPedido.Estado.EN_PREPARACION)
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("3.750"))
            self.assertEqual(self.segundo.cantidad_disponible, Decimal("4.500"))

    def test_two_concurrent_cancellations_refund_historical_ingredients_once(self):
        resultados = self.correr_carrera([
            ("mesero_carrera", "cancelar"),
            ("mesero_carrera", "cancelar"),
        ])
        self.assertEqual(resultados, [200, 409])
        self.item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.segundo.refresh_from_db()
        self.assertEqual(self.item.estado, ItemPedido.Estado.CANCELADO)
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))
        self.assertEqual(self.segundo.cantidad_disponible, Decimal("5.000"))
        self.assertEqual(self.item.composicion.count(), 2)
