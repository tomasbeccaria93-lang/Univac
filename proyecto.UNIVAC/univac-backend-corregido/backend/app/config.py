from dotenv import load_dotenv
import os

load_dotenv()


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

    def connection_string(self) -> str:
        """URL de conexión a MySQL, construida desde variables de entorno."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://"
            f"{_requerido('DB_USER', self.DB_USER)}:"
            f"{_requerido('DB_PASSWORD', self.DB_PASSWORD)}@"
            f"{_requerido('DB_HOST', self.DB_HOST)}:"
            f"{_requerido('DB_PORT', self.DB_PORT)}/"
            f"{_requerido('DB_NAME', self.DB_NAME)}"
        )


settings = Settings()
