from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
import os

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def _requerido(nombre: str, valor: str | None) -> str:
    """Devuelve el valor de una variable obligatoria o aborta el arranque."""
    limpio = (valor or "").strip()
    if not limpio:
        raise RuntimeError(
            f"{nombre} no está configurado. "
            f"Defina {nombre} en el archivo .env (o como variable de entorno) "
            f"antes de arrancar el backend."
        )
    return limpio


def _booleano(nombre: str, valor: str | None, defecto: bool = False) -> bool:
    """Interpreta una variable de entorno booleana."""
    limpio = (valor or "").strip().lower()
    if not limpio:
        return defecto
    if limpio in {"1", "true", "yes", "si", "sí", "on"}:
        return True
    if limpio in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(
        f"{nombre} debe ser un booleano (true/false). Valor recibido: {valor!r}"
    )


class Settings:
    PROJECT_NAME = "Sistema Multi-Empresa"

    # --- Base de datos -----------------------------------------------------
    # DATABASE_URL tiene prioridad; si no se define se arma con las partes.
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or None

    DB_HOST = os.getenv("DB_HOST", "").strip()
    DB_PORT = os.getenv("DB_PORT", "").strip()
    DB_NAME = os.getenv("DB_NAME", "").strip()
    DB_USER = os.getenv("DB_USER", "").strip()
    DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()

    # --- SSL / TLS ---------------------------------------------------------
    # Azure MySQL exige TLS. DB_SSL_CA puede ser una ruta absoluta o relativa
    # a la carpeta del backend (ej. certs/azure-mysql-ca-bundle.pem).
    DB_SSL_CA = os.getenv("DB_SSL_CA", "").strip()
    DB_SSL_ENABLED = _booleano(
        "DB_SSL_ENABLED",
        os.getenv("DB_SSL_ENABLED"),
        defecto=bool(DB_SSL_CA),
    )

    # En produccion el valor por defecto es el seguro: si un deploy olvida
    # definir ENVIRONMENT, no se publican /docs ni /redoc.
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production").strip().lower()
    if ENVIRONMENT not in {"development", "production"}:
        raise RuntimeError(
            "ENVIRONMENT debe ser 'development' o 'production'."
        )

    # --- Seguridad ---------------------------------------------------------
    SECRET_KEY = _requerido("SECRET_KEY", os.getenv("SECRET_KEY"))
    if len(SECRET_KEY) < 32 or SECRET_KEY in {
        "change-this-to-a-random-64-char-hex-string",
        "changeme",
        "secret",
    }:
        raise RuntimeError(
            "SECRET_KEY es demasiado corta o usa un valor de ejemplo. "
            "Genere una clave con: python -c \"import secrets; "
            "print(secrets.token_hex(32))\"."
        )
    ALGORITHM = "HS256"

    try:
        ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120").strip() or "120"
        )
    except ValueError:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un numero entero."
        )
    if ACCESS_TOKEN_EXPIRE_MINUTES < 1 or ACCESS_TOKEN_EXPIRE_MINUTES > 24 * 60:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe estar entre 1 y 1440."
        )

    # --- Cookies / CSRF ----------------------------------------------------
    COOKIE_NAME = os.getenv("COOKIE_NAME", "univac_session").strip() or "univac_session"
    _samesite = os.getenv("COOKIE_SAMESITE", "lax").strip().lower()
    if _samesite not in {"lax", "strict", "none"}:
        raise RuntimeError("COOKIE_SAMESITE debe ser lax, strict o none.")
    COOKIE_SAMESITE = _samesite
    COOKIE_SECURE = _booleano(
        "COOKIE_SECURE",
        os.getenv("COOKIE_SECURE"),
        defecto=(ENVIRONMENT == "production"),
    )
    if COOKIE_SAMESITE == "none" and not COOKIE_SECURE:
        raise RuntimeError(
            "COOKIE_SAMESITE=none exige COOKIE_SECURE=true."
        )
    if ENVIRONMENT == "production" and not COOKIE_SECURE:
        raise RuntimeError(
            "En producción COOKIE_SECURE debe ser true (la sesión viaja por HTTPS)."
        )
    COOKIE_DOMAIN = os.getenv("COOKIE_DOMAIN", "").strip() or None

    EXPOSE_OPENAPI = _booleano(
        "EXPOSE_OPENAPI",
        os.getenv("EXPOSE_OPENAPI"),
        defecto=(ENVIRONMENT == "development"),
    )
    if ENVIRONMENT == "production" and EXPOSE_OPENAPI:
        raise RuntimeError(
            "EXPOSE_OPENAPI debe ser false en producción "
            "(/docs, /redoc y /openapi.json no se publican)."
        )

    # --- Store de seguridad (revocaciones, rate limit, seleccion) ----------
    _store_path = os.getenv("SECURITY_STORE_PATH", "").strip()
    SECURITY_STORE_PATH = (
        Path(_store_path) if _store_path else BACKEND_DIR / "security_store.sqlite3"
    )
    if not SECURITY_STORE_PATH.is_absolute():
        SECURITY_STORE_PATH = BACKEND_DIR / SECURITY_STORE_PATH

    # --- Limites de reportes ----------------------------------------------
    try:
        REPORT_RATE_LIMIT_PER_MINUTE = int(
            os.getenv("REPORT_RATE_LIMIT_PER_MINUTE", "30").strip() or "30"
        )
        REPORT_MAX_CONCURRENT = int(
            os.getenv("REPORT_MAX_CONCURRENT", "3").strip() or "3"
        )
    except ValueError:
        raise RuntimeError(
            "REPORT_RATE_LIMIT_PER_MINUTE y REPORT_MAX_CONCURRENT deben ser enteros."
        )
    if REPORT_RATE_LIMIT_PER_MINUTE < 1 or REPORT_MAX_CONCURRENT < 1:
        raise RuntimeError(
            "Los limites de reportes deben ser mayores que cero."
        )

    # --- CORS --------------------------------------------------------------
    _cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    if any(o.strip() == "*" for o in _cors_env.split(",")):
        raise RuntimeError(
            "CORS_ORIGINS no puede ser '*'. "
            "Defina una lista explícita de orígenes permitidos (separados por coma)."
        )
    CORS_ORIGINS = [o.strip().rstrip("/") for o in _cors_env.split(",") if o.strip()]
    if not CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS no puede quedar vacío.")
    if ENVIRONMENT == "production":
        inseguros = [
            o for o in CORS_ORIGINS
            if "localhost" in o.lower() or "127.0.0.1" in o or "0.0.0.0" in o
        ]
        if inseguros:
            raise RuntimeError(
                "En producción CORS_ORIGINS no puede apuntar a localhost/127.0.0.1. "
                "Configure el dominio real del frontend."
            )

    def ssl_ca_path(self) -> str | None:
        """Ruta absoluta al certificado CA si SSL está habilitado."""
        if not self.DB_SSL_ENABLED:
            return None
        if not self.DB_SSL_CA:
            raise RuntimeError(
                "DB_SSL_ENABLED está activo pero DB_SSL_CA no está configurado. "
                "Defina la ruta al certificado .pem de la base de datos."
            )
        ruta = Path(self.DB_SSL_CA)
        if not ruta.is_absolute():
            ruta = BACKEND_DIR / ruta
        ruta = ruta.resolve()
        if not ruta.is_file():
            raise RuntimeError(
                f"No se encontró el certificado SSL en {ruta}. "
                f"Verifique la ruta configurada en DB_SSL_CA."
            )
        return str(ruta)

    def connection_string(self) -> str:
        """URL de conexión a MySQL, construida desde variables de entorno."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        usuario = quote(_requerido("DB_USER", self.DB_USER), safe="")
        password = quote(_requerido("DB_PASSWORD", self.DB_PASSWORD), safe="")
        return (
            f"mysql+pymysql://"
            f"{usuario}:{password}@"
            f"{_requerido('DB_HOST', self.DB_HOST)}:"
            f"{_requerido('DB_PORT', self.DB_PORT)}/"
            f"{_requerido('DB_NAME', self.DB_NAME)}"
        )


settings = Settings()
