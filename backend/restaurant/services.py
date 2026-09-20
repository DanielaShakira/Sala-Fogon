"""Transactional operations for sessions, orders and payments."""

from collections import defaultdict
from decimal import Decimal

from django.db import IntegrityError, transaction
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError

from .models import (
    ComposicionItemPedido,
    ComposicionPlato,
    Cuenta,
    AsignacionPago,
    Ingrediente,
    ItemPedido,
    Mesa,
    Pedido,
    Pago,
    Plato,
    Sesion,
    Usuario,
)


class Conflicto(APIException):
    status_code = 409
    default_detail = "La operación entra en conflicto con el estado actual."


def sesion_bloqueada(sesion_id, mesero):
    """All writes to a session acquire this lock before touching its items."""
    sesion = Sesion.objects.select_for_update().filter(pk=sesion_id).first()
    if sesion is None:
        raise NotFound("La sesión no existe.")
    if sesion.mesero_id != mesero.id:
        raise PermissionDenied("La sesión pertenece a otro mesero.")
    if sesion.fecha_hora_fin is not None:
        raise Conflicto("La sesión está cerrada.")
    return sesion


def abrir_sesion(mesa_id, mesero):
    try:
        with transaction.atomic():
            # Employee deactivation takes this lock too. Recheck activity after
            # acquiring it so a concurrent deactivation cannot be bypassed.
            perfil = Usuario.objects.select_for_update().get(pk=mesero.pk)
            if perfil.rol != Usuario.Rol.MESERO or not perfil.activo:
                raise PermissionDenied("La cuenta no tiene el rol activo requerido.")
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
        sesion = sesion_bloqueada(datos["sesion_id"], mesero)

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


def avanzar_item(item_id, estado_esperado, estado_nuevo):
    """Lock the unit so competing preparation/cancellation requests serialize."""
    with transaction.atomic():
        item = ItemPedido.objects.select_for_update().filter(pk=item_id).first()
        if item is None:
            raise NotFound("El ítem no existe.")
        if item.estado != estado_esperado:
            raise Conflicto("El ítem ya no está en el estado requerido.")
        item.estado = estado_nuevo
        item.save(update_fields=["estado"])
        return item


def registrar_pago(sesion_id, item_ids, mesero):
    """Pay whole units only once all non-canceled preparation has finished."""
    with transaction.atomic():
        sesion = sesion_bloqueada(sesion_id, mesero)
        cuenta = Cuenta.objects.filter(sesion=sesion).first()
        if cuenta is None:
            raise Conflicto("La sesión no tiene una cuenta registrada.")

        # Lock every unit in ascending ID order. Kitchen may finish a unit at
        # the same time; the readiness decision then uses its committed state.
        items_sesion = list(ItemPedido.objects.select_for_update().filter(
            pedido__sesion=sesion
        ).order_by("pk"))
        por_id = {item.id: item for item in items_sesion}
        if any(item_id not in por_id for item_id in item_ids):
            raise ValidationError({"item_ids": "Uno o más ítems no existen o no pertenecen a esta sesión."})
        items = [por_id[item_id] for item_id in item_ids]
        if any(item.estado == ItemPedido.Estado.CANCELADO for item in items):
            raise Conflicto("Un ítem cancelado no puede asignarse a un pago.")
        if AsignacionPago.objects.filter(item_pedido_id__in=item_ids).exists():
            raise Conflicto("Uno o más ítems ya están asignados a un pago.")
        if any(item.estado not in (ItemPedido.Estado.LISTO, ItemPedido.Estado.CANCELADO)
               for item in items_sesion):
            raise Conflicto("No se pueden registrar pagos hasta que todos los ítems no cancelados estén listos.")

        pago = Pago.objects.create(cuenta=cuenta)
        for item in sorted(items, key=lambda actual: actual.id):
            AsignacionPago.objects.create(pago=pago, item_pedido=item)
        return pago


def cerrar_sesion(sesion_id, mesero):
    """The session lock excludes new orders, payments and competing closes."""
    with transaction.atomic():
        sesion = sesion_bloqueada(sesion_id, mesero)
        if not Cuenta.objects.filter(sesion=sesion).exists():
            raise Conflicto("La sesión no tiene una cuenta registrada.")
        pendientes = list(ItemPedido.objects.filter(
            pedido__sesion=sesion,
            asignacion_pago__isnull=True,
        ).exclude(estado=ItemPedido.Estado.CANCELADO).order_by("pk").values_list("pk", flat=True))
        if pendientes:
            raise Conflicto({
                "detail": "La cuenta tiene ítems pendientes de pago.",
                "item_ids_pendientes": pendientes,
            })
        from django.utils import timezone
        sesion.fecha_hora_fin = timezone.now()
        sesion.save(update_fields=["fecha_hora_fin"])
        return sesion


def cancelar_item(item_id, mesero):
    """Return the historical composition exactly once, in one transaction."""
    with transaction.atomic():
        sesion_id = ItemPedido.objects.filter(pk=item_id).values_list(
            "pedido__sesion_id", flat=True
        ).first()
        if sesion_id is None:
            raise NotFound("El ítem no existe.")
        # Match payment/order/close lock order: session, item, ingredients.
        sesion_bloqueada(sesion_id, mesero)
        item = ItemPedido.objects.select_for_update().filter(pk=item_id).first()
        if item is None:
            raise NotFound("El ítem no existe.")
        if item.estado != ItemPedido.Estado.EN_COLA:
            raise Conflicto("Solo se puede cancelar un ítem en cola.")
        if AsignacionPago.objects.filter(item_pedido=item).exists():
            raise Conflicto("Un ítem asignado a un pago no puede cancelarse.")

        cantidades = {
            fila.ingrediente_id: fila.cantidad
            for fila in ComposicionItemPedido.objects.filter(item_pedido=item)
        }
        ingredientes = Ingrediente.objects.select_for_update().filter(
            pk__in=cantidades
        ).order_by("pk")
        for ingrediente in ingredientes:
            ingrediente.cantidad_disponible += cantidades[ingrediente.id]
            ingrediente.save(update_fields=["cantidad_disponible"])

        item.estado = ItemPedido.Estado.CANCELADO
        item.save(update_fields=["estado"])
        return item
