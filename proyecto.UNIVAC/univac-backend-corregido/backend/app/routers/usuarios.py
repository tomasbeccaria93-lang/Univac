from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..auth import (
    clear_session_cookie,
    get_current_user,
    hashear_password,
    invalidar_tokens_usuario,
    verificar_password,
)
from .. import schemas, security_store
from ..database import get_db

router = APIRouter(
    prefix="/usuario",
    tags=["Usuario"]
)


@router.get("/perfil")
def perfil(
    usuario=Depends(get_current_user)
):
    return {
        "id": usuario.id,
        "empresa_id": usuario.empresa_id,
        "nombre": usuario.nombre,
        "apellido": usuario.apellido,
        "usuario": usuario.usuario,
        "documento": str(usuario.documento) if usuario.documento else "",
        "rol": usuario.rol
    }


@router.put("/password")
def cambiar_password(
    datos: schemas.CambiarPasswordRequest,
    response: Response,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not security_store.permitir(
        f"password-change:{usuario.id}", 5, 5 * 60
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Intente nuevamente más tarde."
        )

    if not verificar_password(usuario, datos.password_actual):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual no coincide"
        )

    try:
        usuario.password = hashear_password(datos.password_nueva)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )

    db.commit()
    invalidar_tokens_usuario(usuario.id)
    clear_session_cookie(response)

    return {
        "mensaje": "Contraseña actualizada. Inicie sesión nuevamente."
    }


@router.put("/perfil")
def actualizar_perfil(
    datos: schemas.ActualizarPerfilRequest,
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if datos.nombre is not None:
        usuario.nombre = datos.nombre

    if datos.apellido is not None:
        usuario.apellido = datos.apellido

    db.commit()
    db.refresh(usuario)

    return {
        "mensaje": "Perfil actualizado"
    }
