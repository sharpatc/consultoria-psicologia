# Docker y despliegue

## Requisitos

- Docker Desktop en Windows/macOS, o Docker Engine y el plugin Compose en Linux.
- Para publicar en internet: un servidor Linux con puertos TCP 80 y 443 disponibles,
  puerto UDP 443 opcionalmente, y un dominio cuyo DNS apunte al servidor.

## Preparar y ejecutar localmente

1. Copia `.env.example` como `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Define `SECRET_KEY` con una cadena aleatoria y `ADMIN_PASSWORD` con una
   contraseña segura de al menos 12 caracteres. `ADMIN_USERNAME` define el usuario
   inicial. Puedes generar `SECRET_KEY` con
   `python -c "import secrets; print(secrets.token_urlsafe(48))"`. No compartas ni
   subas `.env` al repositorio.
3. Inicia el proyecto desde la carpeta raíz:

   ```powershell
   docker compose up --build -d
   ```

4. Abre <http://localhost:3000> y el panel en <http://localhost:3000/admin>.
   La cuenta inicial usa `ADMIN_USERNAME` y `ADMIN_PASSWORD` del primer arranque.

Gunicorn ejecuta la aplicación dentro de un contenedor sin privilegios. El archivo
SQLite reside en el volumen Docker `database`, montado en `/data`; los datos
permanecen tras reiniciar o recrear el contenedor y al ejecutar
`docker compose down`. **No uses `docker compose down -v`**: ese comando elimina
el volumen y sus datos.

El usuario y contraseña iniciales solo se crean si todavía no existe ese usuario.
Si ya hay una base de datos o una cuenta con ese nombre, cambiar las variables de
`.env` no reemplaza su contraseña; inicia sesión y cámbiala desde el panel.

## Confirmaciones y recordatorios por correo

El servicio `reminders` comparte el volumen SQLite persistente de la aplicación y
revisa las citas agendadas cada minuto. Para enviar correos reales, configura en
`.env` `EMAIL_USER`, `EMAIL_PASS`, `SMTP_HOST` y `SMTP_PORT`. Con Gmail, utiliza
una contraseña de aplicación si la cuenta tiene verificación en dos pasos; no
uses ni publiques la contraseña normal de la cuenta. Sin credenciales SMTP, la
cita se guarda y la interfaz informa que el correo no fue enviado.

El recordatorio se envía el mismo día de la cita, desde las 08:00 hora de
`TIMEZONE` (por defecto `America/Panama`), siempre antes de la hora programada.
Si el envío falla, se reintenta hasta cuatro veces, con al menos 15 minutos entre
intentos. Ajusta `APPOINTMENT_REMINDER_HOUR`,
`APPOINTMENT_REMINDER_MAX_ATTEMPTS` y `APPOINTMENT_REMINDER_RETRY_MINUTES` en
`.env` si necesitas otro horario o política de reintentos. Reinicia el worker al
cambiar la configuración:

```powershell
docker compose up -d --force-recreate reminders
```

Comandos útiles:

```powershell
docker compose logs -f app
docker compose logs -f reminders
docker compose ps
docker compose down
docker compose up --build -d
```

## Copias de seguridad de SQLite

La utilidad usa la API de backup de SQLite para crear una copia consistente aunque
la aplicación esté activa. En PowerShell:

```powershell
New-Item -ItemType Directory -Force .\backups | Out-Null
$backup = docker compose exec -T app python scripts/backup_db.py
docker compose cp "app:$backup" .\backups\
```

Guarda la carpeta `backups` fuera del servidor también. Para recuperar una copia,
detén la aplicación, conserva primero una copia actual y reemplaza el nombre de
archivo por la copia que vas a restaurar:

```powershell
docker compose stop app
docker compose run --rm --no-deps --volume "${PWD}/backups:/backups:ro" --entrypoint python app scripts/restore_db.py /backups/consultoria-psicologia-FECHA.sqlite3
docker compose start app
```

El proceso valida la integridad y las tablas principales de la copia, y limpia
los archivos WAL antiguos antes de reemplazar la base.

## Publicar en internet con HTTPS

1. En un servidor Linux instala Docker Engine y Docker Compose. Copia el proyecto
   o clónalo allí, y crea el `.env` con secretos seguros como en los pasos locales.
2. Configura `DOMAIN` con tu dominio y `ACME_EMAIL` con un correo válido en `.env`.
   Crea un registro DNS `A` (y `AAAA` solo si el servidor tiene IPv6 funcional)
   que apunte a la IP pública del servidor.
3. Permite el tráfico entrante TCP 80/443 y, si es posible, UDP 443 en el firewall
   del servidor y del proveedor de alojamiento.
4. En `.env`, cambia `SESSION_COOKIE_SECURE=true` y ejecuta:

   ```bash
   docker compose --profile internet up --build -d
   ```

Caddy obtiene y renueva automáticamente el certificado TLS. El servicio Flask
queda en la red interna de Docker; Caddy es el único servicio publicado en las
interfaces de internet. La aplicación local en el puerto 3000 queda vinculada a
`127.0.0.1` en el servidor. Visita `https://tu-dominio`.

Revisa `docker compose --profile internet logs -f caddy app` si el certificado
no se emite. El DNS público debe resolver al servidor y los puertos 80/443 deben
ser accesibles desde internet.

## Seguridad y persistencia

- En modo producción la app rechaza una clave de sesión corta y una contraseña
  inicial de menos de 12 caracteres.
- Los secretos se inyectan mediante `.env`; no se copian a la imagen Docker.
- La base de datos usa un volumen Docker nombrado y el modo WAL de SQLite.
- Mantén Docker y el sistema operativo actualizados, protege el acceso al servidor
  y conserva copias de seguridad fuera de él. Un volumen persistente no sustituye
  una copia de seguridad.
- El usuario inicial no se debe dejar con una contraseña compartida o temporal.
