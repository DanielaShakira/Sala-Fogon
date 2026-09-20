from django.contrib import admin
from django.urls import path

from .views import HealthView
from restaurant.configuracion_views import (
    ConfigIngredienteAjusteView, ConfigIngredienteEstadoView, ConfigIngredientesView,
    ConfigMesasView, ConfigPlatoView, ConfigPlatosView,
)
from restaurant.views import (
    CancelarItemView,
    ColaCocinaView,
    CuentaSesionView,
    CerrarSesionView,
    EmpleadoView,
    EmpleadosView,
    IniciarItemView,
    ListoItemView,
    MesasView,
    MiPerfilView,
    MisPedidosActivosView,
    PedidosSesionView,
    PedidosView,
    PagosSesionView,
    PlatosView,
    SesionesView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/me/", MiPerfilView.as_view(), name="me"),
    path("api/empleados/", EmpleadosView.as_view(), name="empleados"),
    path("api/empleados/<int:empleado_id>/", EmpleadoView.as_view(), name="empleado"),
    path("api/configuracion/mesas/", ConfigMesasView.as_view(), name="config-mesas"),
    path("api/configuracion/ingredientes/", ConfigIngredientesView.as_view(), name="config-ingredientes"),
    path("api/configuracion/ingredientes/<int:ingrediente_id>/estado/", ConfigIngredienteEstadoView.as_view(), name="config-ingrediente-estado"),
    path("api/configuracion/ingredientes/<int:ingrediente_id>/ajustar/", ConfigIngredienteAjusteView.as_view(), name="config-ingrediente-ajustar"),
    path("api/configuracion/platos/", ConfigPlatosView.as_view(), name="config-platos"),
    path("api/configuracion/platos/<int:plato_id>/", ConfigPlatoView.as_view(), name="config-plato"),
    path("api/mesas/", MesasView.as_view(), name="mesas"),
    path("api/sesiones/", SesionesView.as_view(), name="sesiones"),
    path("api/platos/", PlatosView.as_view(), name="platos"),
    path("api/pedidos/", PedidosView.as_view(), name="pedidos"),
    path("api/mis-pedidos-activos/", MisPedidosActivosView.as_view(), name="mis-pedidos-activos"),
    path("api/sesiones/<int:sesion_id>/pedidos/", PedidosSesionView.as_view(), name="pedidos-sesion"),
    path("api/sesiones/<int:sesion_id>/cuenta/", CuentaSesionView.as_view(), name="cuenta-sesion"),
    path("api/sesiones/<int:sesion_id>/pagos/", PagosSesionView.as_view(), name="pagos-sesion"),
    path("api/sesiones/<int:sesion_id>/cerrar/", CerrarSesionView.as_view(), name="cerrar-sesion"),
    path("api/cocina/cola/", ColaCocinaView.as_view(), name="cola-cocina"),
    path("api/items/<int:item_id>/iniciar/", IniciarItemView.as_view(), name="iniciar-item"),
    path("api/items/<int:item_id>/listo/", ListoItemView.as_view(), name="listo-item"),
    path("api/items/<int:item_id>/cancelar/", CancelarItemView.as_view(), name="cancelar-item"),
]
