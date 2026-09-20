"""Role-protected HTTP endpoints for tables, ingredients and recipes."""

from rest_framework.response import Response

from .configuracion import (
    ajustar_existencias, cambiar_estado_ingrediente, crear_ingrediente, crear_mesa,
    guardar_plato,
)
from .disponibilidad import plato_disponible
from .models import Ingrediente, Mesa, Plato
from .serializers import (
    AjusteExistenciasSerializer, ConfigurarPlatoSerializer, CrearIngredienteSerializer,
    CrearMesaSerializer, EstadoIngredienteSerializer,
)
from .views import VistaAdmin, admin_autenticado


def representar_ingrediente(ingrediente):
    return {
        "id": ingrediente.id, "nombre": ingrediente.nombre,
        "cantidad_disponible": str(ingrediente.cantidad_disponible),
        "activo": ingrediente.activo,
    }


def representar_plato(plato):
    return {
        "id": plato.id, "nombre": plato.nombre, "precio": str(plato.precio),
        "activo": plato.activo,
        "disponible": plato_disponible(plato),
        "composicion": [
            {"ingrediente_id": fila.ingrediente_id, "cantidad_requerida": str(fila.cantidad_requerida)}
            for fila in plato.composicion.all()
        ],
    }


def platos_para_configurar():
    return Plato.objects.prefetch_related("composicion__ingrediente").order_by("nombre", "id")


class ConfigMesasView(VistaAdmin):
    def get(self, request):
        admin_autenticado(request)
        return Response([{"id": mesa.id, "numero": mesa.numero} for mesa in Mesa.objects.order_by("numero")])

    def post(self, request):
        admin_autenticado(request)
        datos = CrearMesaSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        mesa = crear_mesa(datos.validated_data["numero"])
        return Response({"id": mesa.id, "numero": mesa.numero}, status=201)


class ConfigIngredientesView(VistaAdmin):
    def get(self, request):
        admin_autenticado(request)
        return Response([
            representar_ingrediente(ingrediente)
            for ingrediente in Ingrediente.objects.order_by("nombre", "id")
        ])

    def post(self, request):
        admin_autenticado(request)
        datos = CrearIngredienteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ingrediente = crear_ingrediente(datos.validated_data)
        return Response(representar_ingrediente(ingrediente), status=201)


class ConfigIngredienteEstadoView(VistaAdmin):
    def patch(self, request, ingrediente_id):
        admin_autenticado(request)
        datos = EstadoIngredienteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ingrediente = cambiar_estado_ingrediente(ingrediente_id, datos.validated_data["activo"])
        return Response(representar_ingrediente(ingrediente))


class ConfigIngredienteAjusteView(VistaAdmin):
    def post(self, request, ingrediente_id):
        admin_autenticado(request)
        datos = AjusteExistenciasSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        ingrediente = ajustar_existencias(ingrediente_id, **datos.validated_data)
        return Response(representar_ingrediente(ingrediente))


class ConfigPlatosView(VistaAdmin):
    def get(self, request):
        admin_autenticado(request)
        return Response([representar_plato(plato) for plato in platos_para_configurar()])

    def post(self, request):
        admin_autenticado(request)
        datos = ConfigurarPlatoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        plato = guardar_plato(datos.validated_data)
        plato = platos_para_configurar().get(pk=plato.pk)
        return Response(representar_plato(plato), status=201)


class ConfigPlatoView(VistaAdmin):
    def put(self, request, plato_id):
        admin_autenticado(request)
        datos = ConfigurarPlatoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        plato = guardar_plato(datos.validated_data, plato_id=plato_id)
        plato = platos_para_configurar().get(pk=plato.pk)
        return Response(representar_plato(plato))
