from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, List
from datetime import datetime

_PASSWORDS_COMUNES = {
    "1234567890", "123456789", "password", "password1", "qwerty123",
    "administrador", "admin1234", "univac123", "empresa123", "12345678a",
}


def validar_password_fuerte(password: str) -> str:
    if len(password) < 10:
        raise ValueError("La contraseña debe tener al menos 10 caracteres.")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("La contraseña no puede superar los 72 bytes.")
    if not any(c.islower() for c in password):
        raise ValueError("La contraseña debe incluir una letra minúscula.")
    if not any(c.isupper() for c in password):
        raise ValueError("La contraseña debe incluir una letra mayúscula.")
    if not any(c.isdigit() for c in password):
        raise ValueError("La contraseña debe incluir un número.")
    if not any(not c.isalnum() for c in password):
        raise ValueError("La contraseña debe incluir un símbolo.")
    if password.lower() in _PASSWORDS_COMUNES:
        raise ValueError("La contraseña es demasiado común.")
    return password


class LoginRequest(BaseModel):
    usuario: str
    documento: str
    password: str

    @field_validator("usuario", "documento")
    @classmethod
    def limpiar_identificador(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("El usuario y el documento son obligatorios.")
        if len(v) > 64:
            raise ValueError("El usuario o documento es demasiado largo.")
        return v

    @field_validator("password")
    @classmethod
    def limitar_password(cls, v: str) -> str:
        if not v:
            raise ValueError("La contraseña es obligatoria.")
        if len(v.encode("utf-8")) > 256:
            raise ValueError("La contraseña es demasiado larga.")
        return v


class EmpresaOpcion(BaseModel):
    id: int
    nombre: str
    cuit: Optional[str] = None
    activa: bool = True
    usuario_id: int


class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str = ""
    token_type: str = "cookie"
    csrf_token: str = ""
    expires_in: int = 0
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
    selection_token: str = ""

    @field_validator("selection_token")
    @classmethod
    def exigir_codigo(cls, v: str) -> str:
        v = (v or "").strip()
        if not v or len(v) > 128:
            raise ValueError("El código de selección no es válido.")
        return v


class MultiEmpresaResponse(BaseModel):
    require_selection: bool = True
    usuario_nombre: str
    selection_token: str = ""
    expires_in: int = 300
    empresas: List[EmpresaOpcion]


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str

    @field_validator("password_actual")
    @classmethod
    def limitar_actual(cls, v: str) -> str:
        if not v or len(v.encode("utf-8")) > 256:
            raise ValueError("La contraseña actual no es válida.")
        return v

    @field_validator("password_nueva")
    @classmethod
    def exigir_password_fuerte(cls, v: str) -> str:
        return validar_password_fuerte(v)

    @model_validator(mode="after")
    def distinta_de_la_actual(self):
        if self.password_actual == self.password_nueva:
            raise ValueError("La contraseña nueva debe ser distinta de la actual.")
        return self


class ActualizarPerfilRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None

    @field_validator("nombre", "apellido")
    @classmethod
    def limpiar_perfil(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        if not v:
            return None
        if len(v) > 80:
            raise ValueError("El nombre o apellido es demasiado largo.")
        if any(ord(c) < 32 for c in v):
            raise ValueError("El nombre o apellido contiene caracteres inválidos.")
        return v


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
