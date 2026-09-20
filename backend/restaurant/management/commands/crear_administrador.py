"""Create the first operational ADMIN without granting Django superuser powers."""

from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError as APIValidationError

from restaurant.models import Usuario
from restaurant.personal import crear_cuenta_personal


class Command(BaseCommand):
    help = "Crea de forma interactiva la cuenta administradora inicial del restaurante."

    def handle(self, *args, **options):
        if Usuario.objects.filter(rol=Usuario.Rol.ADMIN).exists():
            raise CommandError("Ya existe un perfil ADMIN. Utiliza esa cuenta para gestionar empleados.")

        username = input("Usuario del administrador: ").strip()
        nombre = input("Nombre del administrador: ").strip()
        password = getpass("Contraseña: ")
        confirmacion = getpass("Repetir contraseña: ")
        if password != confirmacion:
            raise CommandError("Las contraseñas no coinciden.")
        if not nombre or len(nombre) > 150:
            raise CommandError("El nombre debe tener entre 1 y 150 caracteres.")
        if not username or len(username) > 150:
            raise CommandError("El usuario debe tener entre 1 y 150 caracteres.")

        try:
            UnicodeUsernameValidator()(username)
            cuenta = get_user_model()(username=username)
            validate_password(password, user=cuenta)
            crear_cuenta_personal(
                username=username, nombre=nombre, password=password, rol=Usuario.Rol.ADMIN
            )
        except (ValidationError, APIValidationError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Cuenta ADMIN creada con su perfil del restaurante."))
