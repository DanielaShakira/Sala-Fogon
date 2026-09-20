"""Operational configuration, availability and PostgreSQL race checks."""

import base64
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    ComposicionItemPedido, ComposicionPlato, Cuenta, Ingrediente, ItemPedido,
    Mesa, Pedido, Plato, Sesion, Usuario,
)


def autenticar(cliente, username):
    token = base64.b64encode(f"{username}:ClaveLocal2026!".encode()).decode()
    cliente.credentials(HTTP_AUTHORIZATION=f"Basic {token}")


def crear_personal(username, rol):
    cuenta = get_user_model().objects.create_user(username, password="ClaveLocal2026!")
    return Usuario.objects.create(cuenta_acceso=cuenta, nombre=username, rol=rol)


def datos_plato(ingrediente_id, **cambios):
    datos = {
        "nombre": "Plato configurado", "precio": "12000.50",
        "activo": True,
        "composicion": [{"ingrediente_id": ingrediente_id, "cantidad_requerida": "2.000"}],
    }
    datos.update(cambios)
    return datos


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConfiguracionTests(TestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        self.client = APIClient()
        self.admin = crear_personal("admin_config", Usuario.Rol.ADMIN)
        self.mesero = crear_personal("mesero_config", Usuario.Rol.MESERO)
        crear_personal("cocinero_config", Usuario.Rol.COCINERO)
        self.mesa = Mesa.objects.create(numero=50)
        self.sesion = Sesion.objects.create(mesa=self.mesa, mesero=self.mesero)
        Cuenta.objects.create(sesion=self.sesion)
        self.ingrediente = Ingrediente.objects.create(
            nombre="Harina", cantidad_disponible=Decimal("10.000")
        )
        autenticar(self.client, "admin_config")

    def crear_plato(self, **cambios):
        return self.client.post(
            "/api/configuracion/platos/", datos_plato(self.ingrediente.id, **cambios), format="json"
        )

    def test_plate_score_is_absent_from_database_and_api(self):
        with connection.cursor() as cursor:
            columnas = {
                columna.name for columna in connection.introspection.get_table_description(
                    cursor, Plato._meta.db_table
                )
            }
        self.assertNotIn("puntaje_carga_preparacion", columnas)
        respuesta = self.crear_plato()
        self.assertEqual(respuesta.status_code, 201)
        self.assertNotIn("puntaje_carga_preparacion", respuesta.data)

    def test_only_admin_can_read_or_write_configuration(self):
        plato = Plato.objects.create(
            nombre="Existente", precio=Decimal("10.00")
        )
        rutas = [
            ("get", "/api/configuracion/mesas/", None),
            ("post", "/api/configuracion/mesas/", {"numero": 51}),
            ("get", "/api/configuracion/ingredientes/", None),
            ("post", "/api/configuracion/ingredientes/", {"nombre": "Sal", "cantidad_disponible": "1.000"}),
            ("patch", f"/api/configuracion/ingredientes/{self.ingrediente.id}/estado/", {"activo": False}),
            ("post", f"/api/configuracion/ingredientes/{self.ingrediente.id}/ajustar/", {
                "cantidad_esperada": "10.000", "cantidad_nueva": "5.000",
            }),
            ("get", "/api/configuracion/platos/", None),
            ("post", "/api/configuracion/platos/", datos_plato(self.ingrediente.id)),
            ("put", f"/api/configuracion/platos/{plato.id}/", datos_plato(self.ingrediente.id)),
        ]
        for username in ("mesero_config", "cocinero_config"):
            autenticar(self.client, username)
            for metodo, ruta, datos in rutas:
                with self.subTest(username=username, metodo=metodo, ruta=ruta):
                    respuesta = getattr(self.client, metodo)(ruta, datos, format="json")
                    self.assertEqual(respuesta.status_code, 403)
        self.client.credentials()
        self.assertEqual(self.client.get("/api/configuracion/platos/").status_code, 401)
        self.assertEqual(Mesa.objects.count(), 1)
        self.assertEqual(Ingrediente.objects.count(), 1)

    def test_tables_are_created_without_duplicates_or_status_column(self):
        respuesta = self.client.post("/api/configuracion/mesas/", {"numero": 51}, format="json")
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(set(respuesta.data), {"id", "numero"})
        self.assertEqual(self.client.post(
            "/api/configuracion/mesas/", {"numero": 51}, format="json"
        ).status_code, 400)
        for numero in (0, -1, "52", 1.5):
            self.assertEqual(self.client.post(
                "/api/configuracion/mesas/", {"numero": numero}, format="json"
            ).status_code, 400)
        self.assertEqual([fila["numero"] for fila in self.client.get(
            "/api/configuracion/mesas/"
        ).data], [50, 51])
        self.assertEqual(self.client.delete(f"/api/configuracion/mesas/{respuesta.data['id']}/").status_code, 404)

    def test_ingredient_creation_status_and_stock_precondition(self):
        respuesta = self.client.post("/api/configuracion/ingredientes/", {
            "nombre": "Aceite", "cantidad_disponible": "1.250", "activo": True,
        }, format="json")
        self.assertEqual(respuesta.status_code, 201)
        ingrediente_id = respuesta.data["id"]
        self.assertEqual(respuesta.data["cantidad_disponible"], "1.250")
        self.assertEqual(self.client.patch(
            f"/api/configuracion/ingredientes/{ingrediente_id}/estado/", {"activo": False}, format="json"
        ).status_code, 200)
        ruta = f"/api/configuracion/ingredientes/{ingrediente_id}/ajustar/"
        self.assertEqual(self.client.post(ruta, {
            "cantidad_esperada": "1.250", "cantidad_nueva": "3.500",
        }, format="json").status_code, 200)
        conflicto = self.client.post(ruta, {
            "cantidad_esperada": "1.250", "cantidad_nueva": "9.000",
        }, format="json")
        self.assertEqual(conflicto.status_code, 409)
        self.assertEqual(conflicto.data["cantidad_actual"], "3.500")
        ingrediente = Ingrediente.objects.get(pk=ingrediente_id)
        self.assertEqual(ingrediente.cantidad_disponible, Decimal("3.500"))
        self.assertFalse(ingrediente.activo)
        self.assertEqual(self.client.patch(
            f"/api/configuracion/ingredientes/{ingrediente_id}/estado/", {"activo": True}, format="json"
        ).status_code, 200)

    def test_invalid_ingredient_quantities_do_not_write(self):
        for cantidad in ("-0.001", "1.2345", "1000000000.000"):
            with self.subTest(cantidad=cantidad):
                self.assertEqual(self.client.post("/api/configuracion/ingredientes/", {
                    "nombre": "Inválido", "cantidad_disponible": cantidad,
                }, format="json").status_code, 400)
        self.assertEqual(Ingrediente.objects.count(), 1)

    def test_recipe_creation_and_derived_availability(self):
        respuesta = self.crear_plato()
        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(respuesta.data["disponible"])
        plato_id = respuesta.data["id"]
        self.assertEqual(ComposicionPlato.objects.get(plato_id=plato_id).cantidad_requerida, Decimal("2.000"))
        estado = f"/api/configuracion/ingredientes/{self.ingrediente.id}/estado/"
        self.assertEqual(self.client.patch(estado, {"activo": False}, format="json").status_code, 200)
        self.assertFalse(self.client.get("/api/configuracion/platos/").data[0]["disponible"])
        self.assertTrue(Plato.objects.get(pk=plato_id).activo)
        self.assertEqual(self.client.patch(estado, {"activo": True}, format="json").status_code, 200)
        self.assertTrue(self.client.get("/api/configuracion/platos/").data[0]["disponible"])
        self.assertEqual(self.client.post(f"/api/configuracion/ingredientes/{self.ingrediente.id}/ajustar/", {
            "cantidad_esperada": "10.000", "cantidad_nueva": "1.000",
        }, format="json").status_code, 200)
        self.assertFalse(self.client.get("/api/configuracion/platos/").data[0]["disponible"])
        self.assertEqual(self.client.post(f"/api/configuracion/ingredientes/{self.ingrediente.id}/ajustar/", {
            "cantidad_esperada": "1.000", "cantidad_nueva": "2.000",
        }, format="json").status_code, 200)
        self.assertTrue(self.client.get("/api/configuracion/platos/").data[0]["disponible"])
        self.assertEqual(self.client.put(f"/api/configuracion/platos/{plato_id}/", datos_plato(
            self.ingrediente.id, activo=False
        ), format="json").status_code, 200)
        self.assertFalse(self.client.get("/api/configuracion/platos/").data[0]["disponible"])

    def test_recipe_rejects_duplicate_or_missing_ingredients_atomically(self):
        repetida = {"ingrediente_id": self.ingrediente.id, "cantidad_requerida": "1.000"}
        self.assertEqual(self.crear_plato(composicion=[repetida, repetida]).status_code, 400)
        self.assertEqual(self.crear_plato(composicion=[{
            "ingrediente_id": 999999, "cantidad_requerida": "1.000",
        }]).status_code, 400)
        self.assertEqual(Plato.objects.count(), 0)
        respuesta = self.crear_plato()
        plato_id = respuesta.data["id"]
        self.assertEqual(self.client.put(f"/api/configuracion/platos/{plato_id}/", datos_plato(
            self.ingrediente.id, nombre="No debe guardarse", composicion=[repetida, repetida]
        ), format="json").status_code, 400)
        self.assertEqual(Plato.objects.get(pk=plato_id).nombre, "Plato configurado")
        self.assertEqual(ComposicionPlato.objects.filter(plato_id=plato_id).count(), 1)

    def test_plate_fields_and_recipe_quantities_are_validated(self):
        for cambios in (
            {"precio": "-1.00"}, {"precio": "1.234"},
            {"puntaje_carga_preparacion": 1},
            {"composicion": [{"ingrediente_id": self.ingrediente.id, "cantidad_requerida": "0.000"}]},
            {"composicion": [{"ingrediente_id": self.ingrediente.id, "cantidad_requerida": "1.0001"}]},
        ):
            with self.subTest(cambios=cambios):
                self.assertEqual(self.crear_plato(**cambios).status_code, 400)
        self.assertFalse(Plato.objects.exists())

    def test_order_rechecks_current_availability_and_preserves_history(self):
        respuesta = self.crear_plato()
        plato_id = respuesta.data["id"]
        autenticar(self.client, "mesero_config")
        self.assertTrue(next(p for p in self.client.get("/api/platos/").data if p["id"] == plato_id)["disponible"])
        autenticar(self.client, "admin_config")
        self.client.patch(f"/api/configuracion/ingredientes/{self.ingrediente.id}/estado/", {
            "activo": False,
        }, format="json")
        autenticar(self.client, "mesero_config")
        self.assertFalse(next(p for p in self.client.get("/api/platos/").data if p["id"] == plato_id)["disponible"])
        self.assertEqual(self.client.post("/api/pedidos/", {
            "sesion_id": self.sesion.id,
            "items": [{"plato_id": plato_id, "cantidad": 1}],
        }, format="json").status_code, 409)
        self.assertFalse(Pedido.objects.exists())
        autenticar(self.client, "admin_config")
        self.client.patch(f"/api/configuracion/ingredientes/{self.ingrediente.id}/estado/", {
            "activo": True,
        }, format="json")
        autenticar(self.client, "mesero_config")
        envio = self.client.post("/api/pedidos/", {
            "sesion_id": self.sesion.id,
            "items": [{"plato_id": plato_id, "cantidad": 1}],
        }, format="json")
        self.assertEqual(envio.status_code, 201)
        item = ItemPedido.objects.get(pedido_id=envio.data["id"])
        self.assertEqual(item.precio_unitario, Decimal("12000.50"))
        self.assertEqual(ComposicionItemPedido.objects.get(item_pedido=item).cantidad, Decimal("2.000"))
        otro = Ingrediente.objects.create(nombre="Tomate", cantidad_disponible=Decimal("5.000"))
        autenticar(self.client, "admin_config")
        edicion = self.client.put(f"/api/configuracion/platos/{plato_id}/", datos_plato(
            otro.id, precio="16000.00", composicion=[{
                "ingrediente_id": otro.id, "cantidad_requerida": "1.500",
            }],
        ), format="json")
        self.assertEqual(edicion.status_code, 200)
        item.refresh_from_db()
        self.assertEqual(item.precio_unitario, Decimal("12000.50"))
        composicion = ComposicionItemPedido.objects.get(item_pedido=item)
        self.assertEqual(composicion.ingrediente_id, self.ingrediente.id)
        self.assertEqual(composicion.cantidad, Decimal("2.000"))
        autenticar(self.client, "mesero_config")
        self.assertEqual(self.client.post(f"/api/items/{item.id}/cancelar/").status_code, 200)
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("10.000"))


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class ConfiguracionConcurrenteTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.settings_dict["NAME"], "test_sala_fogon")
        crear_personal("admin_carrera_config", Usuario.Rol.ADMIN)
        mesero = crear_personal("mesero_carrera_config", Usuario.Rol.MESERO)
        mesa = Mesa.objects.create(numero=70)
        self.sesion = Sesion.objects.create(mesa=mesa, mesero=mesero)
        Cuenta.objects.create(sesion=self.sesion)
        self.ingrediente = Ingrediente.objects.create(
            nombre="Harina", cantidad_disponible=Decimal("5.000")
        )
        self.plato = Plato.objects.create(
            nombre="Plato", precio=Decimal("100.00")
        )
        ComposicionPlato.objects.create(
            plato=self.plato, ingrediente=self.ingrediente, cantidad_requerida=Decimal("2.000")
        )

    def carrera(self, operaciones):
        inicio = Barrier(3, timeout=10)

        def solicitar(username, metodo, ruta, datos):
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
            tareas = [ejecutor.submit(solicitar, *operacion) for operacion in operaciones]
            inicio.wait()
            resultados = [tarea.result(timeout=15) for tarea in tareas]
        self.assertEqual({base for base, _, _ in resultados}, {"test_sala_fogon"})
        self.assertEqual(len({proceso for _, proceso, _ in resultados}), 2)
        return [codigo for _, _, codigo in resultados]

    def test_stock_adjustment_and_order_do_not_lose_updates(self):
        codigos = self.carrera([
            ("admin_carrera_config", "post", f"/api/configuracion/ingredientes/{self.ingrediente.id}/ajustar/", {
                "cantidad_esperada": "5.000", "cantidad_nueva": "0.000",
            }),
            ("mesero_carrera_config", "post", "/api/pedidos/", {
                "sesion_id": self.sesion.id,
                "items": [{"plato_id": self.plato.id, "cantidad": 1}],
            }),
        ])
        self.assertIn(codigos, ([200, 409], [409, 201]))
        self.ingrediente.refresh_from_db()
        if codigos == [200, 409]:
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("0.000"))
            self.assertFalse(Pedido.objects.exists())
        else:
            self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("3.000"))
            self.assertEqual(ItemPedido.objects.count(), 1)

    def test_recipe_edit_and_order_use_one_complete_recipe(self):
        codigos = self.carrera([
            ("admin_carrera_config", "put", f"/api/configuracion/platos/{self.plato.id}/", datos_plato(
                self.ingrediente.id, nombre="Plato nuevo", precio="200.00",
                composicion=[{"ingrediente_id": self.ingrediente.id, "cantidad_requerida": "3.000"}],
            )),
            ("mesero_carrera_config", "post", "/api/pedidos/", {
                "sesion_id": self.sesion.id,
                "items": [{"plato_id": self.plato.id, "cantidad": 1}],
            }),
        ])
        self.assertEqual(codigos, [200, 201])
        item = ItemPedido.objects.get()
        historica = ComposicionItemPedido.objects.get(item_pedido=item).cantidad
        self.assertIn((item.precio_unitario, historica), (
            (Decimal("100.00"), Decimal("2.000")),
            (Decimal("200.00"), Decimal("3.000")),
        ))
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("5.000") - historica)
        self.assertEqual(ComposicionPlato.objects.get(plato=self.plato).cantidad_requerida, Decimal("3.000"))
