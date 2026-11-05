import logging
import secrets
import time

from fastapi import Depends, HTTPException, Request, Response, status
import jwt
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from . import security_store
from .database import get_db
from .models import Usuario
from .config import settings

logger = logging.getLogger("univac.auth")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
TOKEN_EXPIRE_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

_METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def invalidar_token(jti, expires_at=None):
    if not jti:
        return
    exp = float(expires_at) if expires_at is not None else time.time() + TOKEN_EXPIRE_SECONDS
    security_store.revocar_token(str(jti), exp)


def invalidar_tokens_usuario(usuario_id):
    security_store.invalidar_usuario(int(usuario_id), time.time())


def token_invalido(jti):
    return security_store.token_revocado(str(jti)) if jti else False


def verificar_password(usuario, password):
    if not usuario.password:
        return False
    if usuario.password.startswith("$2"):
        if len(password.encode("utf-8")) > 72:
            return False
        try:
            return pwd_context.verify(password, usuario.password)
        except (ValueError, TypeError):
            return False
    # Compatibilidad con el ERP de escritorio: la base sigue guardando texto
    # plano. Se mantiene la comparación en tiempo constante. La migración a
    # bcrypt queda disponible en scripts/migrar_passwords_bcrypt.py.
    if secrets.compare_digest(
        password.encode("utf-8"), usuario.password.encode("utf-8")
    ):
        logger.warning(
            "Usuario %s: acceso con password legado (no-bcrypt). "
            "Se recomienda migrar el hash a bcrypt.",
            usuario.id,
        )
        return True
    return False


def verificar_password_dummy():
    """Consume tiempo similar a un hash real para evitar enumeración por timing."""
    try:
        pwd_context.dummy_verify()
    except Exception:
        pwd_context.hash("dummy-password-timing")


def hashear_password(password):
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña supera el límite de 72 bytes de bcrypt.")
    return pwd_context.hash(password)


def crear_payload_token(usuario):
    ahora = time.time()
    return {
        "purpose": "access",
        "id": usuario.id,
        "empresa": usuario.empresa_id,
        "usuario": usuario.usuario,
        "jti": secrets.token_hex(16),
        "csrf": secrets.token_urlsafe(32),
        "iat": ahora,
        "exp": ahora + TOKEN_EXPIRE_SECONDS,
    }


def firmar_token(usuario):
    payload = crear_payload_token(usuario)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), payload


def decodificar_token(token, verificar_exp=True):
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": bool(verificar_exp)},
        )
    except InvalidTokenError:
        return None


def token_de_request(request: Request):
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        return token, True
    return None, False


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=TOKEN_EXPIRE_SECONDS,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
    )


def clear_session_cookie(response: Response):
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def _rechazar(detail="No autenticado", status_code=status.HTTP_401_UNAUTHORIZED):
    raise HTTPException(
        status_code=status_code,
        detail=detail,
        headers={"WWW-Authenticate": "Cookie"},
    )


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    token, via_cookie = token_de_request(request)
    if not token:
        _rechazar()

    payload = decodificar_token(token, verificar_exp=True)
    if payload is None or payload.get("purpose") != "access":
        _rechazar("Sesión inválida o expirada")

    usuario_id = payload.get("id")
    if usuario_id is None:
        _rechazar("Sesión inválida o expirada")

    jti = payload.get("jti")
    if jti and token_invalido(jti):
        _rechazar("Sesión cerrada")

    emitido = payload.get("iat")
    if emitido is None:
        exp = payload.get("exp")
        emitido = (float(exp) - TOKEN_EXPIRE_SECONDS) if exp else 0
    if float(emitido) < security_store.usuario_invalidado_en(usuario_id):
        _rechazar("Sesión invalidada")

    if via_cookie and request.method.upper() not in _METODOS_SEGUROS:
        csrf_header = request.headers.get("X-CSRF-Token", "")
        csrf_claim = payload.get("csrf", "")
        if not csrf_header or not csrf_claim or not secrets.compare_digest(
            csrf_header, csrf_claim
        ):
            _rechazar("CSRF token inválido", status.HTTP_403_FORBIDDEN)

    request.state.auth_payload = payload
    request.state.auth_via_cookie = via_cookie

    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id
    ).first()

    if usuario is None:
        _rechazar("Sesión inválida o expirada")

    if usuario.bloqueado:
        _rechazar("Sesión inválida o expirada")

    if usuario.nivel_clave != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario no autorizado para consultar esta estadística"
        )

    request.state.usuario = usuario

    return usuario
