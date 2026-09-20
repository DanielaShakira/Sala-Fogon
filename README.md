# Sala&Fogón

Sistema de gestión de pedidos en un restaurante, que optimiza el flujo entre cocineros, meseros, coordina la atención de mesas, la disponibilidad de platos, la preparación y el cobro desde una interfaz para el personal del restaurante.

## Funcionalidades principales

El sistema contempla tres roles:

**Administrador**

* Gestionar empleados y sus estados de actividad.
* Configurar mesas, ingredientes y existencias.
* Administrar el catálogo de platos y sus recetas.

**Mesero**

* Abrir y gestionar sesiones de atención por mesa.
* Consultar el catálogo y enviar pedidos a cocina.
* Consultar el estado de los pedidos y cancelar ítems permitidos.
* Recibir notificaciones cuando los platos estén listos.
* Consultar cuentas, registrar pagos parciales y cerrar sesiones.

**Cocinero**

* Consultar los pedidos pendientes.
* Iniciar la preparación de los ítems.
* Marcar los ítems como listos.

La información compartida se sincroniza automáticamente entre las diferentes sesiones de usuario.

## Tecnologías y requisitos

| Componente    | Tecnología                     |
| ------------- | ------------------------------ |
| Frontend      | React y Vite                   |
| Backend       | Python y Django REST Framework |
| Base de datos | PostgreSQL                     |

Las instrucciones siguientes están probadas en **Windows con PowerShell**. Requieren Python 3.13, Node.js 22.12 o posterior, npm, PostgreSQL y Git para clonar el repositorio. Las dependencias concretas están en `backend/requirements.txt` y `frontend/package.json`.

## Instalación inicial (una sola vez)

1. **Obtener el proyecto:**

   ```powershell
   git clone https://github.com/DanielaShakira/Sala-Fogon.git
   cd Sala-Fogon
   ```

2. **Preparar PostgreSQL.** Comprueba que exista un servicio PostgreSQL activo. En esta instalación se usa PostgreSQL 18; ajusta la ruta de `psql.exe` si tu versión o ubicación es distinta. Entra como administrador de PostgreSQL:

   ```powershell
   & 'C:\Program Files\PostgreSQL\18\bin\psql.exe' -U postgres -d postgres -W
   ```

   Dentro de `psql`, usa `\du` y `\l` para comprobar si ya existen el rol y las bases. Ejecuta solo las instrucciones `CREATE` que falten:

   ```sql
   CREATE ROLE sala_fogon_app LOGIN;
   \password sala_fogon_app
   CREATE DATABASE sala_fogon OWNER sala_fogon_app;
   CREATE DATABASE test_sala_fogon OWNER sala_fogon_app;
   \q
   ```

   `\password` solicita la contraseña sin escribirla en el comando. `sala_fogon` es la base de la aplicación; `test_sala_fogon` es independiente y necesaria para las pruebas Django. No recrees ni borres bases existentes.

3. **Preparar el backend** desde la raíz del repositorio:

Desde la raíz del proyecto:

```powershell
py -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Configurar la conexión local a PostgreSQL mediante el asistente del proyecto:

```powershell
backend\.venv\Scripts\python.exe backend\configure_local.py
```

Aplicar las migraciones:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py migrate
```

Crear el administrador inicial del restaurante:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py crear_administrador
```

Este último comando solicita las credenciales de forma interactiva y solo es necesario cuando todavía no existe una cuenta administradora del restaurante.

4. **Instalar el frontend:**

   ```powershell
   cd frontend
   npm install
   cd ..
   ```

El proyecto no carga mesas, ingredientes ni platos de ejemplo. Al entrar por primera vez, usa la cuenta ADMIN para crear mesas, ingredientes, platos con sus recetas y las cuentas de mesero y cocinero.

## Ejecución local

Una vez configurado el proyecto, no es necesario repetir la instalación cada vez que se utiliza.

Primero, comprobar que el servicio de PostgreSQL se encuentre activo.

**Backend**

Desde la raíz del proyecto, ejecutar en una terminal:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

**Frontend**

En otra terminal, desde la raíz del proyecto:

```powershell
cd frontend
npm run dev
```

Abre la dirección que muestre Vite, normalmente <http://localhost:5173/>. La API se ejecuta en <http://127.0.0.1:8000/>.

## Pruebas

La base `test_sala_fogon` debe existir y pertenecer a `sala_fogon_app`. Desde la raíz:

```powershell
backend\.venv\Scripts\python.exe backend\manage.py test restaurant --keepdb --noinput
backend\.venv\Scripts\python.exe backend\manage.py check
```

Las pruebas Django usan y pueden modificar `test_sala_fogon`, no los datos de `sala_fogon`; reserva esa base exclusivamente para pruebas. Para las pruebas y la compilación React:

```powershell
cd frontend
npm test
npm run build
```

## Rutas de la API

Estas son las rutas implementadas; las rutas operativas usan autenticación y el backend comprueba el rol indicado. `<id>` representa el identificador del recurso. Los contratos de entrada se validan en los serializadores y vistas de `backend/restaurant/`; la lista de rutas vigente está en [backend/config/urls.py](backend/config/urls.py).

| Acceso | Método y ruta | Propósito |
| --- | --- | --- |
| Público | `GET /api/health/` | Comprobar API y base de datos. |
| Personal | `GET /api/me/` | Consultar el perfil autenticado. |
| ADMIN | `GET, POST /api/empleados/`; `PATCH /api/empleados/<id>/` | Consultar, crear y activar o desactivar empleados. |
| ADMIN | `GET, POST /api/configuracion/mesas/` | Consultar y crear mesas. |
| ADMIN | `GET, POST /api/configuracion/ingredientes/` | Consultar y crear ingredientes. |
| ADMIN | `PATCH /api/configuracion/ingredientes/<id>/estado/`; `POST /api/configuracion/ingredientes/<id>/ajustar/` | Cambiar actividad y ajustar existencias. |
| ADMIN | `GET, POST /api/configuracion/platos/`; `PUT /api/configuracion/platos/<id>/` | Consultar, crear y editar platos y recetas. |
| MESERO | `GET /api/mesas/`; `POST /api/sesiones/` | Consultar mesas y abrir sesiones. |
| MESERO | `GET /api/platos/`; `POST /api/pedidos/` | Consultar el catálogo y enviar pedidos. |
| MESERO | `GET /api/mis-pedidos-activos/`; `GET /api/sesiones/<id>/pedidos/` | Consultar pedidos propios. |
| MESERO | `GET /api/sesiones/<id>/cuenta/`; `POST /api/sesiones/<id>/pagos/`; `POST /api/sesiones/<id>/cerrar/` | Consultar la cuenta, registrar pagos y cerrar. |
| MESERO | `POST /api/items/<id>/cancelar/` | Cancelar una unidad permitida. |
| COCINERO | `GET /api/cocina/cola/` | Consultar pedidos pendientes. |
| COCINERO | `POST /api/items/<id>/iniciar/`; `POST /api/items/<id>/listo/` | Avanzar la preparación de una unidad. |

## Documentación complementaria

- [ASSUMPTIONS.md](ASSUMPTIONS.md): supuestos, reglas funcionales y límites del alcance.
- [ADR/](ADR/): decisiones de arquitectura, base de datos, uso de IA y sincronización.
- [BITACORA-IA.md](BITACORA-IA.md): evolución del proyecto, decisiones tomadas y verificaciones realizadas.
- [AGENTS.md](AGENTS.md): modelo conceptual y criterios para futuras intervenciones de IA.
