from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine

# --- Modelos: se importan para que Base.metadata los conozca ---
from app.modules.m02_productos import models as _m02_models  # noqa: F401
from app.modules.m03_inventario import models as _m03_models  # noqa: F401
from app.modules.m04_compras import models as _m04_models  # noqa: F401
from app.modules.m05_proveedores import models as _m05_models  # noqa: F401
from app.modules.m06_comercio_exterior import models as _m06_models  # noqa: F401
from app.modules.m07_operacion_logistica import models as _m07_models  # noqa: F401
from app.modules.m08_costos import models as _m08_models  # noqa: F401
from app.modules.m09_moneda import models as _m09_models  # noqa: F401
from app.modules.m10_ventas import models as _m10_models  # noqa: F401
from app.modules.m11_clientes import models as _m11_models  # noqa: F401
from app.modules.m12_sunat import models as _m12_models  # noqa: F401
from app.modules.m01_dashboard import models as _m01_models  # noqa: F401
from app.modules.m13_inteligencia_comercial import models as _m13_models  # noqa: F401
from app.modules.m14_inteligencia_tributaria import models as _m14_models  # noqa: F401
from app.modules.m15_lean_six_sigma import models as _m15_models  # noqa: F401
from app.modules.m16_theory_of_constraints import models as _m16_models  # noqa: F401
from app.modules.m17_guias_remision import models as _m17_models  # noqa: F401
from app.modules.m20_configuracion import models as _m20_models  # noqa: F401
from app.modules.m21_importacion_datos import models as _m21_models  # noqa: F401

# --- Routers implementados con logica real ---
from app.modules.m02_productos.router import router as productos_router
from app.modules.m03_inventario.router import router as inventario_router
from app.modules.m04_compras.router import router as compras_router
from app.modules.m05_proveedores.router import router as proveedores_router
from app.modules.m06_comercio_exterior.router import router as comercio_exterior_router
from app.modules.m07_operacion_logistica.router import router as operacion_logistica_router
from app.modules.m08_costos.router import router as costos_router
from app.modules.m09_moneda.router import router as moneda_router
from app.modules.m10_ventas.router import router as ventas_router
from app.modules.m11_clientes.router import router as clientes_router
from app.modules.m12_sunat.router import router as sunat_router
from app.modules.m20_configuracion.router import router as configuracion_router
from app.modules.m20_configuracion.router import auth_router
from app.modules.m01_dashboard.router import router as m01_router
from app.modules.m13_inteligencia_comercial.router import router as m13_router
from app.modules.m14_inteligencia_tributaria.router import router as m14_router
from app.modules.m15_lean_six_sigma.router import router as m15_router
from app.modules.m16_theory_of_constraints.router import router as m16_router
from app.modules.m17_guias_remision.router import router as m17_router
from app.modules.m18_balanced_scorecard.router import router as m18_router
from app.modules.m19_reportes.router import router as m19_router
from app.modules.m21_importacion_datos.router import router as m21_router
from app.modules.m22_inteligencia_inventario.router import router as m22_router
from app.modules.m23_dashboard_inventario.router import router as m23_router
from app.modules.m24_reportes_gerenciales_inventario.router import router as m24_router

app = FastAPI(title="Core ERP - Almacen de Exportacion", version="0.1.0")

# FASE 3 (CORS seguro): origenes explicitos via variable de entorno
# CORS_ORIGINS (coma-separados; ver app/config.py y backend/.env.example).
# Nunca se usa "*" como allow_origins. Si CORS_ORIGINS no esta definida
# (instalacion local limpia, sin .env con ese valor), se agrega ademas
# allow_origin_regex solo para localhost/127.0.0.1 en cualquier puerto,
# de forma que el Frontend local siga funcionando sin configuracion
# manual. allow_credentials se mantiene en False (identico al valor
# anterior): el Frontend envia el JWT por header "Authorization", no por
# cookies, por lo que no depende de credentials=True.
_CORS_ORIGINS_ENV = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
_CORS_LOCALHOST_REGEX = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS_ENV,
    allow_origin_regex=None if _CORS_ORIGINS_ENV else _CORS_LOCALHOST_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _migrar_estado_lote_si_falta() -> None:
    """FASE 1 (seguridad operativa perecibles): agrega la columna
    Lote.estado a una tabla 'lotes' preexistente que todavia no la
    tenga. Base.metadata.create_all() solo crea tablas nuevas, no altera
    tablas ya existentes, por eso este paso extra es necesario para no
    romper una base de datos con datos previos. No toca ninguna fila:
    los lotes existentes quedan con estado='ACTIVO' por defecto (su
    estado real se recalcula solo en el proximo ingreso/salida/ajuste, y
    el bloqueo de vencidos igual funciona de inmediato porque compara la
    fecha directamente, sin depender de esta columna)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "lotes" not in inspector.get_table_names():
        return
    columnas = {c["name"] for c in inspector.get_columns("lotes")}
    if "estado" in columnas:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE lotes ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'ACTIVO'"))


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _migrar_estado_lote_si_falta()


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Implementados
app.include_router(auth_router)
app.include_router(configuracion_router)
app.include_router(productos_router)
app.include_router(inventario_router)
app.include_router(proveedores_router)
app.include_router(compras_router)
app.include_router(comercio_exterior_router)
app.include_router(operacion_logistica_router)
app.include_router(costos_router)
app.include_router(moneda_router)
app.include_router(ventas_router)
app.include_router(clientes_router)
app.include_router(sunat_router)
app.include_router(m01_router)
app.include_router(m13_router)
app.include_router(m14_router)
app.include_router(m15_router)
app.include_router(m16_router)
app.include_router(m17_router)
app.include_router(m18_router)
app.include_router(m19_router)
app.include_router(m21_router)
app.include_router(m22_router)
app.include_router(m23_router)
app.include_router(m24_router)
