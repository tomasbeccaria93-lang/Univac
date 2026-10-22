from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session, joinedload
import jwt
import logging
from datetime import datetime, timedelta, timezone
import time

from ..database import get_db
from ..models import Usuario
from ..schemas import (
    LoginRequest, LoginResponse,
    SeleccionarEmpresaRequest, MultiEmpresaResponse,
    EmpresaOpcion
)
from ..auth import get_current_user, invalidar_token, verificar_password, security
from ..config import settings

logger = logging.getLogger("univac.auth")

router = APIRouter(
    prefix="/auth",
    tags=["Autenticacion"]
)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

_SELECCION_TIMEOUT_SEG = 5 * 60
_selecciones_pendientes = {}

_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 10
_login_attempts = {}


def _to_bool(v):
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().upper() in ('S', 'T', '1', 'TRUE', 'VERDADERO', 'X')


def _to_int(v):
    if v is None:
        return None
    if isinstance(v, int):
        return v
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return None


def _to_str(v):
    if v is None:
        return ""
    return str(v).strip()


def crear_token(usuario):
    import uuid
    datos = {
        "id": usuario.id,
        "empresa": usuario.empresa_id,
        "usuario": usuario.usuario,
        "jti": str(uuid.uuid4()),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(datos, SECRET_KEY, algorithm=ALGORITHM)


def _registrar_seleccion_pendiente(usuario_id):
    now = datetime.now(timezone.utc).timestamp()
    expirados = [k for k, v in _selecciones_pendientes.items() if now > v]
    for k in expirados:
        _selecciones_pendientes.pop(k, None)
    _selecciones_pendientes[usuario_id] = (
        datetime.now(timezone.utc) + timedelta(seconds=_SELECCION_TIMEOUT_SEG)
    ).timestamp()


def _validar_seleccion_pendiente(usuario_id):
    vencimiento = _selecciones_pendientes.get(usuario_id)
    if vencimiento is None:
        return False
    if datetime.now(timezone.utc).timestamp() > vencimiento:
        _selecciones_pendientes.pop(usuario_id, None)
        return False
    return True


def _check_rate_limit(key):
    now = time.time()
    attempts = _login_attempts.get(key, [])
    attempts = [t for t in attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(attempts) >= _RATE_LIMIT_MAX:
        _login_attempts[key] = attempts
        return False
    attempts.append(now)
    _login_attempts[key] = attempts
    if len(_login_attempts) > 1000:
        stale_keys = [
            k for k, v in _login_attempts.items()
            if not v or v[-1] < now - _RATE_LIMIT_WINDOW
        ]
        for k in stale_keys:
            _login_attempts.pop(k, None)
    return True


def _construir_respuesta_login(usuario):
    empresa_nombre = ""
    empresa_activa = True
    if usuario.empresa:
        empresa_nombre = _to_str(usuario.empresa.nombre)
        empresa_activa = not _to_bool(usuario.empresa.bloqueado)

    return LoginResponse(
        access_token=crear_token(usuario),
        token_type="bearer",
        usuario_id=usuario.id,
        empresa_id=usuario.empresa_id,
        nombre=usuario.nombre,
        usuario=usuario.usuario,
        empresa_nombre=empresa_nombre,
        empresa_activa=empresa_activa,
        visualiza_totales=_to_bool(usuario.visualiza_totales),
        venta_rapida=_to_bool(usuario.venta_rapida),
        modifica_precio_venta=_to_bool(usuario.modifica_precio_venta),
        scanner=_to_bool(usuario.scanner),
        nivel_clave=_to_int(usuario.nivel_clave),
        ordenamiento_articulos=_to_int(usuario.ordenamiento_articulos)
    )


@router.post("/login", response_model=None)
def login(
    request: Request,
    datos: LoginRequest,
    db: Session = Depends(get_db)
):
    # La clave combina IP y usuario: con solo el usuario se podrian enumerar
    # cuentas variando el documento, porque cada par creaba su propio bucket.
    ip = request.client.host if request.client else "desconocida"
    rate_key = f"{ip}:{datos.usuario}"
    if not _check_rate_limit(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Intente nuevamente en un minuto."
        )

    usuarios = db.query(Usuario).options(
        joinedload(Usuario.empresa)
    ).filter(
        Usuario.identificacion == datos.usuario,
        Usuario.documento == datos.documento,
        Usuario.nivel_clave == 2
    ).all()

    if not usuarios:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    validos = []
    for u in usuarios:
        if u.bloqueado:
            continue
        if verificar_password(u, datos.password):
            validos.append(u)

    if not validos:
        if all(u.bloqueado for u in usuarios):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El usuario se encuentra deshabilitado"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )

    candidatos = [u for u in validos if u.empresa is not None]

    if not candidatos:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El usuario no tiene una empresa cargada. Contacte al administrador del sistema."
        )

    candidatos = [u for u in candidatos if not _to_bool(u.empresa.bloqueado)]

    if not candidatos:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Todas las empresas asociadas a su usuario se encuentran inactivas. Comuniquese con el administrador del sistema."
        )

    if len(candidatos) == 1:
        return _construir_respuesta_login(candidatos[0])

    for u in candidatos:
        _registrar_seleccion_pendiente(u.id)

    empresas_opciones = []
    for u in candidatos:
        emp = u.empresa
        empresas_opciones.append(
            EmpresaOpcion(
                id=u.empresa_id,
                nombre=_to_str(emp.nombre),
                cuit=_to_str(emp.cuit),
                activa=not _to_bool(emp.bloqueado),
                usuario_id=u.id
            )
        )

    return MultiEmpresaResponse(
        usuario_nombre=_to_str(candidatos[0].usuario),
        empresas=empresas_opciones
    )


@router.post("/seleccionar-empresa", response_model=LoginResponse)
def seleccionar_empresa(
    datos: SeleccionarEmpresaRequest,
    db: Session = Depends(get_db)
):
    if not _validar_seleccion_pendiente(datos.usuario_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debe iniciar sesion nuevamente para elegir la empresa"
        )

    usuario = db.query(Usuario).options(
        joinedload(Usuario.empresa)
    ).filter(
        Usuario.id == datos.usuario_id,
        Usuario.empresa_id == datos.empresa_id
    ).first()

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontro acceso a esa empresa"
        )

    if usuario.bloqueado:
        raise HTTPException(
            status_code=403,
            detail="Usuario deshabilitado para esta empresa"
        )

    if usuario.empresa is None or _to_bool(usuario.empresa.bloqueado):
        raise HTTPException(
            status_code=403,
            detail="La empresa se encuentra inactiva. Comuniquese con el administrador del sistema."
        )

    _selecciones_pendientes.pop(datos.usuario_id, None)
    return _construir_respuesta_login(usuario)


@router.get("/me")
def mi_cuenta(
    usuario: Usuario = Depends(get_current_user)
):
    empresa_nombre = ""
    empresa_activa = True
    if usuario.empresa:
        empresa_nombre = _to_str(usuario.empresa.nombre)
        empresa_activa = not _to_bool(usuario.empresa.bloqueado)

    return {
        "id": usuario.id,
        "empresa_id": usuario.empresa_id,
        "empresa_nombre": empresa_nombre,
        "empresa_activa": empresa_activa,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "usuario": usuario.usuario,
        "documento": _to_str(usuario.documento),
        "identificacion": _to_str(usuario.identificacion),
        "nivel_clave": _to_int(usuario.nivel_clave),
        "ordenamiento_articulos": _to_int(usuario.ordenamiento_articulos),
        "dia_cumpleanos": _to_int(usuario.dia_cumpleanos),
        "mes_cumpleanos": _to_int(usuario.mes_cumpleanos),
        "scanner": _to_bool(usuario.scanner),
        "venta_rapida": _to_bool(usuario.venta_rapida),
        "modifica_precio_venta": _to_bool(usuario.modifica_precio_venta),
        "visualiza_totales": _to_bool(usuario.visualiza_totales),
        "estado_default": _to_int(usuario.estado_default),
        "hora_desde": _to_str(usuario.hora_desde),
        "hora_hasta": _to_str(usuario.hora_hasta),
        "bloqueado": _to_bool(usuario.bloqueado),
        "rol": _to_int(usuario.rol)
    }


@router.get("/verify")
def verify(
    usuario: Usuario = Depends(get_current_user)
):
    return {
        "ok": True,
        "usuario": usuario.usuario
    }


@router.post("/logout")
def logout(
    usuario: Usuario = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(security)
):
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
            jti = payload.get("jti")
            if jti:
                invalidar_token(jti)
        except Exception as exc:
            logger.warning("logout: no se pudo invalidar el token: %s", exc)
    return {
        "success": True
    }
