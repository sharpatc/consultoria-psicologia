# PsicoEmocional - Sistema Web y Panel Administrativo

Plataforma web integral para consultoría psicológica, con sitio público para pacientes (información, servicios, tarjeta digital 3D interactiva y formulario de contacto/agendamiento) y un panel administrativo completo para la gestión de citas, pacientes y usuarios con roles.

El panel incluye evaluaciones psicológicas infantiles/adolescentes y un historial de atenciones editable. Estas fichas contienen datos clínicos sensibles: las rutas requieren una cuenta con rol de administrador y los datos se guardan en SQLite sin cifrado de aplicación. Restringe el acceso a la base de datos y sus copias de seguridad; no uses datos reales hasta definir y aplicar las medidas de protección exigidas para tu entorno.

Para ejecutar con Docker, conservar SQLite en un volumen persistente y desplegar
con HTTPS, consulta la [guía de Docker](./README.Docker.md).

---

## 🏛️ Análisis y Mejora de Arquitectura

### Situación Anterior (Monolito)
- **Archivo único monolítico (`app.py`)**: Más de 500 líneas donde confluían configuración, esquemas SQL, migraciones ad-hoc, lógica de negocio, validaciones, decoradores de autenticación, controladores HTTP, generación de HTML para correos y llamadas SMTP directas.
- **Acoplamiento fuerte**: Modificar un detalle del correo o una consulta a la base de datos implicaba tocar todo el servidor.
- **Plantillas en código duro**: El correo electrónico de confirmación era un string HTML concatenado dentro de una ruta.
- **Sin capa de abstracción de datos**: Consultas SQL manuales repartidas en múltiples funciones sin un patrón de repositorio ni manejo robusto de conexiones.

### Nueva Arquitectura Modular (Capas y Application Factory)
La nueva arquitectura implementa las mejores prácticas recomendadas por la comunidad de Python y Flask:

1. **Patrón Application Factory (`create_app`)**: Permite instanciar la aplicación con diferentes configuraciones (Desarrollo, Producción, Pruebas) y facilita las pruebas automatizadas.
2. **Capa de Presentación / Rutas (Blueprints)**:
   - `auth_routes`: Autenticación (`/api/login`, `/api/logout`, `/api/check-auth`).
   - `appointment_routes`: Gestión de citas y mensajes de contacto (`/api/contact`, `/api/messages`, etc.).
   - `dashboard_routes`: Métricas y estadísticas del consultorio (`/api/dashboard/stats`).
   - `user_routes`: Gestión de administradores, visualizadores y perfiles (`/api/users`, `/api/profile`).
   - `clinical_routes`: Evaluaciones infantiles/adolescentes e historial de atenciones, con acceso exclusivo de administradores (`/api/clinical`).
   - `static_routes`: Servidor seguro de páginas públicas y estáticas.
3. **Capa de Servicios (Lógica de Negocio)**:
   - `AuthService`: Hashing seguro (Werkzeug pbkdf2:sha256), verificación de credenciales y gestión de sesiones.
   - `EmailService`: Renderizado de plantillas HTML y despacho de correos SMTP con modo de simulación automático en desarrollo.
4. **Capa de Acceso a Datos (Patrón Repositorio)**:
   - `UserRepository`, `MessageRepository` y `ClinicalRepository`: Consultas SQL parametrizadas, persistencia de evaluaciones y sesiones, e integridad referencial.
5. **Capa de Base de Datos y Migraciones**:
   - `schema.sql`: Definición declarativa de tablas e índices (`users`, `messages`, `clinical_evaluations`, `clinical_sessions`).
   - `migrations.py`: Inicialización automática e idempotente (agrega columnas si es necesario sin perder datos).
   - `connection.py`: Administrador de conexiones con context managers para commit/rollback automático.
6. **Capa de Middleware y Seguridad**:
   - Decoradores `@login_required` y `@admin_required`.
   - Sanitización contra XSS (`sanitize`, `sanitize_input`) y validación de correo (`is_valid_email`).
7. **Plantillas Jinja2 Limpias**:
   - `templates/emails/appointment_confirmation.html`: Plantilla HTML responsive y profesional, desacoplada del código Python.

---

## 📁 Estructura del Proyecto

```text
consultoria-psicologia-main/
│
├── backend/                              # Núcleo modular de la aplicación Flask
│   ├── __init__.py                       # Application Factory (create_app)
│   ├── config.py                         # Configuraciones (Dev, Prod, Test) y .env
│   ├── database/                         # Persistencia y base de datos
│   │   ├── __init__.py
│   │   ├── connection.py                 # Gestor de conexiones SQLite
│   │   ├── migrations.py                 # Migraciones y seeding de usuario inicial
│   │   └── schema.sql                    # Definición declarativa del esquema SQL
│   ├── models/                           # Capa de Acceso a Datos (Repositorios)
│   │   ├── __init__.py
│   │   ├── clinical_repository.py        # Evaluaciones y atenciones (solo administración)
│   ├── message_repository.py         # Repositorio de mensajes y citas
│   │   └── user_repository.py            # Repositorio de usuarios y permisos
│   ├── services/                         # Lógica de Negocio
│   │   ├── __init__.py
│   │   ├── auth_service.py               # Servicio de autenticación y credenciales
│   │   └── email_service.py              # Servicio de envío de correos
│   ├── routes/                           # Controladores HTTP (Blueprints)
│   │   ├── __init__.py                   # Registro central de rutas
│   │   ├── appointment_routes.py         # Endpoints de citas y contacto
│   ├── clinical_routes.py            # Endpoints protegidos de fichas y atenciones
│   │   ├── auth_routes.py                # Endpoints de login y sesión
│   │   ├── dashboard_routes.py           # Endpoints de estadísticas
│   │   ├── static_routes.py              # Servidor de archivos estáticos y páginas
│   │   └── user_routes.py                # Endpoints de usuarios y perfil
│   ├── middlewares/                      # Middleware y decoradores
│   │   ├── __init__.py
│   │   └── auth_middleware.py            # @login_required, @admin_required
│   ├── utils/                            # Utilidades transversales
│   │   ├── __init__.py
│   │   └── validators.py                 # Sanitización y validaciones regex
│   └── templates/                        # Plantillas de correo (Jinja2)
│       └── emails/
│           └── appointment_confirmation.html # Plantilla de confirmación de cita
│
├── admin/                                # Interfaz Web del Panel de Administración
│   ├── css/
│   │   └── admin.css                     # Estilos modernos del dashboard
│   ├── js/
│   │   └── script.js                     # Lógica cliente del panel (SPA dinámica)
│   ├── index.html                        # Dashboard principal
│   └── login.html                        # Página de inicio de sesión administrativo
│
├── css/                                  # Estilos del Sitio Web Público
│   └── style.css
├── js/                                   # Scripts del Sitio Web Público
│   └── script.js
├── tests/                                # Suite de Pruebas Automatizadas
│   ├── __init__.py
│   └── test_api.py                       # Pruebas unitarias y de integración
│
├── .env.example                          # Plantilla de variables de entorno
├── .gitignore                            # Exclusiones de Git
├── app.py                                # Punto de entrada WSGI (gunicorn / python)
├── database.sqlite                       # Base de datos SQLite
├── index.html                            # Página web pública del consultorio
├── Procfile                              # Configuración de despliegue (Heroku/Render)
└── requirements.txt                      # Dependencias de Python
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Requisitos Previos
- Python 3.10 o superior instalado en el sistema.

### 2. Clonar o Ubicarse en el Directorio
```bash
cd consultoria-psicologia-main
```

### 3. Crear y Activar un Entorno Virtual
En Windows:
```powershell
python -m venv .venv
.venv\Scripts\activate
```

En Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Instalar Dependencias
```bash
pip install -r requirements.txt
```

### 5. Configurar Variables de Entorno (Opcional)
Copia el archivo `.env.example` como `.env`:
```bash
cp .env.example .env
```
Si no configuras las credenciales SMTP de correo (`EMAIL_USER`, `EMAIL_PASS`), el sistema funcionará automáticamente en **modo simulación**, imprimiendo los correos formateados en la terminal.

### 6. Iniciar la Aplicación
```bash
python app.py
```
El servidor arrancará en: **http://localhost:3000**
- Sitio web público: `http://localhost:3000/`
- Panel administrativo: `http://localhost:3000/admin`

> **Solo para ejecución local sin Docker**, las credenciales de administrador iniciales son:
> - **Usuario**: `admin`
> - **Contraseña**: `admin123`
>
> Docker requiere configurar `ADMIN_USERNAME` y `ADMIN_PASSWORD` en `.env`; no usa
> las credenciales de desarrollo.

---

## 🧪 Pruebas Automatizadas

El proyecto incluye pruebas de integración y validaciones con `unittest`:
```bash
python -m unittest discover tests
```

---

## 🔌 Referencia de Endpoints API

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/contact` | Público | Envío de formulario de consulta desde la web |
| `POST` | `/api/login` | Público | Inicio de sesión administrativo |
| `POST` | `/api/logout` | Sesión | Cierre de sesión y limpieza de cookies |
| `GET` | `/api/check-auth` | Público | Consulta el estado y rol de la sesión actual |
| `GET` | `/api/dashboard/stats` | `@login_required` | Métricas y estadísticas de citas y pacientes |
| `GET` | `/api/messages` | `@login_required` | Listado completo de consultas y solicitudes |
| `POST` | `/api/messages/<id>/schedule` | `@login_required` | Agendar cita y enviar correo de confirmación |
| `POST` | `/api/messages/<id>/cancel` | `@login_required` | Cancelar cita agendada |
| `GET` | `/api/users` | `@login_required` | Listado de usuarios del panel |
| `POST` | `/api/users` | `@admin_required` | Crear nuevo usuario (admin o viewer) |
| `DELETE`| `/api/users/<id>` | `@admin_required` | Eliminar usuario (protege al último admin) |
| `PUT` | `/api/profile` | `@login_required` | Actualizar nombre y correo personal |
| `PUT` | `/api/profile/password` | `@login_required` | Cambio de contraseña |

---

## 🛡️ Seguridad Implementada
- **Protección contra Inyecciones SQL**: Todas las consultas utilizan parámetros vinculados (`?`).
- **Protección XSS**: Sanitización de strings en todos los puntos de entrada mediante `html.escape`.
- **Criptografía de Contraseñas**: PBKDF2 con sal individual gestionado por Werkzeug Security.
- **Control de Acceso Basado en Roles (RBAC)**: Distinción estricta entre rol `admin` y `viewer`.
- **Cookies de Sesión Seguras**: Flags `HttpOnly` y `SameSite=Lax` para prevenir robo de sesión.
