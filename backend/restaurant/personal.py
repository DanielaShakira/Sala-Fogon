"""Creation and activation of restaurant staff accounts."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from rest_framework.exceptions import NotFound, ValidationError

from .models import Sesion, Usuario
from .services import Conflicto


def crear_cuenta_personal(*, username, nombre, password, rol):
    """Credentials and restaurant profile must either both exist or neither exist."""
    try:
        with transaction.atomic():
            cuenta = get_user_model().objects.create_user(
                username=username, password=password, is_active=True,
                is_staff=False, is_superuser=False,
            )
            return Usuario.objects.create(cuenta_acceso=cuenta, nombre=nombre, rol=rol)
    except IntegrityError as exc:
        if get_user_model().objects.filter(username=username).exists():
            raise ValidationError({"username": "Ya existe una cuenta con ese usuario."}) from exc
        raise


def cambiar_estado_empleado(empleado_id, activo):
    with transaction.atomic():
        # Session opening takes this same profile lock before creating a session.
        empleado = Usuario.objects.select_for_update().filter(
            pk=empleado_id, rol__in=(Usuario.Rol.MESERO, Usuario.Rol.COCINERO)
        ).first()
        if empleado is None:
            raise NotFound("El empleado no existe.")
        if not activo and empleado.rol == Usuario.Rol.MESERO and Sesion.objects.filter(
            mesero=empleado, fecha_hora_fin__isnull=True
        ).exists():
            raise Conflicto("El mesero tiene sesiones abiertas; debe cerrarlas antes de desactivar su cuenta.")
        cuenta = empleado.cuenta_acceso
        if cuenta.is_active != activo:
            cuenta.is_active = activo
            cuenta.save(update_fields=["is_active"])
        return empleado
