"""Ask for the local database password without putting it in shell history."""

from getpass import getpass
from pathlib import Path

from dotenv import set_key


def main():
    password = getpass("Contraseña de sala_fogon_app: ")
    if not password:
        raise SystemExit("No se guardó una contraseña vacía.")

    env_file = Path(__file__).resolve().parent / ".env"
    set_key(env_file, "POSTGRES_DB", "sala_fogon")
    set_key(env_file, "POSTGRES_USER", "sala_fogon_app")
    set_key(env_file, "POSTGRES_HOST", "127.0.0.1")
    set_key(env_file, "POSTGRES_PORT", "5432")
    set_key(env_file, "POSTGRES_PASSWORD", password, quote_mode="always")
    print("Configuración local guardada en backend/.env (ignorado por Git).")


if __name__ == "__main__":
    main()
