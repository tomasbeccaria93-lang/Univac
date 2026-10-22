from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user, verificar_password, hashear_password, invalidar_tokens_usuario
from .. import schemas
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
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    password_valida = verificar_password(usuario, datos.password_actual)

    if not password_valida:
        raise HTTPException(
            status_code=400,
            detail="La contraseña actual no coincide"
        )

    if len(datos.password_nueva) < 6:
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña debe tener al menos 6 caracteres"
        )

    if verificar_password(usuario, datos.password_nueva):
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña debe ser distinta a la actual"
        )

    usuario.password = hashear_password(datos.password_nueva)
    db.commit()
    invalidar_tokens_usuario(usuario.id)

    return {
        "mensaje": "Contraseña actualizada"
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
