"""Crea el unico usuario Administrador, el almacen central y datos
minimos de ejemplo para probar el flujo de Inventario."""
import os

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.security import hash_password

from app.modules.m02_productos import models as _m02_models  # noqa: F401
from app.modules.m03_inventario import models as _m03_models  # noqa: F401
from app.modules.m04_compras import models as _m04_models  # noqa: F401
from app.modules.m05_proveedores import models as _m05_models  # noqa: F401
from app.modules.m20_configuracion import models as _m20_models  # noqa: F401

from app.modules.m02_productos.models import Producto
from app.modules.m03_inventario.models import Inventario
from app.modules.m05_proveedores.models import Proveedor
from app.modules.m20_configuracion.models import ParametroSistema, Usuario

# Contraseña fija del usuario admin. Se toma de la variable de entorno
# ADMIN_PASSWORD (definida en backend/.env); si no existe, se usa el
# valor por defecto indicado abajo.
# IMPORTANTE (produccion): "Admin123*" es solo un valor de arranque.
# Definí ADMIN_PASSWORD en backend/.env con una contraseña propia y fuerte
# antes de desplegar, y cambiala luego desde la app si el sistema lo permite.
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin123*")


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        usuario_admin = db.query(Usuario).filter(Usuario.username == "admin").first()
        if not usuario_admin:
            db.add(
                Usuario(
                    username="admin",
                    nombre_completo="Administrador",
                    password_hash=hash_password(ADMIN_PASSWORD),
                    rol="ADMINISTRADOR",
                )
            )
        else:
            # Ya existe: se actualiza su contraseña al valor fijo/configurado
            # para evitar quedar bloqueado por una contraseña aleatoria previa.
            usuario_admin.password_hash = hash_password(ADMIN_PASSWORD)

        if not db.query(Inventario).filter_by(codigo="INV-001").first():
            db.add(Inventario(codigo="INV-001", nombre="Inventario 1"))

        if not db.query(ParametroSistema).filter_by(clave="MONEDA_BASE").first():
            db.add(ParametroSistema(clave="MONEDA_BASE", valor="USD", descripcion="Moneda base del ERP"))

        if not db.query(Producto).filter_by(codigo="EXP-0001").first():
            db.add(
                Producto(
                    codigo="EXP-0001",
                    nombre="Producto de exportacion demo",
                    unidad_medida="KG",
                    stock_minimo=100,
                )
            )

        if not db.query(Proveedor).filter_by(ruc="20123456789").first():
            db.add(
                Proveedor(
                    ruc="20123456789",
                    razon_social="Proveedor Demo S.A.C.",
                    contacto="Juan Perez",
                    email="contacto@proveedordemo.com",
                    pais="Peru",
                )
            )

        db.commit()
        print("Usuario administrador creado/actualizado correctamente.")
        print("Usuario: admin")
        print("Contraseña: ********")
        print("Seed OK: almacen central, producto y proveedor demo creados.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
