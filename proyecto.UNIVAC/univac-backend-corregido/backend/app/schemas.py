from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


class LoginRequest(BaseModel):
    usuario: str
    documento: str
    password: str


class EmpresaOpcion(BaseModel):
    id: int
    nombre: str
    cuit: Optional[str] = None
    activa: bool = True
    usuario_id: int


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    empresa_id: Optional[int] = None
    nombre: str
    usuario: str
    empresa_nombre: str = ""
    empresa_activa: bool = True
    visualiza_totales: bool = False
    venta_rapida: bool = False
    modifica_precio_venta: bool = False
    scanner: bool = False
    nivel_clave: Optional[int] = None
    ordenamiento_articulos: Optional[int] = None

    @field_validator(
        'visualiza_totales', 'venta_rapida',
        'modifica_precio_venta', 'scanner',
        'empresa_activa',
        mode='before'
    )
    @classmethod
    def coerce_bool(cls, v):
        if v is None:
            return False
        if isinstance(v, bool):
            return v
        return str(v).strip().upper() in ('S', 'T', '1', 'TRUE', 'VERDADERO', 'X')

    @field_validator(
        'nivel_clave', 'ordenamiento_articulos',
        mode='before'
    )
    @classmethod
    def coerce_int(cls, v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        try:
            return int(float(str(v).strip()))
        except (ValueError, TypeError):
            return None


class SeleccionarEmpresaRequest(BaseModel):
    usuario_id: int
    empresa_id: int


class MultiEmpresaResponse(BaseModel):
    require_selection: bool = True
    usuario_nombre: str
    empresas: List[EmpresaOpcion]


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


class ActualizarPerfilRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None


class EmpresaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    razon_social: str | None = None
    cuit: str | None = None
    direccion: str | None = None
    telefono: str | None = None
    email: str | None = None
    mensaje: str | None = None
    activa: bool | None = None


class ArchivoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    hora: str | None = None
    tamanio: float | None = None
    fecha: datetime | None = None
    empresa_id: int | None = None
