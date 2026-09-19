# Sala Fogón

Sistema de gestión de pedidos y cocina para la prueba técnica Sistema E. Este primer incremento contiene una API Django REST Framework, una interfaz React/Vite y una comprobación de conexión a PostgreSQL. El flujo de pedidos se implementará en el siguiente incremento.

## Requisitos

- Python 3.13, Node.js 22.12 o posterior, npm y PostgreSQL local.
- Dos terminales PowerShell para ejecutar backend y frontend.

## Preparar PostgreSQL por primera vez

En esta máquina PostgreSQL 18 está instalado y el servicio escucha en el puerto 5432. En otra máquina, instala PostgreSQL y comprueba que el servicio esté activo. Los siguientes comandos **crean** un rol y una base nuevos; si ya existen, reutilízalos sin ejecutar las órdenes `CREATE` de nuevo.

Abre PowerShell y entra a `psql` como administrador. El parámetro `-W` solicita la contraseña en la terminal sin escribirla en el comando:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres -W
```

Dentro de `psql`, comprueba primero los nombres existentes con `\du` y `\l`. Si no existen, crea el usuario, establece su contraseña de forma interactiva y crea la base:

```sql
CREATE ROLE sala_fogon_app LOGIN CREATEDB;
\password sala_fogon_app
CREATE DATABASE sala_fogon OWNER sala_fogon_app;
\q
```

`CREATEDB` permite que el ejecutor de pruebas de Django cree su base temporal. No concedas `SUPERUSER`. Introduce una contraseña propia en el prompt de `\password`; no la pongas en el SQL ni en el chat.

Para comprobar la conexión del usuario, `psql` puede pedir la contraseña otra vez:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -h 127.0.0.1 -U sala_fogon_app -d sala_fogon -W -c 'SELECT current_database(), current_user;'
```

## Backend

Desde la raíz del repositorio:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

La configuración toma los datos de variables de entorno. También carga `backend/.env` para desarrollo local; este archivo está ignorado por Git. Puedes crearlo con un prompt que oculta la contraseña, sin ponerla en el historial ni en el chat:

```powershell
backend\.venv\Scripts\python.exe backend\configure_local.py
backend\.venv\Scripts\python.exe backend\manage.py migrate
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

Si prefieres no guardar la contraseña en un archivo, establece `POSTGRES_PASSWORD` en tu sesión de PowerShell antes de ejecutar Django; las variables de entorno tienen prioridad sobre `backend/.env`. Para una instalación compartida configura también `DJANGO_SECRET_KEY` con un valor privado y desactiva `DJANGO_DEBUG`. La clave incluida en `settings.py` es solo para desarrollo local.

Abre <http://127.0.0.1:8000/api/health/>. Una conexión válida devuelve `{"api":"ok","database":"ok"}`. Si PostgreSQL no responde o faltan credenciales válidas, devuelve HTTP 503 y `database: unavailable`.

## Frontend

En otra terminal, desde la raíz:

```powershell
cd frontend
npm install
npm run dev
```

Abre la dirección mostrada por Vite, normalmente <http://localhost:5173/>. La pantalla debe indicar «API y PostgreSQL conectados». Vite reenvía las peticiones `/api` al backend en `127.0.0.1:8000`; no hay que configurar CORS para este entorno local.

Para comprobar la compilación:

```powershell
cd frontend
npm run build
```

## Organización

- `backend/config/`: configuración Django y comprobación de salud de la API.
- `backend/restaurant/`: aplicación inicial donde se incorporará el primer flujo de restaurante.
- `frontend/src/`: interfaz React.
- `ADR/`, `AGENTS.md` y `ASSUMPTIONS.md`: decisiones y modelo conceptual.

En el siguiente incremento se incorporarán apertura de sesión, catálogo disponible, envío transaccional de pedidos, cola de cocina y avance de ítems. Pagos quedan para una etapa posterior.
