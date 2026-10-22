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
- `SECRET_KEY` — clave de firma de los JWT. **Obligatoria y secreta.** Genérela
  con `python -c "import secrets; print(secrets.token_hex(32))"`. Si no se define,
  el backend la genera aleatoriamente en cada reinicio e invalida todos los tokens.
- `CORS_ORIGINS` — dominios del frontend permitidos (coma separada). En desarrollo
  ya está `http://localhost:5173`. En producción, la URL real del frontend.
- `ENVIRONMENT=development|production` — en `production` se desactivan Swagger
  (`/docs`) y ReDoc (`/redoc`).

El archivo `.env` y `.venv/` están en `.gitignore` y no deben commitearse.

## Ejecutar

```bash
.venv\Scripts\activate        # Windows
uvicorn app.main:app --reload
```

La API queda en `http://127.0.0.1:8000`.
Documentación interactiva (Swagger) en `http://127.0.0.1:8000/docs` (solo desarrollo).

## Endpoints principales

- `POST /auth/login` — login con `usuario`, `documento`, `password`. Devuelve un token.
- `GET /auth/me` — datos básicos del usuario logueado.
- `GET /usuario/perfil` — perfil completo del usuario logueado.
- `PUT /usuario/perfil` — actualizar nombre, apellido, teléfono, email.
- `PUT /usuario/password` — cambiar contraseña.
- `GET /empresa/perfil` — datos de la empresa del usuario logueado.
- `GET /archivos/mios` — archivos propios del usuario.
- `GET /archivos/empresa` — archivos de toda la empresa.
- `GET /reportes/*` — reportes de compras, ventas, movimientos y herramientas.

Todos los endpoints (salvo `/auth/login`) requieren el header:
`Authorization: Bearer <token>`.

## Notas importantes

- La tabla `usuarios` es la misma que usa el software de escritorio
  (columnas `usuario`, `documento`, `password`). El login valida contra
  esas mismas columnas, así el cliente entra con las mismas credenciales
  que ya usa en la computadora.
- Las contraseñas se guardan en la columna `password` tal como las guarda el
  software de escritorio (hoy en texto plano en la base). El login valida
  contra la misma columna y soporta tanto texto plano como hashes **bcrypt**
  (prefijo `$2`, lo que genera `hashear_password` de passlib). Para
  endurecer el acceso es recomendable migrar los hashes a bcrypt; mientras
  tanto NO debe deshabilitarse la comparación en texto plano o los usuarios
  existentes no podrán ingresar.
- MySQL se conecta en el modo permisivo del ERP original (sin
  `ONLY_FULL_GROUP_BY`): los reportes traducidos del `INFORMES-ORIGINAL.prg`
  seleccionan columnas que no están en el `GROUP BY` y solo funcionan en ese
  modo. No forzar `ONLY_FULL_GROUP_BY` en la sesión.
