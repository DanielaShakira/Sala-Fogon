"""Input validation; database-dependent rules live in services."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Usuario


class EnteroPositivoEstricto(serializers.IntegerField):
    def run_validation(self, data=serializers.empty):
        # DRF's IntegerField also accepts strings and floats; units must be JSON integers.
        if data is not serializers.empty and type(data) is not int:
            raise serializers.ValidationError("Debe ser un número entero positivo.")
        return super().run_validation(data)


class AperturaSesionSerializer(serializers.Serializer):
    mesa_id = EnteroPositivoEstricto(min_value=1)


class UnidadSolicitadaSerializer(serializers.Serializer):
    plato_id = EnteroPositivoEstricto(min_value=1)
    cantidad = EnteroPositivoEstricto(min_value=1)


class EnvioPedidoSerializer(serializers.Serializer):
    sesion_id = EnteroPositivoEstricto(min_value=1)
    observaciones = serializers.CharField(required=False, allow_blank=True, default="")
    items = UnidadSolicitadaSerializer(many=True, allow_empty=False)


class RegistroPagoSerializer(serializers.Serializer):
    item_ids = serializers.ListField(
        child=EnteroPositivoEstricto(min_value=1, max_value=9223372036854775807),
        allow_empty=False,
    )

    def validate_item_ids(self, item_ids):
        if len(item_ids) != len(set(item_ids)):
            raise serializers.ValidationError("No se puede incluir dos veces el mismo ítem.")
        return item_ids


class CamposConocidosSerializer(serializers.Serializer):
    """Reject privilege fields instead of silently ignoring unknown input."""

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("Se espera un objeto JSON.")
        desconocidos = set(data) - set(self.fields)
        if desconocidos:
            raise serializers.ValidationError({
                campo: "Este campo no está permitido." for campo in sorted(desconocidos)
            })
        return super().to_internal_value(data)


class NuevoEmpleadoSerializer(CamposConocidosSerializer):
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    nombre = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    rol = serializers.ChoiceField(choices=(Usuario.Rol.MESERO, Usuario.Rol.COCINERO))

    def validate_username(self, username):
        if get_user_model().objects.filter(username=username).exists():
            raise serializers.ValidationError("Ya existe una cuenta con ese usuario.")
        return username

    def validate(self, datos):
        usuario = get_user_model()(username=datos["username"])
        try:
            validate_password(datos["password"], user=usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return datos


class EstadoEmpleadoSerializer(CamposConocidosSerializer):
    activo = serializers.BooleanField()
