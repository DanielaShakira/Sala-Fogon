from django.contrib import admin
from django.urls import path

from .views import HealthView
from restaurant.views import MesasView, MiPerfilView, PedidosView, PlatosView, SesionesView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", HealthView.as_view(), name="health"),
    path("api/me/", MiPerfilView.as_view(), name="me"),
    path("api/mesas/", MesasView.as_view(), name="mesas"),
    path("api/sesiones/", SesionesView.as_view(), name="sesiones"),
    path("api/platos/", PlatosView.as_view(), name="platos"),
    path("api/pedidos/", PedidosView.as_view(), name="pedidos"),
]
