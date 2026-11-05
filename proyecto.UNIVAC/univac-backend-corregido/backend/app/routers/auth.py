from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session, joinedload
import logging
import secrets
import time

from .. import security_store
from ..database import get_db
from ..models import Usuario
from ..schemas import (
    LoginRequest, LoginResponse,
    SeleccionarEmpresaRequest, MultiEmpresaResponse,
    EmpresaOpcion
)
from ..auth import (
    clear_session_cookie,
    decodificar_token,
    firmar_token,
    get_current_user,
    invalidar_token,
    set_session_cookie,
    token_de_request,
    verificar_password,
    verificar_password_dummy,
)
from ..config import settings

logger = logging.getLogger("univac.auth")

router = APIRouter(
    prefix="/auth",
    tags=["Autenticacion"]
)

ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

_SELECCION_TIMEOUT_SEG = 5 * 60
_SELECCION_MAX_INTENTOS = 5

_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 10
_RATE_LIMIT_MAX_IP = 30


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


def _demasiados_intentos():
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Demasiados intentos. Intente nuevamente en un minuto."
    )


def _credenciales_invalidas():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Usuario o contraseña incorrectos"
    )


def _crear_codigo_seleccion(pares):
    code = secrets.token_urlsafe(48)
    payload = [[int(uid), int(eid)] for uid, eid in pares]
    security_store.crear_codigo_seleccion(
        code,
        payload,
        expires_at=time.time() + _SELECCION_TIMEOUT_SEG,
        attempts=_SELECCION_MAX_INTENTOS,
    )
    return code


def _construir_respuesta_login(usuario, response: Response):
    empresa_nombre = ""
    empresa_activa = True
    if usuario.empresa:
        empresa_nombre = _to_str(usuario.empresa.nombre)
        empresa_activa = not _to_bool(usuario.empresa.bloqueado)

    token, payload = firmar_token(usuario)
    set_session_cookie(response, token)

    return LoginResponse(
        access_token="",
        token_type="cookie",
        csrf_token=payload["csrf"],
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
    response: Response,
    datos: LoginRequest,
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else "desconocida"

    # El limite por IP frena la enumeracion masiva de documentos; el limite
    # por IP+usuario protege una cuenta concreta.
    if not security_store.permitir(
        f"login-ip:{ip}", _RATE_LIMIT_MAX_IP, _RATE_LIMIT_WINDOW
    ):
        _demasiados_intentos()
    if not security_store.permitir(
        f"login-user:{ip}:{datos.usuario.strip().lower()}",
        _RATE_LIMIT_MAX,
        _RATE_LIMIT_WINDOW,
    ):
        _demasiados_intentos()

    usuarios = db.query(Usuario).options(
        joinedload(Usuario.empresa)
    ).filter(
        Usuario.identificacion == datos.usuario,
        Usuario.documento == datos.documento
    ).all()

    if not usuarios:
        verificar_password_dummy()
        _credenciales_invalidas()

    validos = []
    for u in usuarios:
        if u.bloqueado:
            continue
        if verificar_password(u, datos.password):
            validos.append(u)

    if not validos:
        verificar_password_dummy()
        _credenciales_invalidas()

    autorizados = [u for u in validos if _to_int(u.nivel_clave) == 2]
    if not autorizados:
        logger.info("login: credenciales válidas sin nivel_clave=2")
        _credenciales_invalidas()

    candidatos = [u for u in autorizados if u.empresa is not None]
    if not candidatos:
        logger.info("login: credenciales válidas sin empresa asociada")
        _credenciales_invalidas()

    candidatos = [u for u in candidatos if not _to_bool(u.empresa.bloqueado)]
    if not candidatos:
        logger.info("login: credenciales válidas con todas las empresas inactivas")
        _credenciales_invalidas()

    if len(candidatos) == 1:
        return _construir_respuesta_login(candidatos[0], response)

    selection_token = _crear_codigo_seleccion(
        [(u.id, u.empresa_id) for u in candidatos]
    )

    empresas_opciones = []
    for u in candidatos:
        emp = u.empresa
        empresas_opciones.append(
            EmpresaOpcion(
                id=u.empresa_id,
                nombre=_to_str(emp.nombre),
                cuit=_to_str(emp.cuit) if _to_bool(u.visualiza_totales) else "",
                activa=not _to_bool(emp.bloqueado),
                usuario_id=u.id
            )
        )

    return MultiEmpresaResponse(
        usuario_nombre=_to_str(candidatos[0].usuario),
        selection_token=selection_token,
        expires_in=_SELECCION_TIMEOUT_SEG,
        empresas=empresas_opciones
    )


@router.post("/seleccionar-empresa", response_model=LoginResponse)
def seleccionar_empresa(
    response: Response,
    datos: SeleccionarEmpresaRequest,
    db: Session = Depends(get_db)
):
    pares = security_store.usar_codigo_seleccion(datos.selection_token)
    if not pares:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debe iniciar sesión nuevamente para elegir la empresa"
        )

    autorizado = [int(uid) for uid, eid in pares
                  if int(uid) == datos.usuario_id and int(eid) == datos.empresa_id]
    if not autorizado:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debe iniciar sesión nuevamente para elegir la empresa"
        )

    usuario = db.query(Usuario).options(
        joinedload(Usuario.empresa)
    ).filter(
        Usuario.id == datos.usuario_id,
        Usuario.empresa_id == datos.empresa_id
    ).first()

    if (
        usuario is None
        or usuario.bloqueado
        or _to_int(usuario.nivel_clave) != 2
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se encontró acceso a esa empresa"
        )

    if usuario.empresa is None or _to_bool(usuario.empresa.bloqueado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La empresa se encuentra inactiva. Comuníquese con el administrador del sistema."
        )

    security_store.borrar_codigo_seleccion(datos.selection_token)
    return _construir_respuesta_login(usuario, response)


@router.get("/me")
def mi_cuenta(
    request: Request,
    usuario: Usuario = Depends(get_current_user)
):
    empresa_nombre = ""
    empresa_activa = True
    if usuario.empresa:
        empresa_nombre = _to_str(usuario.empresa.nombre)
        empresa_activa = not _to_bool(usuario.empresa.bloqueado)

    payload = getattr(request.state, "auth_payload", {}) or {}

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
        "rol": _to_int(usuario.rol),
        "csrf_token": payload.get("csrf", ""),
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
def logout(request: Request, response: Response):
    token, via_cookie = token_de_request(request)
    if token and via_cookie:
        payload = decodificar_token(token, verificar_exp=False)
        if payload and payload.get("purpose") == "access":
            csrf_header = request.headers.get("X-CSRF-Token", "")
            csrf_claim = payload.get("csrf", "")
            if not csrf_header or not csrf_claim or not secrets.compare_digest(
                csrf_header, csrf_claim
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token inválido"
                )
            invalidar_token(payload.get("jti"), payload.get("exp"))
    clear_session_cookie(response)
    return {"success": True}
