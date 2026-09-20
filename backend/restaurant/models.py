"""Relational model for the restaurant operation.

Business transitions and stock reservation belong in services, not here.
"""

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


# 12 total digits: prices have 2 decimal places; abstract portions have 3.
PRICE_DIGITS = 12
PRICE_DECIMALS = 2
QUANTITY_DIGITS = 12
QUANTITY_DECIMALS = 3


class Usuario(models.Model):
    class Rol(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        MESERO = "MESERO", "Mesero"
        COCINERO = "COCINERO", "Cocinero"

    # Django owns credentials and is_active. This model keeps restaurant data.
    cuenta_acceso = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="usuario_restaurante",
    )
    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=8, choices=Rol.choices)

    @property
    def activo(self):
        return self.cuenta_acceso.is_active

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(rol__in=("ADMIN", "MESERO", "COCINERO")),
                name="usuario_rol_valido",
            ),
        ]


class Mesa(models.Model):
    numero = models.PositiveIntegerField(unique=True)


class Sesion(models.Model):
    fecha_hora_inicio = models.DateTimeField(default=timezone.now)
    fecha_hora_fin = models.DateTimeField(null=True, blank=True)
    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name="sesiones")
    mesero = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="sesiones")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["mesa"],
                condition=Q(fecha_hora_fin__isnull=True),
                name="una_sesion_activa_por_mesa",
            ),
        ]


class Plato(models.Model):
    nombre = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=PRICE_DIGITS, decimal_places=PRICE_DECIMALS)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(precio__gte=0), name="plato_precio_no_negativo"),
        ]


class Ingrediente(models.Model):
    nombre = models.CharField(max_length=150)
    cantidad_disponible = models.DecimalField(
        max_digits=QUANTITY_DIGITS,
        decimal_places=QUANTITY_DECIMALS,
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad_disponible__gte=0),
                name="ingrediente_cantidad_no_negativa",
            ),
        ]


class ComposicionPlato(models.Model):
    plato = models.ForeignKey(Plato, on_delete=models.PROTECT, related_name="composicion")
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.PROTECT,
        related_name="recetas",
    )
    cantidad_requerida = models.DecimalField(
        max_digits=QUANTITY_DIGITS,
        decimal_places=QUANTITY_DECIMALS,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plato", "ingrediente"],
                name="ingrediente_unico_por_plato",
            ),
            models.CheckConstraint(
                condition=Q(cantidad_requerida__gt=0),
                name="composicion_plato_cantidad_positiva",
            ),
        ]


class Pedido(models.Model):
    fecha_hora_creacion = models.DateTimeField(default=timezone.now)
    observaciones = models.TextField(blank=True, default="")
    sesion = models.ForeignKey(Sesion, on_delete=models.PROTECT, related_name="pedidos")


class ItemPedido(models.Model):
    class Estado(models.TextChoices):
        EN_COLA = "EN_COLA", "En cola"
        EN_PREPARACION = "EN_PREPARACION", "En preparación"
        LISTO = "LISTO", "Listo"
        CANCELADO = "CANCELADO", "Cancelado"

    precio_unitario = models.DecimalField(max_digits=PRICE_DIGITS, decimal_places=PRICE_DECIMALS)
    estado = models.CharField(max_length=16, choices=Estado.choices, default=Estado.EN_COLA)
    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name="items")
    plato = models.ForeignKey(Plato, on_delete=models.PROTECT, related_name="items_pedidos")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(precio_unitario__gte=0),
                name="item_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=("EN_COLA", "EN_PREPARACION", "LISTO", "CANCELADO")),
                name="item_estado_valido",
            ),
        ]


class ComposicionItemPedido(models.Model):
    item_pedido = models.ForeignKey(
        ItemPedido,
        on_delete=models.PROTECT,
        related_name="composicion",
    )
    ingrediente = models.ForeignKey(
        Ingrediente,
        on_delete=models.PROTECT,
        related_name="composiciones_items",
    )
    cantidad = models.DecimalField(
        max_digits=QUANTITY_DIGITS,
        decimal_places=QUANTITY_DECIMALS,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["item_pedido", "ingrediente"],
                name="ingrediente_unico_por_item",
            ),
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="composicion_item_cantidad_positiva",
            ),
        ]


class Cuenta(models.Model):
    sesion = models.OneToOneField(
        Sesion,
        on_delete=models.PROTECT,
        related_name="cuenta",
    )


class Pago(models.Model):
    fecha_hora = models.DateTimeField(default=timezone.now)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.PROTECT, related_name="pagos")


class AsignacionPago(models.Model):
    pago = models.ForeignKey(Pago, on_delete=models.PROTECT, related_name="asignaciones")
    item_pedido = models.OneToOneField(
        ItemPedido,
        on_delete=models.PROTECT,
        related_name="asignacion_pago",
    )
