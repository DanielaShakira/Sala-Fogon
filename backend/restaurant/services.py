"""Transactional operations for sessions and orders."""

from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

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
)


class Conflicto(APIException):
    status_code = 409
    default_detail = "La operación entra en conflicto con el estado actual."


def abrir_sesion(mesa_id, mesero):
    try:
        with transaction.atomic():
            mesa = Mesa.objects.select_for_update().filter(pk=mesa_id).first()
            if mesa is None:
                raise NotFound("La mesa no existe.")
            if Sesion.objects.filter(mesa=mesa, fecha_hora_fin__isnull=True).exists():
                raise Conflicto("La mesa ya tiene una sesión activa.")
            sesion = Sesion.objects.create(mesa=mesa, mesero=mesero)
            Cuenta.objects.create(sesion=sesion)
            return sesion
    except IntegrityError as exc:
        # The partial unique index is the final guard against concurrent openings.
        if getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None) != "una_sesion_activa_por_mesa":
            raise
        raise Conflicto("La mesa ya tiene una sesión activa.") from exc


def enviar_pedido(datos, mesero):
    with transaction.atomic():
        sesion = Sesion.objects.select_for_update().filter(pk=datos["sesion_id"]).first()
        if sesion is None:
            raise NotFound("La sesión no existe.")
        if sesion.fecha_hora_fin is not None:
            raise Conflicto("La sesión está cerrada.")
        if sesion.mesero_id != mesero.id:
            raise PermissionDenied("La sesión pertenece a otro mesero.")

        cantidades = defaultdict(int)
        for linea in datos["items"]:
            cantidades[linea["plato_id"]] += linea["cantidad"]

        platos = {
            plato.id: plato
            for plato in Plato.objects.select_for_update().filter(
                pk__in=cantidades
            ).order_by("pk")
        }
        if len(platos) != len(cantidades):
            raise ValidationError({"items": "Uno o más platos no existen."})
        if any(not plato.activo for plato in platos.values()):
            raise Conflicto("Uno o más platos están inactivos.")

        recetas = defaultdict(list)
        requeridas = defaultdict(lambda: Decimal("0"))
        for fila in ComposicionPlato.objects.select_for_update().filter(
            plato_id__in=platos
        ).order_by("plato_id", "ingrediente_id"):
            recetas[fila.plato_id].append(fila)
            requeridas[fila.ingrediente_id] += fila.cantidad_requerida * cantidades[fila.plato_id]

        ingredientes = {
            ingrediente.id: ingrediente
            for ingrediente in Ingrediente.objects.select_for_update().filter(
                pk__in=requeridas
            ).order_by("pk")
        }
        for ingrediente_id, cantidad in requeridas.items():
            ingrediente = ingredientes[ingrediente_id]
            if not ingrediente.activo or ingrediente.cantidad_disponible < cantidad:
                raise Conflicto(f"Existencia insuficiente del ingrediente {ingrediente.nombre}.")

        pedido = Pedido.objects.create(
            sesion=sesion,
            observaciones=datos["observaciones"],
        )
        for plato_id in sorted(cantidades):
            for _ in range(cantidades[plato_id]):
                item = ItemPedido.objects.create(
                    pedido=pedido,
                    plato=platos[plato_id],
                    precio_unitario=platos[plato_id].precio,
                    estado=ItemPedido.Estado.EN_COLA,
                )
                for fila in recetas[plato_id]:
                    ComposicionItemPedido.objects.create(
                        item_pedido=item,
                        ingrediente_id=fila.ingrediente_id,
                        cantidad=fila.cantidad_requerida,
                    )

        for ingrediente_id in sorted(requeridas):
            ingrediente = ingredientes[ingrediente_id]
            ingrediente.cantidad_disponible -= requeridas[ingrediente_id]
            ingrediente.save(update_fields=["cantidad_disponible"])

        return pedido
