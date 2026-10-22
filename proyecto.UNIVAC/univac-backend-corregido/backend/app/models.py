from sqlalchemy import (
    Column, Integer, BigInteger, String, Boolean,
    DateTime, LargeBinary, ForeignKey, Text, Float, TypeDecorator
)
from sqlalchemy.orm import relationship, synonym

from .database import Base


class FoxProBoolean(TypeDecorator):
    impl = String(10)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return 'S' if value else 'N'

    def process_result_value(self, value, dialect):
        if value is None:
            return False
        return str(value).strip().upper() in ('S', 'T', '1', 'TRUE', 'VERDADERO', 'X')


class FoxProInteger(TypeDecorator):
    impl = String(20)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return int(float(str(value).strip()))
        except (ValueError, TypeError):
            return None


class Empresa(Base):
    __tablename__ = "parametros"

    id = Column(BigInteger, primary_key=True, index=True)
    nombre = Column("empresa", String(60), nullable=False)
    razon_social = Column(String(60))
    direccion = Column(String(50))
    rubro_empresarial = Column(String(50))
    id_localidad = Column(Integer)
    id_provincia = Column(Integer)
    id_zona_administracion = Column(Integer)
    telefono = Column(String(50))
    email = Column(String(80))
    mensaje = Column(Text)
    bloqueado = Column("bloqueado", FoxProBoolean, default=False)
    hora_desde = Column(String(5))
    hora_hasta = Column(String(5))
    cuit = Column(String(13))
    ingresos_brutos = Column(String(50))
    agente_retencion_rentas = Column(Boolean, default=False)
    mails_contactos = Column(String(200))
    ubicacion = Column(String(150))
    id_contribuyente = Column(Integer)
    cod_ctacte_univac = Column(String(50))
    folio_compras_sistema = Column(String(50))
    folio_compras_preimpreso = Column(String(50))
    folio_ventas_sistema = Column(String(50))
    folio_ventas_preimpreso = Column(String(50))
    si_extendida = Column(Boolean, default=False)
    si_contabilidad = Column(Boolean, default=False)
    inicio_ejercicio = Column(String(20))
    fin_ejercicio = Column(String(20))
    logo = Column(String(300))
    logo_png = Column(String(300))
    certificado = Column(String(300))
    clave = Column(String(150))
    vencimiento_certificado = Column(String(50))
    smtp = Column(String(150))
    desde = Column(String(150))
    usuario = Column(String(150))
    contrasena = Column(String(150))
    puerto = Column(String(20))
    smtpssl = Column(Boolean, default=False)
    banco_fcredito = Column(String(100))
    cbu_fcredito = Column(String(100))
    transmision_fcredito = Column(String(100))
    precio_venta_con = Column(String(50))
    interes_diario_mora = Column(String(50))
    mismo_precio_estados = Column(Boolean, default=False)
    uso_imagen = Column(Boolean, default=False)
    uso_app_clientes = Column(Boolean, default=False)
    lista_1 = Column(String(50))
    lista_2 = Column(String(50))
    lista_3 = Column(String(50))
    lista_1_abrev = Column(String(20))
    lista_2_abrev = Column(String(20))
    lista_3_abrev = Column(String(20))
    ctacte_por_fecha = Column(Boolean, default=False)
    estado_comprob_app_clientes = Column(Boolean, default=False)
    retenciones_en_iva_compras = Column(Boolean, default=False)
    descuenta_stock_componentes = Column(Boolean, default=False)
    clave_fiscal = Column(String(100))
    cuit_entrar = Column(String(20))
    precio_libreria = Column(String(50))
    confirmacion = Column(String(150))
    autorizo = Column(String(150))

    usuarios = relationship("Usuario", back_populates="empresa")

    @property
    def activa(self):
        return not bool(self.bloqueado)


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(BigInteger, primary_key=True, index=True)
    empresa_id = Column("empresa", BigInteger, ForeignKey("parametros.id"))
    usuario = Column("usuario", String(50), index=True, nullable=False)
    documento = Column("codigo", String(20))
    identificacion = Column("identificacion", String(20))
    password = Column("password", String(100))
    tipo = Column("tipo", FoxProInteger)
    rol = synonym("tipo")
    hora_desde = Column("hora_desde", String(5))
    hora_hasta = Column("hora_hasta", String(5))
    nivel_clave = Column("nivel_clave", FoxProInteger)
    ordenamiento_articulos = Column("ordenamiento_articulos", FoxProInteger)
    dia_cumpleanos = Column("dia_cumpleanos", FoxProInteger)
    mes_cumpleanos = Column("mes_cumpleanos", FoxProInteger)
    scanner = Column("scanner", FoxProBoolean, default=False)
    venta_rapida = Column("venta_rapida", FoxProBoolean, default=False)
    id_comprobante_comun_ventas = Column("id_comprobante_comun_ventas", FoxProInteger)
    modifica_precio_venta = Column("modifica_precio_venta", FoxProBoolean, default=False)
    estado_default = Column("estado_default", FoxProInteger)
    visualiza_totales = Column("visualiza_totales", FoxProBoolean, default=False)
    bloqueado = Column("bloqueado", FoxProBoolean, default=False)
    mensaje = Column("mensaje", Text)

    empresa = relationship("Empresa", back_populates="usuarios")

    @property
    def nombre(self):
        if not self.usuario:
            return ""
        parts = self.usuario.strip().split()
        return parts[0] if parts else ""

    @property
    def apellido(self):
        if not self.usuario:
            return ""
        parts = self.usuario.strip().split()
        return " ".join(parts[1:]) if len(parts) > 1 else ""

    @nombre.setter
    def nombre(self, value):
        name = value.strip() if value else ""
        current = (self.usuario or "").strip()
        parts = current.split() if current else []
        if len(parts) > 1:
            self.usuario = " ".join([name] + parts[1:]).strip()
        else:
            self.usuario = name

    @apellido.setter
    def apellido(self, value):
        surname = value.strip() if value else ""
        current = (self.usuario or "").strip()
        parts = current.split() if current else []
        if len(parts) > 1:
            self.usuario = " ".join([parts[0], surname]).strip()
        elif len(parts) == 1:
            self.usuario = " ".join([parts[0], surname]).strip()
        else:
            self.usuario = surname


class Archivo(Base):
    __tablename__ = "archivos"

    id = Column("sql_rowid", BigInteger, primary_key=True, index=True)
    nombre = Column(String(30))
    archivo = Column(LargeBinary)
    tamanio = Column("tamano", Float)
    fecha = Column(DateTime)
    hora = Column(String(10))
    empresa_id = Column("empresa", BigInteger, ForeignKey("parametros.id"), nullable=True)
    usuario_id = Column(BigInteger, nullable=True)
