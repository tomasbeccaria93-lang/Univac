from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv
import os

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent.parent


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

    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()

    # --- Seguridad ---------------------------------------------------------
    SECRET_KEY = _requerido("SECRET_KEY", os.getenv("SECRET_KEY"))
    ALGORITHM = "HS256"

    try:
        ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120").strip() or "120"
        )
    except ValueError:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un numero entero."
        )

    # --- CORS --------------------------------------------------------------
    _cors_env = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    if _cors_env.strip() == "*":
        raise RuntimeError(
            "CORS_ORIGINS no puede ser '*'. "
            "Defina una lista explícita de orígenes permitidos (separados por coma)."
        )
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]

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
