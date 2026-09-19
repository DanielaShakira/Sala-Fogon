"""Database-level checks for the relational model."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from .models import (
    AsignacionPago,
    ComposicionItemPedido,
    ComposicionPlato,
    Cuenta,
    Ingrediente,
    ItemPedido,
    Mesa,
    Pago,
    Pedido,
    Plato,
    Sesion,
    Usuario,
)


class RelationalModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        access = get_user_model().objects.create_user(username="mesero")
        cls.mesero = Usuario.objects.create(
            cuenta_acceso=access,
            nombre="Mesero de prueba",
            rol=Usuario.Rol.MESERO,
        )
        cls.mesa = Mesa.objects.create(numero=1)
        cls.sesion = Sesion.objects.create(mesa=cls.mesa, mesero=cls.mesero)
        cls.cuenta = Cuenta.objects.create(sesion=cls.sesion)
        cls.plato = Plato.objects.create(
            nombre="Plato de prueba",
            precio=Decimal("15000.50"),
            puntaje_carga_preparacion=2,
        )
        cls.ingrediente = Ingrediente.objects.create(
            nombre="Ingrediente de prueba",
            cantidad_disponible=Decimal("2.125"),
        )
        cls.receta = ComposicionPlato.objects.create(
            plato=cls.plato,
            ingrediente=cls.ingrediente,
            cantidad_requerida=Decimal("0.125"),
        )
        cls.pedido = Pedido.objects.create(sesion=cls.sesion)
        cls.item = ItemPedido.objects.create(
            pedido=cls.pedido,
            plato=cls.plato,
            precio_unitario=cls.plato.precio,
        )
        cls.composicion_item = ComposicionItemPedido.objects.create(
            item_pedido=cls.item,
            ingrediente=cls.ingrediente,
            cantidad=cls.receta.cantidad_requerida,
        )
        cls.pago = Pago.objects.create(cuenta=cls.cuenta)
        cls.asignacion = AsignacionPago.objects.create(
            pago=cls.pago,
            item_pedido=cls.item,
        )

    def test_only_one_active_session_per_table(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sesion.objects.create(mesa=self.mesa, mesero=self.mesero)

        self.sesion.fecha_hora_fin = timezone.now()
        self.sesion.save(update_fields=["fecha_hora_fin"])
        next_session = Sesion.objects.create(mesa=self.mesa, mesero=self.mesero)
        self.assertIsNone(next_session.fecha_hora_fin)
        self.assertEqual(self.mesa.sesiones.count(), 2)

    def test_other_table_can_have_an_active_session(self):
        other_table = Mesa.objects.create(numero=2)
        Sesion.objects.create(mesa=other_table, mesero=self.mesero)
        self.assertEqual(Sesion.objects.filter(fecha_hora_fin__isnull=True).count(), 2)

    def test_table_numbers_are_unique(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Mesa.objects.create(numero=1)

    def test_one_account_per_session(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cuenta.objects.create(sesion=self.sesion)

    def test_recipe_ingredient_is_unique_per_dish(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ComposicionPlato.objects.create(
                plato=self.plato,
                ingrediente=self.ingrediente,
                cantidad_requerida=Decimal("0.250"),
            )

    def test_snapshot_ingredient_is_unique_per_item(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ComposicionItemPedido.objects.create(
                item_pedido=self.item,
                ingrediente=self.ingrediente,
                cantidad=Decimal("0.250"),
            )

    def test_item_can_belong_to_only_one_payment(self):
        second_payment = Pago.objects.create(cuenta=self.cuenta)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsignacionPago.objects.create(pago=second_payment, item_pedido=self.item)

    def test_decimal_values_and_relationships_round_trip(self):
        self.plato.refresh_from_db()
        self.ingrediente.refresh_from_db()
        self.assertEqual(self.plato.precio, Decimal("15000.50"))
        self.assertEqual(self.ingrediente.cantidad_disponible, Decimal("2.125"))
        self.assertEqual(self.mesa.sesiones.get().mesero, self.mesero)
        self.assertEqual(self.sesion.cuenta, self.cuenta)
        self.assertEqual(self.sesion.pedidos.get().items.get(), self.item)
        self.assertEqual(self.item.composicion.get().cantidad, Decimal("0.125"))
        self.assertEqual(self.cuenta.pagos.get().asignaciones.get().item_pedido, self.item)

    def test_database_rejects_negative_stock_and_price(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Ingrediente.objects.create(nombre="Negativo", cantidad_disponible=Decimal("-0.001"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Plato.objects.create(
                nombre="Negativo",
                precio=Decimal("-0.01"),
                puntaje_carga_preparacion=1,
            )

    def test_database_rejects_zero_recipe_quantity_and_invalid_state(self):
        other_ingredient = Ingrediente.objects.create(
            nombre="Otro",
            cantidad_disponible=Decimal("1.000"),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ComposicionPlato.objects.create(
                plato=self.plato,
                ingrediente=other_ingredient,
                cantidad_requerida=Decimal("0.000"),
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemPedido.objects.create(
                pedido=self.pedido,
                plato=self.plato,
                precio_unitario=self.plato.precio,
                estado="DESCONOCIDO",
            )

    def test_active_status_comes_from_django_auth_user(self):
        self.assertTrue(self.mesero.activo)
        self.mesero.cuenta_acceso.is_active = False
        self.mesero.cuenta_acceso.save(update_fields=["is_active"])
        self.assertFalse(self.mesero.activo)

    def test_derived_states_are_not_columns(self):
        for model in (Sesion, Pedido, Cuenta):
            with self.assertRaises(FieldDoesNotExist):
                model._meta.get_field("estado")

    def test_referenced_table_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.mesa.delete()
