from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models, schemas

router = APIRouter(
    prefix="/empresa",
    tags=["Empresa"]
)


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

    return empresa
