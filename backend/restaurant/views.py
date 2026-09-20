"""HTTP endpoints for waiters and kitchen staff."""

from decimal import Decimal

from django.db import transaction
from django.db.models import Prefetch
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AsignacionPago, Cuenta, ItemPedido, Mesa, Pago, Pedido, Plato, Sesion, Usuario
from .serializers import AperturaSesionSerializer, EnvioPedidoSerializer, RegistroPagoSerializer
from .services import Conflicto, abrir_sesion, avanzar_item, cancelar_item, cerrar_sesion, enviar_pedido, registrar_pago


def perfil_autenticado(request, rol=None):
    try:
        perfil = request.user.usuario_restaurante
    except Usuario.DoesNotExist as exc:
        raise PermissionDenied("La cuenta no tiene un perfil del restaurante.") from exc
    if not perfil.activo or (rol is not None and perfil.rol != rol):
        raise PermissionDenied("La cuenta no tiene el rol activo requerido.")
    return perfil


def mesero_autenticado(request):
    return perfil_autenticado(request, Usuario.Rol.MESERO)


def cocinero_autenticado(request):
    return perfil_autenticado(request, Usuario.Rol.COCINERO)


class VistaAutenticada(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]


class VistaMesero(VistaAutenticada):
    pass


class VistaCocina(VistaAutenticada):
    pass


class MiPerfilView(VistaAutenticada):
    def get(self, request):
        perfil = perfil_autenticado(request)
        return Response({"id": perfil.id, "nombre": perfil.nombre, "rol": perfil.rol})


class MesasView(VistaMesero):
    def get(self, request):
        perfil = mesero_autenticado(request)
        mesas = Mesa.objects.prefetch_related(
            Prefetch("sesiones", queryset=Sesion.objects.filter(fecha_hora_fin__isnull=True))
        ).order_by("numero")
        resultado = []
        for mesa in mesas:
            activa = next(iter(mesa.sesiones.all()), None)
            resultado.append({
                "id": mesa.id,
                "numero": mesa.numero,
                "sesion_activa_id": activa.id if activa else None,
                "sesion_propia": bool(activa and activa.mesero_id == perfil.id),
            })
        return Response(resultado)


class SesionesView(VistaMesero):
    def post(self, request):
        perfil = mesero_autenticado(request)
        datos = AperturaSesionSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        sesion = abrir_sesion(datos.validated_data["mesa_id"], perfil)
        return Response({
            "id": sesion.id,
            "mesa_id": sesion.mesa_id,
            "cuenta_id": sesion.cuenta.id,
            "fecha_hora_inicio": sesion.fecha_hora_inicio,
        }, status=201)


class PlatosView(VistaMesero):
    def get(self, request):
        mesero_autenticado(request)
        platos = Plato.objects.prefetch_related("composicion__ingrediente").order_by("nombre", "id")
        return Response([
            {
                "id": plato.id,
                "nombre": plato.nombre,
                "precio": str(plato.precio),
                "disponible": plato.activo and all(
                    fila.ingrediente.activo
                    and fila.ingrediente.cantidad_disponible >= fila.cantidad_requerida
                    for fila in plato.composicion.all()
                ),
            }
            for plato in platos
        ])


class PedidosView(VistaMesero):
    def post(self, request):
        perfil = mesero_autenticado(request)
        datos = EnvioPedidoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        pedido = enviar_pedido(datos.validated_data, perfil)
        return Response({
            "id": pedido.id,
            "sesion_id": pedido.sesion_id,
            "fecha_hora_creacion": pedido.fecha_hora_creacion,
            "items": [
                {
                    "id": item.id,
                    "plato_id": item.plato_id,
                    "precio_unitario": str(item.precio_unitario),
                    "estado": item.estado,
                }
                for item in pedido.items.order_by("id")
            ],
        }, status=201)


def representar_item(item):
    return {"id": item.id, "plato": item.plato.nombre, "estado": item.estado}


def calcular_estado_general(items):
    """Derive the order's display state; Pedido has no estado column."""
    if not items:
        return None  # The API does not create empty orders.
    vigentes = [item.estado for item in items if item.estado != ItemPedido.Estado.CANCELADO]
    if not vigentes:
        return "CANCELADO"
    if all(estado == ItemPedido.Estado.LISTO for estado in vigentes):
        return "COMPLETO"
    if all(estado == ItemPedido.Estado.EN_COLA for estado in vigentes):
        return "EN_COLA"
    return "EN_CURSO"


class PedidosSesionView(VistaMesero):
    def get(self, request, sesion_id):
        perfil = mesero_autenticado(request)
        sesion = Sesion.objects.filter(pk=sesion_id).first()
        if sesion is None:
            raise NotFound("La sesión no existe.")
        if sesion.mesero_id != perfil.id:
            raise PermissionDenied("La sesión pertenece a otro mesero.")
        pedidos = Pedido.objects.filter(sesion=sesion).prefetch_related(
            Prefetch("items", queryset=ItemPedido.objects.select_related("plato", "asignacion_pago").order_by("id"))
        ).order_by("fecha_hora_creacion", "id")
        resultado = []
        for numero, pedido in enumerate(pedidos, start=1):
            items = list(pedido.items.all())
            resultado.append({
                "id": pedido.id,
                "numero_en_sesion": numero,
                "fecha_hora_creacion": pedido.fecha_hora_creacion,
                "estado_general": calcular_estado_general(items),
                "items": [
                    {**representar_item(item), "pagado": hasattr(item, "asignacion_pago")}
                    for item in items
                ],
            })
        return Response(resultado)


class CuentaSesionView(VistaMesero):
    @transaction.atomic
    def get(self, request, sesion_id):
        perfil = mesero_autenticado(request)
        sesion = Sesion.objects.select_for_update().filter(pk=sesion_id).first()
        if sesion is None:
            raise NotFound("La sesión no existe.")
        if sesion.mesero_id != perfil.id:
            raise PermissionDenied("La sesión pertenece a otro mesero.")
        cuenta = Cuenta.objects.filter(sesion=sesion).first()
        if cuenta is None:
            raise Conflicto("La sesión no tiene una cuenta registrada.")

        pagos = Pago.objects.filter(cuenta=cuenta).prefetch_related(
            Prefetch("asignaciones", queryset=AsignacionPago.objects.select_related(
                "item_pedido__plato", "item_pedido__pedido"
            ).order_by("id"))
        ).order_by("fecha_hora", "id")
        pagos_resultado = []
        pago_por_item = {}
        total_pagado = Decimal("0.00")
        for pago in pagos:
            items_pago = []
            total_pago = Decimal("0.00")
            for asignacion in pago.asignaciones.all():
                item = asignacion.item_pedido
                pago_por_item[item.id] = pago.id
                total_pago += item.precio_unitario
                items_pago.append({
                    "id": item.id, "pedido_id": item.pedido_id,
                    "plato": item.plato.nombre,
                    "precio_unitario": str(item.precio_unitario),
                })
            total_pagado += total_pago
            pagos_resultado.append({
                "id": pago.id, "fecha_hora": pago.fecha_hora,
                "total": str(total_pago), "items": items_pago,
            })

        pedidos = Pedido.objects.filter(sesion=sesion).prefetch_related(
            Prefetch("items", queryset=ItemPedido.objects.select_related("plato").order_by("id"))
        ).order_by("fecha_hora_creacion", "id")
        pedidos_resultado = []
        pendientes = []
        no_listos = []
        total_consumo = Decimal("0.00")
        for numero, pedido in enumerate(pedidos, start=1):
            items_resultado = []
            for item in pedido.items.all():
                facturable = item.estado != ItemPedido.Estado.CANCELADO
                if facturable:
                    total_consumo += item.precio_unitario
                    if item.id not in pago_por_item:
                        pendientes.append(item.id)
                    if item.estado != ItemPedido.Estado.LISTO:
                        no_listos.append(item.id)
                items_resultado.append({
                    "id": item.id, "plato": item.plato.nombre,
                    "estado": item.estado,
                    "precio_unitario": str(item.precio_unitario),
                    "facturable": facturable,
                    "pago_id": pago_por_item.get(item.id),
                })
            pedidos_resultado.append({
                "id": pedido.id, "numero_en_sesion": numero,
                "fecha_hora_creacion": pedido.fecha_hora_creacion,
                "items": items_resultado,
            })
        return Response({
            "cuenta_id": cuenta.id,
            "sesion_id": sesion.id,
            "mesa_numero": sesion.mesa.numero,
            "fecha_hora_inicio": sesion.fecha_hora_inicio,
            "fecha_hora_fin": sesion.fecha_hora_fin,
            "pedidos": pedidos_resultado,
            "pagos": pagos_resultado,
            "total_consumo": str(total_consumo),
            "total_pagado": str(total_pagado),
            "total_pendiente": str(total_consumo - total_pagado),
            "estado_cuenta": "PENDIENTE" if pendientes else "PAGADA",
            "item_ids_pendientes": pendientes,
            "pago_habilitado": not no_listos,
            "item_ids_no_listos": no_listos,
        })


class PagosSesionView(VistaMesero):
    def post(self, request, sesion_id):
        perfil = mesero_autenticado(request)
        datos = RegistroPagoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        pago = registrar_pago(sesion_id, datos.validated_data["item_ids"], perfil)
        items = list(pago.asignaciones.select_related("item_pedido").order_by("id"))
        return Response({
            "id": pago.id,
            "sesion_id": sesion_id,
            "fecha_hora": pago.fecha_hora,
            "item_ids": [asignacion.item_pedido_id for asignacion in items],
            "total": str(sum((asignacion.item_pedido.precio_unitario for asignacion in items), Decimal("0.00"))),
        }, status=201)


class CerrarSesionView(VistaMesero):
    def post(self, request, sesion_id):
        perfil = mesero_autenticado(request)
        sesion = cerrar_sesion(sesion_id, perfil)
        return Response({"id": sesion.id, "fecha_hora_fin": sesion.fecha_hora_fin})


class ColaCocinaView(VistaCocina):
    def get(self, request):
        cocinero_autenticado(request)
        pendientes = (ItemPedido.Estado.EN_COLA, ItemPedido.Estado.EN_PREPARACION)
        pedidos = Pedido.objects.filter(items__estado__in=pendientes).distinct().select_related(
            "sesion__mesa"
        ).prefetch_related(
            Prefetch(
                "items",
                queryset=ItemPedido.objects.select_related("plato").order_by("id"),
            )
        ).order_by("fecha_hora_creacion", "id")
        resultado = []
        for pedido in pedidos:
            items = list(pedido.items.all())
            resultado.append({
                "id": pedido.id,
                "sesion_id": pedido.sesion_id,
                "mesa_numero": pedido.sesion.mesa.numero,
                "fecha_hora_creacion": pedido.fecha_hora_creacion,
                "observaciones": pedido.observaciones,
                "estado_general": calcular_estado_general(items),
                "items": [representar_item(item) for item in items if item.estado in pendientes],
            })
        return Response(resultado)


class IniciarItemView(VistaCocina):
    def post(self, request, item_id):
        cocinero_autenticado(request)
        item = avanzar_item(item_id, ItemPedido.Estado.EN_COLA, ItemPedido.Estado.EN_PREPARACION)
        return Response({"id": item.id, "estado": item.estado})


class ListoItemView(VistaCocina):
    def post(self, request, item_id):
        cocinero_autenticado(request)
        item = avanzar_item(item_id, ItemPedido.Estado.EN_PREPARACION, ItemPedido.Estado.LISTO)
        return Response({"id": item.id, "estado": item.estado})


class CancelarItemView(VistaMesero):
    def post(self, request, item_id):
        perfil = mesero_autenticado(request)
        item = cancelar_item(item_id, perfil)
        return Response({"id": item.id, "estado": item.estado})
