from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user
from .. import models
from .. import schemas

router = APIRouter(
    prefix="/archivos",
    tags=["Archivos"]
)


@router.get("/mios", response_model=list[schemas.ArchivoResponse])
def mis_archivos(
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    archivos = db.query(models.Archivo).filter(
        models.Archivo.usuario_id == usuario.id
    ).order_by(
        models.Archivo.fecha.desc()
    ).limit(100).all()

    return archivos


@router.get("/empresa", response_model=list[schemas.ArchivoResponse])
def archivos_empresa(
    usuario=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    eid = usuario.empresa_id
    archivos = db.query(models.Archivo).filter(
        models.Archivo.empresa_id == eid
    ).order_by(
        models.Archivo.fecha.desc()
    ).limit(100).all()

    return archivos
