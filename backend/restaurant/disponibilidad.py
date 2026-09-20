"""One availability rule for catalogue display and order submission."""

from collections import defaultdict
from decimal import Decimal


def problema_disponibilidad(platos, recetas, ingredientes, cantidades):
    """Return the first reason a set of plate units cannot be requested.

    `recetas` maps each plate ID to its current composition rows. Shared
    ingredients are accumulated before checking stock, so this also covers
    multi-plate orders. Call with one unit for catalogue availability.
    """
    requeridas = defaultdict(lambda: Decimal("0"))
    for plato_id in sorted(cantidades):
        plato = platos[plato_id]
        if not plato.activo:
            return ("plato_inactivo", plato), requeridas
        for fila in recetas.get(plato_id, ()):
            requeridas[fila.ingrediente_id] += fila.cantidad_requerida * cantidades[plato_id]

    for ingrediente_id in sorted(requeridas):
        ingrediente = ingredientes[ingrediente_id]
        if not ingrediente.activo:
            return ("ingrediente_inactivo", ingrediente), requeridas
        if ingrediente.cantidad_disponible < requeridas[ingrediente_id]:
            return ("existencia_insuficiente", ingrediente), requeridas
    return None, requeridas


def plato_disponible(plato):
    """Catalogue projection; order submission uses the same rule with all units."""
    filas = list(plato.composicion.all())
    ingredientes = {fila.ingrediente_id: fila.ingrediente for fila in filas}
    problema, _ = problema_disponibilidad(
        {plato.id: plato}, {plato.id: filas}, ingredientes, {plato.id: 1}
    )
    return problema is None
