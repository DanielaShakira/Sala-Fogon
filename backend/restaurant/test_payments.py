"""Account, partial payment, session closure and PostgreSQL concurrency checks."""

import base64
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    AsignacionPago, ComposicionItemPedido, ComposicionPlato, Cuenta, Ingrediente,
    ItemPedido, Mesa, Pago, Pedido, Plato, Sesion, Usuario,
)


def autenticar(cliente, usuario, clave="clave-prueba"):
    token = base64.b64encode(f"{usuario}:{clave}".encode()).decode()
    cliente.credentials(HTTP_AUTHORIZATION=f"Basic {token}")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CuentaYPagosTests(TestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        self.client = APIClient()
        acceso = get_user_model().objects.create_user("mesero_pagos", password="clave-prueba")
        self.mesero = Usuario.objects.create(cuenta_acceso=acceso, nombre="Mesero", rol=Usuario.Rol.MESERO)
        otro_acceso = get_user_model().objects.create_user("otro_pagos", password="clave-prueba")
        self.otro = Usuario.objects.create(cuenta_acceso=otro_acceso, nombre="Otro", rol=Usuario.Rol.MESERO)
        cocinero_acceso = get_user_model().objects.create_user("cocinero_pagos", password="clave-prueba")
        Usuario.objects.create(cuenta_acceso=cocinero_acceso, nombre="Cocinero", rol=Usuario.Rol.COCINERO)
        self.mesa = Mesa.objects.create(numero=101)
        self.sesion = Sesion.objects.create(mesa=self.mesa, mesero=self.mesero)
        self.cuenta = Cuenta.objects.create(sesion=self.sesion)
        self.ingrediente = Ingrediente.objects.create(nombre="Harina", cantidad_disponible=Decimal("100.000"))
        self.plato = Plato.objects.create(nombre="Plato", precio=Decimal("12000.50"), puntaje_carga_preparacion=1)
        self.otro_plato = Plato.objects.create(nombre="Otro plato", precio=Decimal("9000.00"), puntaje_carga_preparacion=1)
        for plato in (self.plato, self.otro_plato):
            ComposicionPlato.objects.create(plato=plato, ingrediente=self.ingrediente, cantidad_requerida=Decimal("1.250"))
        autenticar(self.client, "mesero_pagos")

    def enviar(self, plato=None, cantidad=1, sesion=None):
        respuesta = self.client.post("/api/pedidos/", {
            "sesion_id": (sesion or self.sesion).id,
            "items": [{"plato_id": (plato or self.plato).id, "cantidad": cantidad}],
        }, format="json")
        self.assertEqual(respuesta.status_code, 201)
        return Pedido.objects.get(pk=respuesta.data["id"])

    def pagar(self, ids, sesion=None):
        return self.client.post(
            f"/api/sesiones/{(sesion or self.sesion).id}/pagos/",
            {"item_ids": ids}, format="json",
        )

    def cuenta_api(self):
        return self.client.get(f"/api/sesiones/{self.sesion.id}/cuenta/")

    def dejar_listos(self):
        ItemPedido.objects.filter(pedido__sesion=self.sesion).exclude(
            estado=ItemPedido.Estado.CANCELADO
        ).update(estado=ItemPedido.Estado.LISTO)

    def cerrar(self):
        return self.client.post(f"/api/sesiones/{self.sesion.id}/cerrar/")

    def test_account_uses_historical_prices_and_excludes_canceled_units(self):
        primero = self.enviar(cantidad=2)
        segundo = self.enviar(plato=self.otro_plato)
        cancelado, vigente = list(primero.items.order_by("id"))
        self.assertEqual(self.client.post(f"/api/items/{cancelado.id}/cancelar/").status_code, 200)
        self.plato.precio = Decimal("50000.00")
        self.plato.save(update_fields=["precio"])
        respuesta = self.cuenta_api()
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.data
        self.assertEqual(datos["mesa_numero"], self.mesa.numero)
        self.assertEqual(datos["sesion_id"], self.sesion.id)
        self.assertEqual([p["id"] for p in datos["pedidos"]], [primero.id, segundo.id])
        self.assertEqual(datos["total_consumo"], "21000.50")
        self.assertEqual(datos["total_pagado"], "0.00")
        self.assertEqual(datos["total_pendiente"], "21000.50")
        self.assertEqual(datos["item_ids_pendientes"], [vigente.id, segundo.items.get().id])
        self.assertFalse(datos["pago_habilitado"])
        self.assertEqual(datos["item_ids_no_listos"], [vigente.id, segundo.items.get().id])
        self.assertEqual(datos["pedidos"][0]["items"][0]["estado"], "CANCELADO")
        self.assertFalse(datos["pedidos"][0]["items"][0]["facturable"])
        self.assertEqual(datos["pedidos"][0]["items"][1]["precio_unitario"], "12000.50")

    def test_partial_payments_can_mix_orders_and_split_repeated_units(self):
        primero = self.enviar(cantidad=2)
        segundo = self.enviar(plato=self.otro_plato)
        a, b = list(primero.items.order_by("id"))
        c = segundo.items.get()
        self.dejar_listos()
        pago_uno = self.pagar([a.id, c.id])
        self.assertEqual(pago_uno.status_code, 201)
        self.assertEqual(pago_uno.data["total"], "21000.50")
        cuenta = self.cuenta_api().data
        self.assertEqual(cuenta["total_consumo"], "33001.00")
        self.assertEqual(cuenta["total_pagado"], "21000.50")
        self.assertEqual(cuenta["total_pendiente"], "12000.50")
        self.assertEqual(cuenta["item_ids_pendientes"], [b.id])
        self.assertEqual({i["id"] for i in cuenta["pagos"][0]["items"]}, {a.id, c.id})
        self.assertEqual(self.pagar([b.id]).status_code, 201)
        cuenta = self.cuenta_api().data
        self.assertEqual(cuenta["total_pagado"], "33001.00")
        self.assertEqual(cuenta["total_pendiente"], "0.00")
        self.assertEqual(cuenta["estado_cuenta"], "PAGADA")
        self.assertEqual(Pago.objects.count(), 2)
        self.assertEqual(AsignacionPago.objects.count(), 3)

    def test_client_amount_is_ignored_in_favor_of_historical_item_price(self):
        item = self.enviar().items.get()
        self.dejar_listos()
        self.plato.precio = Decimal("30000.00")
        self.plato.save(update_fields=["precio"])
        respuesta = self.client.post(
            f"/api/sesiones/{self.sesion.id}/pagos/",
            {"item_ids": [item.id], "monto": "0.01"}, format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.data["total"], "12000.50")
        self.assertEqual(self.cuenta_api().data["total_pagado"], "12000.50")

    def test_invalid_empty_duplicate_foreign_canceled_and_paid_items_are_rejected_atomically(self):
        primero = self.enviar(cantidad=3)
        valido, cancelado, pagado = list(primero.items.order_by("id"))
        self.assertEqual(self.client.post(f"/api/items/{cancelado.id}/cancelar/").status_code, 200)
        self.dejar_listos()
        self.assertEqual(self.pagar([pagado.id]).status_code, 201)
        otra_mesa = Mesa.objects.create(numero=102)
        otra_sesion = Sesion.objects.create(mesa=otra_mesa, mesero=self.mesero)
        Cuenta.objects.create(sesion=otra_sesion)
        ajeno = self.enviar(sesion=otra_sesion).items.get()
        for ids, estado in (
            ([], 400), ([valido.id, valido.id], 400),
            ([valido.id, "3"], 400), ([valido.id, -1], 400),
            ([valido.id, True], 400), ([valido.id, 1.5], 400),
            ([valido.id, 9223372036854775808], 400),
            ([valido.id, 999999], 400), ([valido.id, ajeno.id], 400),
            ([valido.id, cancelado.id], 409), ([valido.id, pagado.id], 409),
        ):
            with self.subTest(ids=ids):
                self.assertEqual(self.pagar(ids).status_code, estado)
                self.assertEqual(Pago.objects.count(), 1)
                self.assertFalse(AsignacionPago.objects.filter(item_pedido=valido).exists())

    def test_failure_during_second_assignment_rolls_back_payment_and_first_assignment(self):
        pedido = self.enviar(cantidad=2)
        self.dejar_listos()
        ids = list(pedido.items.order_by("id").values_list("id", flat=True))
        crear_original = AsignacionPago.objects.create
        llamadas = 0

        def crear_con_fallo(*args, **kwargs):
            nonlocal llamadas
            llamadas += 1
            if llamadas == 2:
                raise RuntimeError("fallo de asignación simulado")
            return crear_original(*args, **kwargs)

        with patch("restaurant.services.AsignacionPago.objects.create", side_effect=crear_con_fallo):
            with self.assertRaisesMessage(RuntimeError, "fallo de asignación simulado"):
                self.pagar(ids)
        self.assertFalse(Pago.objects.exists())
        self.assertFalse(AsignacionPago.objects.exists())
        self.assertEqual(self.cuenta_api().data["item_ids_pendientes"], ids)

    def test_close_requires_all_non_canceled_units_paid_and_reopens_table(self):
        pedido = self.enviar(cantidad=2)
        self.dejar_listos()
        ids = list(pedido.items.order_by("id").values_list("id", flat=True))
        self.assertEqual(self.pagar([ids[0]]).status_code, 201)
        respuesta = self.cerrar()
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn(str(ids[1]), str(respuesta.data["item_ids_pendientes"]))
        self.sesion.refresh_from_db()
        self.assertIsNone(self.sesion.fecha_hora_fin)
        self.assertEqual(self.pagar([ids[1]]).status_code, 201)
        self.assertEqual(self.cerrar().status_code, 200)
        self.sesion.refresh_from_db()
        self.assertIsNotNone(self.sesion.fecha_hora_fin)
        self.assertEqual(self.cerrar().status_code, 409)
        self.assertEqual(self.pagar([ids[0]]).status_code, 409)
        self.assertEqual(self.client.post("/api/pedidos/", {
            "sesion_id": self.sesion.id,
            "items": [{"plato_id": self.plato.id, "cantidad": 1}],
        }, format="json").status_code, 409)
        nueva = self.client.post("/api/sesiones/", {"mesa_id": self.mesa.id}, format="json")
        self.assertEqual(nueva.status_code, 201)
        self.assertNotEqual(nueva.data["id"], self.sesion.id)
        self.assertEqual(Cuenta.objects.count(), 2)
        self.assertEqual(self.cuenta_api().status_code, 200)

    def test_empty_consumption_can_close(self):
        self.assertEqual(self.cerrar().status_code, 200)

    def test_only_canceled_consumption_can_close_without_payment(self):
        item = self.enviar().items.get()
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 200)
        self.assertEqual(self.cuenta_api().data["total_consumo"], "0.00")
        self.assertEqual(self.cerrar().status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_payment_requires_all_non_canceled_units_ready(self):
        pedido = self.enviar(cantidad=2)
        listo, pendiente = list(pedido.items.order_by("id"))
        listo.estado = ItemPedido.Estado.LISTO
        listo.save(update_fields=["estado"])
        self.assertFalse(self.cuenta_api().data["pago_habilitado"])
        self.assertEqual(self.pagar([listo.id]).status_code, 409)
        pendiente.estado = ItemPedido.Estado.EN_PREPARACION
        pendiente.save(update_fields=["estado"])
        self.assertEqual(self.pagar([listo.id]).status_code, 409)
        self.assertFalse(Pago.objects.exists())
        pendiente.estado = ItemPedido.Estado.LISTO
        pendiente.save(update_fields=["estado"])
        self.assertTrue(self.cuenta_api().data["pago_habilitado"])
        self.assertEqual(self.pagar([listo.id]).status_code, 201)

    def test_new_order_after_partial_payment_pauses_further_payments_until_ready(self):
        primero = self.enviar().items.get()
        self.dejar_listos()
        self.assertEqual(self.pagar([primero.id]).status_code, 201)
        segundo = self.enviar().items.get()
        cuenta = self.cuenta_api().data
        self.assertFalse(cuenta["pago_habilitado"])
        self.assertEqual(cuenta["total_pagado"], "12000.50")
        self.assertEqual(self.pagar([segundo.id]).status_code, 409)
        self.assertEqual(self.cerrar().status_code, 409)
        segundo.estado = ItemPedido.Estado.LISTO
        segundo.save(update_fields=["estado"])
        self.assertEqual(self.pagar([segundo.id]).status_code, 201)
        self.assertEqual(self.cerrar().status_code, 200)

    def test_paid_en_cola_item_cannot_be_canceled_even_if_legacy_data_exists(self):
        item = self.enviar().items.get()
        pago = Pago.objects.create(cuenta=self.cuenta)
        AsignacionPago.objects.create(pago=pago, item_pedido=item)
        self.ingrediente.refresh_from_db()
        anterior = self.ingrediente.cantidad_disponible
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 409)
        item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertEqual(item.estado, ItemPedido.Estado.EN_COLA)
        self.assertEqual(self.ingrediente.cantidad_disponible, anterior)
        self.assertEqual(AsignacionPago.objects.count(), 1)

    def test_auth_role_and_ownership_apply_to_account_payment_and_close(self):
        item = self.enviar().items.get()
        for ruta, metodo, datos in (
            (f"/api/sesiones/{self.sesion.id}/cuenta/", "get", None),
            (f"/api/sesiones/{self.sesion.id}/pagos/", "post", {"item_ids": [item.id]}),
            (f"/api/sesiones/{self.sesion.id}/cerrar/", "post", {}),
        ):
            for usuario, esperado in ((None, 401), ("otro_pagos", 403), ("cocinero_pagos", 403)):
                with self.subTest(ruta=ruta, usuario=usuario):
                    if usuario is None:
                        self.client.credentials()
                    else:
                        autenticar(self.client, usuario)
                    respuesta = getattr(self.client, metodo)(ruta, datos, format="json") if metodo == "post" else self.client.get(ruta)
                    self.assertEqual(respuesta.status_code, esperado)
        self.assertFalse(Pago.objects.exists())
        self.sesion.refresh_from_db()
        self.assertIsNone(self.sesion.fecha_hora_fin)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class CarreraPagosYCierreTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        acceso = get_user_model().objects.create_user("mesero_carrera_pago", password="clave-prueba")
        mesero = Usuario.objects.create(cuenta_acceso=acceso, nombre="Mesero", rol=Usuario.Rol.MESERO)
        acceso_cocinero = get_user_model().objects.create_user("cocinero_carrera_pago", password="clave-prueba")
        Usuario.objects.create(cuenta_acceso=acceso_cocinero, nombre="Cocinero", rol=Usuario.Rol.COCINERO)
        mesa = Mesa.objects.create(numero=201)
        self.sesion = Sesion.objects.create(mesa=mesa, mesero=mesero)
        Cuenta.objects.create(sesion=self.sesion)
        self.plato = Plato.objects.create(nombre="Plato", precio=Decimal("10.25"), puntaje_carga_preparacion=1)
        self.ingrediente = Ingrediente.objects.create(nombre="Ingrediente", cantidad_disponible=Decimal("3.750"))
        ComposicionPlato.objects.create(plato=self.plato, ingrediente=self.ingrediente, cantidad_requerida=Decimal("1.250"))
        pedido = Pedido.objects.create(sesion=self.sesion)
        self.item = ItemPedido.objects.create(pedido=pedido, plato=self.plato, precio_unitario=self.plato.precio)
        ComposicionItemPedido.objects.create(item_pedido=self.item, ingrediente=self.ingrediente, cantidad=Decimal("1.250"))
        self.item.estado = ItemPedido.Estado.LISTO
        self.item.save(update_fields=["estado"])

    def carrera(self, operaciones):
        inicio = Barrier(3, timeout=10)

        def solicitar(operacion):
            cliente = APIClient()
            autenticar(cliente, "mesero_carrera_pago")
            try:
                with connections["default"].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SELECT current_database(), pg_backend_pid()")
                    base, proceso = cursor.fetchone()
                inicio.wait()
                respuesta = operacion(cliente)
                return base, proceso, respuesta.status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as ejecutor:
            tareas = [ejecutor.submit(solicitar, operacion) for operacion in operaciones]
            inicio.wait()
            resultados = [tarea.result(timeout=15) for tarea in tareas]
        self.assertEqual({base for base, _, _ in resultados}, {"test_sala_fogon"})
        self.assertEqual(len({proceso for _, proceso, _ in resultados}), 2)
        return sorted(codigo for _, _, codigo in resultados)

    def pago(self, cliente):
        return cliente.post(f"/api/sesiones/{self.sesion.id}/pagos/", {"item_ids": [self.item.id]}, format="json")

    def cierre(self, cliente):
        return cliente.post(f"/api/sesiones/{self.sesion.id}/cerrar/")

    def finalizar_item(self, cliente):
        autenticar(cliente, "cocinero_carrera_pago")
        return cliente.post(f"/api/items/{self.item.id}/listo/")

    def envio(self, cliente):
        return cliente.post("/api/pedidos/", {
            "sesion_id": self.sesion.id,
            "items": [{"plato_id": self.plato.id, "cantidad": 1}],
        }, format="json")

    def test_two_payments_on_same_item_create_only_one_assignment(self):
        self.assertEqual(self.carrera([self.pago, self.pago]), [201, 409])
        self.assertEqual(Pago.objects.count(), 1)
        self.assertEqual(AsignacionPago.objects.count(), 1)
        self.assertEqual(AsignacionPago.objects.get().item_pedido_id, self.item.id)
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("3.750"))

    def test_payment_and_cancel_cannot_both_win_for_one_unit(self):
        self.item.estado = ItemPedido.Estado.EN_COLA
        self.item.save(update_fields=["estado"])
        resultados = self.carrera([
            self.pago,
            lambda cliente: cliente.post(f"/api/items/{self.item.id}/cancelar/"),
        ])
        self.assertEqual(resultados, [200, 409])
        self.item.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.item.estado, ItemPedido.Estado.CANCELADO)
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000"))
        self.assertFalse(Pago.objects.exists())
        self.assertFalse(AsignacionPago.objects.exists())

    def test_payment_and_kitchen_completion_use_current_item_state(self):
        self.item.estado = ItemPedido.Estado.EN_PREPARACION
        self.item.save(update_fields=["estado"])
        resultados = self.carrera([self.pago, self.finalizar_item])
        self.assertIn(resultados, ([200, 201], [200, 409]))
        self.item.refresh_from_db()
        self.assertEqual(self.item.estado, ItemPedido.Estado.LISTO)
        if 201 in resultados:
            self.assertEqual(Pago.objects.count(), 1)
            self.assertEqual(AsignacionPago.objects.get().item_pedido_id, self.item.id)
        else:
            self.assertFalse(Pago.objects.exists())
            self.assertFalse(AsignacionPago.objects.exists())

    def test_close_and_new_order_serialize_on_session(self):
        cliente = APIClient()
        autenticar(cliente, "mesero_carrera_pago")
        self.assertEqual(self.pago(cliente).status_code, 201)
        resultados = self.carrera([self.cierre, self.envio])
        self.assertIn(resultados, ([200, 409], [201, 409]))
        self.sesion.refresh_from_db()
        self.ingrediente.refresh_from_db()
        if self.sesion.fecha_hora_fin is None:
            self.assertEqual(Pedido.objects.count(), 2)
            self.assertEqual(ItemPedido.objects.count(), 2)
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("2.500"))
        else:
            self.assertEqual(Pedido.objects.count(), 1)
            self.assertEqual(ItemPedido.objects.count(), 1)
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("3.750"))

    def test_two_concurrent_closes_only_close_once(self):
        cliente = APIClient()
        autenticar(cliente, "mesero_carrera_pago")
        self.assertEqual(self.pago(cliente).status_code, 201)
        self.assertEqual(self.carrera([self.cierre, self.cierre]), [200, 409])
        self.sesion.refresh_from_db()
        self.assertIsNotNone(self.sesion.fecha_hora_fin)
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(Pago.objects.count(), 1)
