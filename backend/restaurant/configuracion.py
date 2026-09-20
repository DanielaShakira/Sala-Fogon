"""Small operational catalogue configuration for restaurant administrators."""

from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound, ValidationError

from .models import ComposicionPlato, Ingrediente, Mesa, Plato
from .services import Conflicto


def crear_mesa(numero):
    try:
        with transaction.atomic():
            return Mesa.objects.create(numero=numero)
    except IntegrityError as exc:
        if Mesa.objects.filter(numero=numero).exists():
            raise ValidationError({"numero": "Ya existe una mesa con ese número."}) from exc
        raise


def crear_ingrediente(datos):
    return Ingrediente.objects.create(**datos)


def cambiar_estado_ingrediente(ingrediente_id, activo):
    with transaction.atomic():
        ingrediente = Ingrediente.objects.select_for_update().filter(pk=ingrediente_id).first()
        if ingrediente is None:
            raise NotFound("El ingrediente no existe.")
        if ingrediente.activo != activo:
            ingrediente.activo = activo
            ingrediente.save(update_fields=["activo"])
        return ingrediente


def ajustar_existencias(ingrediente_id, cantidad_esperada, cantidad_nueva):
    """Absolute adjustment with a precondition, serialized with order discounts."""
    with transaction.atomic():
        ingrediente = Ingrediente.objects.select_for_update().filter(pk=ingrediente_id).first()
        if ingrediente is None:
            raise NotFound("El ingrediente no existe.")
        if ingrediente.cantidad_disponible != cantidad_esperada:
            raise Conflicto({
                "detail": "Las existencias cambiaron. Actualiza la lista antes de ajustar.",
                "cantidad_actual": str(ingrediente.cantidad_disponible),
            })
        ingrediente.cantidad_disponible = cantidad_nueva
        ingrediente.save(update_fields=["cantidad_disponible"])
        return ingrediente


def guardar_plato(datos, plato_id=None):
    """Replace the current recipe while preserving every ordered item's snapshot."""
    with transaction.atomic():
        if plato_id is None:
            plato = Plato.objects.create(
                nombre=datos["nombre"], precio=datos["precio"],
                activo=datos["activo"],
            )
        else:
            # Order submission locks the plate before reading its recipe.
            plato = Plato.objects.select_for_update().filter(pk=plato_id).first()
            if plato is None:
                raise NotFound("El plato no existe.")

        ids = {fila["ingrediente_id"] for fila in datos["composicion"]}
        existentes = set(Ingrediente.objects.filter(pk__in=ids).values_list("pk", flat=True))
        if existentes != ids:
            raise ValidationError({"composicion": "Uno o más ingredientes no existen."})

        if plato_id is not None:
            plato.nombre = datos["nombre"]
            plato.precio = datos["precio"]
            plato.activo = datos["activo"]
            plato.save(update_fields=["nombre", "precio", "activo"])
            ComposicionPlato.objects.filter(plato=plato).delete()

        ComposicionPlato.objects.bulk_create([
            ComposicionPlato(
                plato=plato, ingrediente_id=fila["ingrediente_id"],
                cantidad_requerida=fila["cantidad_requerida"],
            )
            for fila in datos["composicion"]
        ])
        return plato
