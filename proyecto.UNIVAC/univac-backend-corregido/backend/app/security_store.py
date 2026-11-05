"""Store compartido y persistente para el estado de seguridad.

Guarda revocaciones de tokens, invalidaciones por cambio de contraseña,
limites de intentos y codigos de seleccion de empresa. Se apoya en SQLite
para que el estado sobreviva a reinicios y sea visible por varios workers.

No toca la base MySQL del ERP: crea un archivo local (SECURITY_STORE_PATH).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from .config import settings

logger = logging.getLogger("univac.security_store")

_LOCK = threading.Lock()
_INITIALIZED = False


def _connect() -> sqlite3.Connection:
    settings.SECURITY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(settings.SECURITY_STORE_PATH),
        timeout=10,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


@contextmanager
def _connection():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def init() -> None:
    global _INITIALIZED
    with _LOCK:
        if _INITIALIZED:
            return
        with _connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    jti TEXT PRIMARY KEY,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_revoked_exp
                    ON revoked_tokens(expires_at);

                CREATE TABLE IF NOT EXISTS user_invalidations (
                    usuario_id INTEGER PRIMARY KEY,
                    changed_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS rate_limits (
                    key TEXT NOT NULL,
                    ts REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_rate_key_ts
                    ON rate_limits(key, ts);

                CREATE TABLE IF NOT EXISTS selection_codes (
                    code TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    attempts INTEGER NOT NULL
                );
                """
            )
        _INITIALIZED = True


def revocar_token(jti: str, expires_at: float) -> None:
    if not jti:
        return
    ahora = time.time()
    try:
        with _connection() as conn:
            conn.execute(
                "DELETE FROM revoked_tokens WHERE expires_at <= ?", (ahora,)
            )
            conn.execute(
                "INSERT OR REPLACE INTO revoked_tokens(jti, expires_at) VALUES(?, ?)",
                (jti, float(expires_at)),
            )
    except sqlite3.Error as exc:
        logger.warning("No se pudo persistir la revocacion del token: %s", exc)


def token_revocado(jti: str) -> bool:
    if not jti:
        return False
    ahora = time.time()
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT expires_at FROM revoked_tokens WHERE jti = ?", (jti,)
            ).fetchone()
            if row is None:
                return False
            if float(row["expires_at"]) <= ahora:
                conn.execute(
                    "DELETE FROM revoked_tokens WHERE jti = ?", (jti,)
                )
                return False
            return True
    except sqlite3.Error as exc:
        logger.warning("No se pudo consultar la revocacion del token: %s", exc)
        return False


def invalidar_usuario(usuario_id: int, changed_at: float | None = None) -> None:
    ts = float(changed_at if changed_at is not None else time.time())
    try:
        with _connection() as conn:
            conn.execute(
                "INSERT INTO user_invalidations(usuario_id, changed_at) "
                "VALUES(?, ?) ON CONFLICT(usuario_id) "
                "DO UPDATE SET changed_at = excluded.changed_at",
                (int(usuario_id), ts),
            )
    except sqlite3.Error as exc:
        logger.warning("No se pudo persistir la invalidacion del usuario: %s", exc)


def usuario_invalidado_en(usuario_id: int) -> float:
    try:
        with _connection() as conn:
            row = conn.execute(
                "SELECT changed_at FROM user_invalidations WHERE usuario_id = ?",
                (int(usuario_id),),
            ).fetchone()
            return float(row["changed_at"]) if row is not None else 0.0
    except sqlite3.Error as exc:
        logger.warning("No se pudo consultar la invalidacion del usuario: %s", exc)
        return 0.0


def permitir(key: str, max_intentos: int, ventana_segundos: int) -> bool:
    """Rate limit por ventana deslizante. True si el intento esta permitido."""
    ahora = time.time()
    desde = ahora - float(ventana_segundos)
    try:
        with _connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute(
                    "DELETE FROM rate_limits WHERE key = ? AND ts < ?",
                    (key, desde),
                )
                row = conn.execute(
                    "SELECT COUNT(*) AS n FROM rate_limits WHERE key = ?",
                    (key,),
                ).fetchone()
                if int(row["n"]) >= int(max_intentos):
                    conn.execute("COMMIT")
                    return False
                conn.execute(
                    "INSERT INTO rate_limits(key, ts) VALUES(?, ?)",
                    (key, ahora),
                )
                conn.execute("COMMIT")
                return True
            except sqlite3.Error:
                conn.execute("ROLLBACK")
                raise
    except sqlite3.Error as exc:
        logger.warning("No se pudo aplicar el rate limit: %s", exc)
        # Sin store disponible se prioriza la disponibilidad del login.
        return True


def crear_codigo_seleccion(
    code: str,
    payload: list[list[int]],
    expires_at: float,
    attempts: int,
) -> None:
    ahora = time.time()
    try:
        with _connection() as conn:
            conn.execute(
                "DELETE FROM selection_codes WHERE expires_at <= ?", (ahora,)
            )
            conn.execute(
                "INSERT OR REPLACE INTO selection_codes"
                "(code, payload, expires_at, attempts) VALUES(?, ?, ?, ?)",
                (code, json.dumps(payload), float(expires_at), int(attempts)),
            )
    except sqlite3.Error as exc:
        logger.warning("No se pudo crear el codigo de seleccion: %s", exc)


def usar_codigo_seleccion(code: str) -> list[list[int]] | None:
    """Devuelve los pares autorizados y descuenta un intento de forma atomica."""
    if not code:
        return None
    ahora = time.time()
    try:
        with _connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute(
                    "SELECT payload, expires_at, attempts FROM selection_codes "
                    "WHERE code = ?",
                    (code,),
                ).fetchone()
                if row is None:
                    conn.execute("COMMIT")
                    return None
                if float(row["expires_at"]) <= ahora or int(row["attempts"]) <= 0:
                    conn.execute(
                        "DELETE FROM selection_codes WHERE code = ?", (code,)
                    )
                    conn.execute("COMMIT")
                    return None
                conn.execute(
                    "UPDATE selection_codes SET attempts = attempts - 1 "
                    "WHERE code = ?",
                    (code,),
                )
                payload = json.loads(row["payload"])
                conn.execute("COMMIT")
                return payload
            except (sqlite3.Error, ValueError, TypeError):
                conn.execute("ROLLBACK")
                raise
    except (sqlite3.Error, ValueError, TypeError) as exc:
        logger.warning("No se pudo consumir el codigo de seleccion: %s", exc)
        return None


def borrar_codigo_seleccion(code: str) -> None:
    if not code:
        return
    try:
        with _connection() as conn:
            conn.execute(
                "DELETE FROM selection_codes WHERE code = ?", (code,)
            )
    except sqlite3.Error as exc:
        logger.warning("No se pudo borrar el codigo de seleccion: %s", exc)


def ruta_store() -> Path:
    return Path(settings.SECURITY_STORE_PATH)


init()
