# Backend - Sistema Multi Empresa

API en FastAPI que permite a los clientes autenticarse (usuario + N° de
documento + contraseña) y ver sus propios datos en la base de datos:
perfil, datos de su empresa y sus archivos.

## Instalación

```bash
cd web2.0
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

pip install -r requirements.txt
```

## Configuración

No se incluye ningún `.env` con credenciales reales en el repositorio.
Copie la plantilla y complete los valores:

```bash
cp .env-plantilla .env   # Windows: Copy-Item .env-plantilla .env
```

Variables principales:
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` — conexión MySQL.
- `DB_SSL_ENABLED` / `DB_SSL_CA` — habilitan TLS y apuntan al certificado CA
  (por ejemplo `certs/azure-mysql-ca-bundle.pem`). Obligatorio para Azure
  Database for MySQL.
- `SECRET_KEY` — clave de firma de los JWT. **Obligatoria, secreta y de al menos
  32 caracteres.** Genérela con
  `python -c "import secrets; print(secrets.token_hex(32))"`. El backend no
  arranca si falta o si usa un valor de ejemplo.
- `CORS_ORIGINS` — dominios del frontend permitidos (coma separada). En desarrollo
  ya está `http://localhost:5173`. En producción, la URL real del frontend.
- `ENVIRONMENT=development|production` — el valor por defecto es `production`.
  En `production` se desactivan Swagger (`/docs`), ReDoc (`/redoc`) y
  `/openapi.json`, se exige HSTS y no se permite CORS hacia localhost.
- `COOKIE_NAME`, `COOKIE_SAMESITE`, `COOKIE_SECURE`, `COOKIE_DOMAIN` — sesión
  en cookie HttpOnly. En local (HTTP) use `COOKIE_SAMESITE=lax` y
  `COOKIE_SECURE=false`; en producción HTTPS use `COOKIE_SECURE=true`.
  Si el frontend y la API están en el mismo dominio registrable (por ejemplo
  `app.tu-dominio.com` y `api.tu-dominio.com`), `lax` alcanza. Si están en
  sitios distintos, use `COOKIE_SAMESITE=none` (exige HTTPS); algunos
  navegadores bloquean cookies de terceros, por lo que se recomienda el
  esquema de subdominios.
- `SECURITY_STORE_PATH` — archivo SQLite local donde se guardan revocaciones,
  invalidaciones por cambio de contraseña, rate limits y códigos de selección.
  No se guarda en MySQL ni se commitea.
- `REPORT_RATE_LIMIT_PER_MINUTE` / `REPORT_MAX_CONCURRENT` — cupo de consultas
  de reportes por usuario/IP y cantidad de reportes concurrentes.

El archivo `.env` y `.venv/` están en `.gitignore` y no deben commitearse.

## Ejecutar

```bash
.venv\Scripts\activate        # Windows
uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000`.
Documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs` (solo desarrollo).

En producción detrás de Nginx/Render/Vercel, arranque Uvicorn con
`--proxy-headers --forwarded-allow-ips=<IP_DEL_PROXY>` para que los límites de
intentos usen la IP real del cliente y no la del proxy.

## Endpoints principales

- `POST /auth/login` — login con `usuario`, `documento`, `password`. Devuelve
  los datos de sesión y un `csrf_token`; la sesión viaja en cookie HttpOnly.
- `POST /auth/seleccionar-empresa` — consume un código opaco de un solo uso
  cuando el usuario tiene varias empresas.
- `POST /auth/logout` — revoca la sesión y borra la cookie.
- `GET /auth/me` — datos básicos del usuario logueado y `csrf_token` actual.
- `GET /usuario/perfil` — perfil completo del usuario logueado.
- `PUT /usuario/perfil` — actualizar nombre, apellido, teléfono, email.
- `PUT /usuario/password` — cambiar contraseña.
- `GET /empresa/perfil` — datos de la empresa del usuario logueado.
- `GET /archivos/mios` — archivos propios del usuario.
- `GET /archivos/empresa` — archivos de toda la empresa.
- `GET /reportes/*` — reportes de compras, ventas, movimientos y herramientas.

Todos los endpoints (salvo `/auth/login` y `/auth/seleccionar-empresa`)
requieren la cookie de sesión. En peticiones que modifican datos (`POST`,
`PUT`, `PATCH`, `DELETE`) el frontend debe enviar además el header
`X-CSRF-Token` con el valor recibido en el login o en `/auth/me`.

## Contraseñas

El login web mantiene compatibilidad con el ERP de escritorio:
- Si `usuarios.password` empieza con `$2`, valida el hash bcrypt.
- Si no, compara en tiempo constante contra el texto plano guardado.

La migración a bcrypt es **opcional** y no se ejecuta automáticamente. Si se
decide hacerla, primero simular y luego aplicar con autorización explícita:

```bash
# Simulación: solo cuenta filas, no escribe nada
python -m scripts.migrar_passwords_bcrypt

# Aplica el cambio (modifica MySQL; requiere autorización)
python -m scripts.migrar_passwords_bcrypt --apply
```

Si el software de escritorio sigue leyendo texto plano, migrar la base deja las
dos puntas inconsistentes: debe actualizarse el escritorio antes o después.

## Notas importantes

- La tabla `usuarios` es la misma que usa el software de escritorio
  (columnas `usuario`, `documento`, `password`). El login valida contra
  esas mismas columnas.
- Los reportes aplican en el servidor el permiso `visualiza_totales`: si está
  apagado, la API devuelve los importes y el CUIT en `null`.
- El parámetro `estado` de reportes solo acepta `0` o `1`; los nombres de tabla
  y columna salen de una lista blanca.
- MySQL se conecta en el modo permisivo del ERP original (sin
  `ONLY_FULL_GROUP_BY`): los reportes traducidos del `INFORMES-ORIGINAL.prg`
  seleccionan columnas que no están en el `GROUP BY` y solo funcionan en ese
  modo. No forzar `ONLY_FULL_GROUP_BY` en la sesión.
