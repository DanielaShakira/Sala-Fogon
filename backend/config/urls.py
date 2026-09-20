from django.contrib import admin
from django.urls import path

from .views import HealthView
from restaurant.views import (
    CancelarItemView,
    ColaCocinaView,
    IniciarItemView,
    ListoItemView,
    MesasView,
    MiPerfilView,
    PedidosSesionView,
    PedidosView,
    PlatosView,
    SesionesView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/me/", MiPerfilView.as_view(), name="me"),
    path("api/mesas/", MesasView.as_view(), name="mesas"),
    path("api/sesiones/", SesionesView.as_view(), name="sesiones"),
    path("api/platos/", PlatosView.as_view(), name="platos"),
    path("api/pedidos/", PedidosView.as_view(), name="pedidos"),
    path("api/sesiones/<int:sesion_id>/pedidos/", PedidosSesionView.as_view(), name="pedidos-sesion"),
    path("api/cocina/cola/", ColaCocinaView.as_view(), name="cola-cocina"),
    path("api/items/<int:item_id>/iniciar/", IniciarItemView.as_view(), name="iniciar-item"),
    path("api/items/<int:item_id>/listo/", ListoItemView.as_view(), name="listo-item"),
    path("api/items/<int:item_id>/cancelar/", CancelarItemView.as_view(), name="cancelar-item"),
]
