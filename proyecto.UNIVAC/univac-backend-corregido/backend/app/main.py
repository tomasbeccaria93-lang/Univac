import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routers import auth, usuarios, empresas, archivos, reportes

logging.basicConfig(
    level=logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
logger = logging.getLogger("univac")

docs_habilitados = settings.EXPOSE_OPENAPI
docs_url = "/docs" if docs_habilitados else None
redoc_url = "/redoc" if docs_habilitados else None
openapi_url = "/openapi.json" if docs_habilitados else None

app = FastAPI(
    title="Sistema Multi Empresa",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
    max_age=600,
)

_RUTAS_DOCS = {"/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def cabeceras_seguridad(request: Request, call_next):
    respuesta = await call_next(request)

    respuesta.headers["X-Content-Type-Options"] = "nosniff"
    respuesta.headers["X-Frame-Options"] = "DENY"
    respuesta.headers["Referrer-Policy"] = "no-referrer"
    respuesta.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )
    respuesta.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    respuesta.headers["Cross-Origin-Resource-Policy"] = "same-site"
    respuesta.headers["X-XSS-Protection"] = "0"

    if request.url.path in _RUTAS_DOCS:
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "frame-ancestors 'none'; base-uri 'self'"
        )
    else:
        respuesta.headers["Content-Security-Policy"] = (
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
        )

    if request.url.path.startswith("/auth"):
        respuesta.headers["Cache-Control"] = "no-store"
        respuesta.headers["Pragma"] = "no-cache"

    if settings.ENVIRONMENT == "production":
        respuesta.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )

    return respuesta


@app.exception_handler(Exception)
async def manejador_errores_no_controlados(request: Request, exc: Exception):
    logger.exception(
        "Error no controlado en %s %s",
        request.method,
        request.url.path
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Ocurrió un error interno. Intente nuevamente."
        }
    )


app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(empresas.router)
app.include_router(archivos.router)
app.include_router(reportes.router)


@app.get("/")
def inicio():
    return {
        "estado": "ok",
        "mensaje": "Backend funcionando"
    }
