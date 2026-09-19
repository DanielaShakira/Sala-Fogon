# Sala Fogón

Sistema de gestión de pedidos y cocina para la prueba técnica Sistema E. El repositorio contiene la base Django REST Framework y React/Vite, la conexión con PostgreSQL y el modelo relacional. El flujo operativo de pedidos se implementará en el siguiente incremento.

## Requisitos

- Python 3.13, Node.js 22.12 o posterior, npm y PostgreSQL local.
- Dos terminales PowerShell para ejecutar backend y frontend.

## Preparar PostgreSQL por primera vez

En esta máquina PostgreSQL 18 está instalado y el servicio escucha en el puerto 5432. En otra máquina, instala PostgreSQL y comprueba que el servicio esté activo. Los siguientes comandos **crean** un rol y dos bases nuevas; si ya existen, reutilízalos sin ejecutar las órdenes `CREATE` de nuevo.

Abre PowerShell y entra a `psql` como administrador. El parámetro `-W` solicita la contraseña en la terminal sin escribirla en el comando:

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres -W
```

Dentro de `psql`, comprueba primero los nombres existentes con `\du` y `\l`. Si no existen, crea el usuario, establece su contraseña de forma interactiva y crea la base:

```sql
CREATE ROLE sala_fogon_app LOGIN;
\password sala_fogon_app
CREATE DATABASE sala_fogon OWNER sala_fogon_app;
CREATE DATABASE test_sala_fogon OWNER sala_fogon_app;
\q
```

`test_sala_fogon` es exclusiva para pruebas; `--keepdb` hace que Django reutilice esa base sin requerir `CREATEDB`. No concedas `SUPERUSER`. Introduce una contraseña propia en el prompt de `\password`; no la pongas en el SQL ni en el chat.

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
- `backend/restaurant/`: modelos relacionales del restaurante; la lógica del primer flujo se incorporará después.
- `frontend/src/`: interfaz React.
- `ADR/`, `AGENTS.md` y `ASSUMPTIONS.md`: decisiones y modelo conceptual.

## Modelo de datos

`restaurant/models.py` define las doce entidades del modelo conceptual. Django conserva el nombre y rol del restaurante en `Usuario` y gestiona las credenciales en su modelo `auth.User`, unido uno a uno con `Usuario`. La propiedad `Usuario.activo` lee `auth.User.is_active`, de modo que la actividad no se almacena dos veces. Los campos adicionales de `auth.User`, como `username` y el hash de contraseña, son soporte de autenticación y no representan nuevas entidades del negocio.

Los precios usan `DecimalField(max_digits=12, decimal_places=2)`, para conservar centavos sin errores de coma flotante. Las cantidades abstractas de ingredientes usan `DecimalField(max_digits=12, decimal_places=3)`, que permite milésimas de porción. Esto admite precios de hasta 9.999.999.999,99 y cantidades de hasta 999.999.999,999 por registro. El backend rechaza valores negativos mediante restricciones de base de datos; las recetas y composiciones comprometidas requieren cantidades mayores que cero.

La base limita a una sesión activa por mesa con una unicidad condicionada a `fecha_hora_fin IS NULL`. También garantiza una cuenta por sesión, una asignación de pago por ítem y la unicidad de ingredientes en cada receta o composición de ítem. Los estados de `Sesion`, `Pedido` y `Cuenta` no se almacenan. Las reglas entre registros, como comprobar que el mesero tiene el rol correcto o validar una transición de estado, se incorporarán a la lógica del siguiente flujo.

Para ejecutar las pruebas estructurales sobre `test_sala_fogon`, desde la raíz del repositorio:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py test restaurant --keepdb --noinput
```

Antes de ejecutarlas, comprueba que `test_sala_fogon` existe, está vacía la primera vez y pertenece a `sala_fogon_app`. El comando no usa la base principal `sala_fogon` para los datos de prueba y conserva la base de pruebas al terminar.

En el siguiente incremento se incorporarán apertura de sesión, catálogo disponible, envío transaccional de pedidos, cola de cocina y avance de ítems. El registro operativo de pagos queda para una etapa posterior.
