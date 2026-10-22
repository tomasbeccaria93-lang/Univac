from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import logging

from .config import settings

logger = logging.getLogger("univac.database")

DATABASE_URL = settings.connection_string()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=15,
    max_overflow=10,
    echo=False,
    connect_args={"connect_timeout": 10}
)


@event.listens_for(engine, "connect")
def _set_mysql_mode(dbapi_connection, connection_record):
    try:
        with dbapi_connection.cursor() as cursor:
            cursor.execute(
                "SET SESSION sql_mode='NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES'"
            )
    except Exception as exc:
        logger.warning("no se pudo fijar sql_mode en la sesion: %s", exc)


class Base(DeclarativeBase):
    pass

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
