from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models, schemas

router = APIRouter(
    prefix="/empresa",
    tags=["Empresa"]
)


def _visualiza_totales(usuario):
    valor = getattr(usuario, "visualiza_totales", False)
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().upper() in ("S", "T", "1", "TRUE", "VERDADERO", "X")


@router.get("/perfil", response_model=schemas.EmpresaResponse)
def perfil_empresa(
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    empresa = db.query(models.Empresa).filter(
        models.Empresa.id == usuario.empresa_id
    ).first()

    if empresa is None:
        raise HTTPException(
            status_code=404,
            detail="Empresa inexistente"
        )

    respuesta = schemas.EmpresaResponse.model_validate(empresa)
    if not _visualiza_totales(usuario):
        respuesta.razon_social = None
        respuesta.cuit = None
        respuesta.direccion = None
        respuesta.telefono = None
        respuesta.email = None
        respuesta.mensaje = None
    return respuesta
