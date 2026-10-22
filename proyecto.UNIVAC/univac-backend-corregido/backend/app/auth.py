import time
import logging
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import InvalidTokenError
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from .database import get_db
from .models import Usuario
from .config import settings

logger = logging.getLogger("univac.auth")

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM

security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

_tokens_invalidados: dict[str, float] = {}
_usuarios_invalidados: dict[int, float] = {}
TOKEN_EXPIRE_SECONDS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def invalidar_token(jti):
    _tokens_invalidados[jti] = time.time() + TOKEN_EXPIRE_SECONDS
    if len(_tokens_invalidados) > 5000:
        now = time.time()
        expired = [k for k, v in _tokens_invalidados.items() if v <= now]
        for k in expired:
            _tokens_invalidados.pop(k, None)


def invalidar_tokens_usuario(usuario_id):
    _usuarios_invalidados[usuario_id] = time.time()
    if len(_usuarios_invalidados) > 5000:
        limite = time.time() - TOKEN_EXPIRE_SECONDS
        viejos = [k for k, v in _usuarios_invalidados.items() if v <= limite]
        for k in viejos:
            _usuarios_invalidados.pop(k, None)


def token_invalido(jti):
    exp = _tokens_invalidados.get(jti)
    if exp is None:
        return False
    if time.time() > exp:
        _tokens_invalidados.pop(jti, None)
        return False
    return True


def verificar_password(usuario, password):
    if not usuario.password:
        return False
    if usuario.password.startswith("$2"):
        return pwd_context.verify(password, usuario.password)
    if secrets.compare_digest(password.encode("utf-8"), usuario.password.encode("utf-8")):
        logger.warning(
            "Usuario %s: acceso con password legado (no-bcrypt). "
            "Se recomienda migrar el hash a bcrypt.",
            usuario.id
        )
        return True
    return False


def hashear_password(password):
    return pwd_context.hash(password)


def _rechazar(detail):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"}
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        _rechazar("No autenticado")

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        usuario_id = payload.get("id")
        if usuario_id is None:
            _rechazar("Token inválido")
        jti = payload.get("jti")
        if jti and token_invalido(jti):
            _rechazar("Token invalidado (sesión cerrada)")
        exp = payload.get("exp")
        if exp is not None and exp - TOKEN_EXPIRE_SECONDS < _usuarios_invalidados.get(usuario_id, 0):
            _rechazar("Token invalidado (contraseña cambiada)")
    except InvalidTokenError:
        _rechazar("Token inválido")

    usuario = db.query(Usuario).filter(
        Usuario.id == usuario_id
    ).first()

    if usuario is None:
        _rechazar("Usuario inexistente")

    if usuario.bloqueado:
        _rechazar("Usuario deshabilitado")

    return usuario
