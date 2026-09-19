"""Input validation; database-dependent rules live in services."""

from rest_framework import serializers


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
