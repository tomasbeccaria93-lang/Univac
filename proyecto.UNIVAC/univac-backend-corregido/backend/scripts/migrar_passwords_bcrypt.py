"""Migra las contraseñas en texto plano de `usuarios` a hashes bcrypt.

Uso (desde la carpeta backend):

    python -m scripts.migrar_passwords_bcrypt          # simulación, no escribe
    python -m scripts.migrar_passwords_bcrypt --apply  # aplica el cambio

El modo por defecto solo informa cuántas filas se migrarían. Requiere
autorización explícita antes de ejecutar --apply porque modifica MySQL.
"""

from __future__ import annotations

import argparse
import sys

from passlib.context import CryptContext
from sqlalchemy import text

from app.database import SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migra contraseñas legado (texto plano) a bcrypt."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Escribe los hashes en MySQL. Sin este flag solo simula.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        filas = db.execute(
            text("SELECT id, password FROM usuarios ORDER BY id")
        ).fetchall()

        pendientes = []
        ya_bcrypt = 0
        vacias = 0
        invalidas = 0

        for fila in filas:
            usuario_id = fila[0]
            password = fila[1]
            if password is None or str(password) == "":
                vacias += 1
                continue
            password = str(password)
            if password.startswith("$2"):
                ya_bcrypt += 1
                continue
            if len(password.encode("utf-8")) > 72:
                invalidas += 1
                print(
                    f"AVISO: usuario id={usuario_id} tiene una clave de más de "
                    "72 bytes; se omite. Debe resetearla manualmente."
                )
                continue
            pendientes.append((usuario_id, password))

        print(f"Total de filas: {len(filas)}")
        print(f"Ya en bcrypt: {ya_bcrypt}")
        print(f"Vacías: {vacias}")
        print(f"Demasiado largas (omitidas): {invalidas}")
        print(f"Pendientes de migrar: {len(pendientes)}")

        if not pendientes:
            print("No hay nada para migrar.")
            return 0

        if not args.apply:
            print("Simulación: no se escribió nada. Ejecute con --apply para aplicar.")
            return 0

        for usuario_id, password in pendientes:
            nuevo_hash = pwd_context.hash(password)
            db.execute(
                text("UPDATE usuarios SET password = :hash WHERE id = :id"),
                {"hash": nuevo_hash, "id": usuario_id},
            )

        db.commit()
        print(f"Migradas {len(pendientes)} contraseñas a bcrypt.")
        print(
            "El escritorio debe actualizarse para leer bcrypt; si sigue "
            "comparando texto plano, dejará de autenticar."
        )
        return 0


if __name__ == "__main__":
    sys.exit(main())
