# Sala Fogón

Sistema de gestión de pedidos y cocina para la prueba técnica Sistema E. El repositorio contiene Django REST Framework, React/Vite, PostgreSQL y el modelo relacional. El primer flujo permite a un mesero abrir una sesión de mesa, consultar el catálogo y enviar pedidos a cocina.

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

Abre la dirección mostrada por Vite, normalmente <http://localhost:5173/>. Vite reenvía las peticiones `/api` al backend en `127.0.0.1:8000`; no hay que configurar CORS para este entorno local. La interfaz solicita las credenciales de un mesero, permite elegir una mesa, abrir o retomar su sesión, armar un pedido temporal y enviarlo. La contraseña no se guarda en el repositorio ni en el almacenamiento del navegador; la pestaña mantiene la autorización Basic en memoria hasta salir o recargarla. Usa este flujo únicamente en el entorno local previsto, pues HTTP Basic envía credenciales en cada petición y una instalación compartida requeriría HTTPS.

Para comprobar la compilación:

```powershell
cd frontend
npm run build
```

## Organización

- `backend/config/`: configuración Django y comprobación de salud de la API.
- `backend/restaurant/`: modelos relacionales, validadores de entrada, servicios transaccionales, vistas, administración de datos y pruebas.
- `frontend/src/`: interfaz React.
- `ADR/`, `AGENTS.md` y `ASSUMPTIONS.md`: decisiones y modelo conceptual.

## Modelo de datos

`restaurant/models.py` define las doce entidades del modelo conceptual. Django conserva el nombre y rol del restaurante en `Usuario` y gestiona las credenciales en su modelo `auth.User`, unido uno a uno con `Usuario`. La propiedad `Usuario.activo` lee `auth.User.is_active`, de modo que la actividad no se almacena dos veces. Los campos adicionales de `auth.User`, como `username` y el hash de contraseña, son soporte de autenticación y no representan nuevas entidades del negocio.

Los precios usan `DecimalField(max_digits=12, decimal_places=2)`, para conservar centavos sin errores de coma flotante. Las cantidades abstractas de ingredientes usan `DecimalField(max_digits=12, decimal_places=3)`, que permite milésimas de porción. Esto admite precios de hasta 9.999.999.999,99 y cantidades de hasta 999.999.999,999 por registro. El backend rechaza valores negativos mediante restricciones de base de datos; las recetas y composiciones comprometidas requieren cantidades mayores que cero.

La base limita a una sesión activa por mesa con una unicidad condicionada a `fecha_hora_fin IS NULL`. También garantiza una cuenta por sesión, una asignación de pago por ítem y la unicidad de ingredientes en cada receta o composición de ítem. Los estados de `Sesion`, `Pedido` y `Cuenta` no se almacenan. La apertura y el envío de pedidos validan en el backend el rol y las reglas entre registros. Las transiciones de cocina, cancelaciones y pagos continúan pendientes.

Para ejecutar las pruebas estructurales sobre `test_sala_fogon`, desde la raíz del repositorio:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py test restaurant --keepdb --noinput
```

Antes de ejecutarlas, comprueba que `test_sala_fogon` existe, está vacía la primera vez y pertenece a `sala_fogon_app`. El comando no usa la base principal `sala_fogon` para los datos de prueba y conserva la base de pruebas al terminar.

## Datos iniciales y primer flujo

El sistema no crea mesas, platos, ingredientes ni cuentas de personal automáticamente. Para probarlo desde cero, crea primero un administrador local con `backend\.venv\Scripts\python.exe backend\manage.py createsuperuser` y entra a <http://127.0.0.1:8000/admin/>. En la administración de Django:

1. Crea una cuenta de acceso normal en **Usuarios** con contraseña propia e `is_active` activado; no necesita `is_staff` para trabajar como mesero.
2. Crea su perfil en **Usuarios del restaurante**, vincúlalo a esa cuenta y asigna el rol `MESERO`.
3. Crea una mesa, ingredientes con existencias, y platos activos con su precio y composición. Las cantidades de receta son por **una unidad** de plato; las existencias y recetas admiten tres decimales.

En React, entra con la cuenta del mesero. Una mesa sin sesión activa muestra **Abrir sesión**; una sesión propia activa puede retomarse. Añade unidades enteras de platos disponibles y confirma **Enviar a cocina**. La consulta del catálogo es informativa: el backend vuelve a comprobar los datos actuales al enviar. Si el consumo conjunto excede las existencias o alguna validación falla, no se crea el pedido ni se descuenta ingrediente alguno.

Los endpoints de este flujo son:

| Método y ruta | Función |
| --- | --- |
| `GET /api/me/` | Verificar cuenta Basic y perfil `MESERO` activo. |
| `GET /api/mesas/` | Listar mesas y su sesión activa, si existe. |
| `POST /api/sesiones/` | Abrir sesión y cuenta con `{"mesa_id": 1}`. El mesero se toma de la autenticación. |
| `GET /api/platos/` | Listar platos y disponibilidad calculada desde estado, receta y existencias. |
| `POST /api/pedidos/` | Enviar `{"sesion_id": 1, "observaciones": "", "items": [{"plato_id": 1, "cantidad": 2}]}`. Cada unidad crea un `ItemPedido` en `EN_COLA`. |

Las rutas del flujo requieren HTTP Basic y el rol `MESERO`. Las cantidades de `items` deben ser números enteros JSON mayores que cero y el arreglo no puede estar vacío. Los pedidos solo pueden enviarse a una sesión activa del mesero autenticado. No se ha implementado todavía la consulta de la cola de cocina, el avance o cancelación de ítems ni los pagos.

La prueba `restaurant` usa explícitamente `test_sala_fogon` y reutiliza esa base con `--keepdb`; no escribe datos de prueba en `sala_fogon`. Aún quedan pendientes pruebas automatizadas de navegador y de aperturas o pedidos realmente concurrentes con conexiones independientes.
