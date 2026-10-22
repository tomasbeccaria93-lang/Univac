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

docs_url = "/docs" if settings.ENVIRONMENT == "development" else None
redoc_url = "/redoc" if settings.ENVIRONMENT == "development" else None

app = FastAPI(
    title="Sistema Multi Empresa",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
)

app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


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
