"""Small HTTP boundary for the first waiter flow."""

from django.db.models import Prefetch
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Mesa, Plato, Sesion, Usuario
from .serializers import AperturaSesionSerializer, EnvioPedidoSerializer
from .services import abrir_sesion, enviar_pedido


def mesero_autenticado(request):
    try:
        perfil = request.user.usuario_restaurante
    except Usuario.DoesNotExist as exc:
        raise PermissionDenied("La cuenta no tiene un perfil del restaurante.") from exc
    if not perfil.activo or perfil.rol != Usuario.Rol.MESERO:
        raise PermissionDenied("Esta operación requiere un mesero activo.")
    return perfil


class VistaMesero(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]


class MiPerfilView(VistaMesero):
    def get(self, request):
        perfil = mesero_autenticado(request)
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
