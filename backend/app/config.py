"""Configuracion global del ERP de Almacen de Exportacion.

Diseno: un solo almacen central, un solo usuario (Administrador).
No existen sucursales, tiendas ni permisos por sucursal.
"""
import os
from pydantic_settings import BaseSettings

# Fallback de SOLO desarrollo local. Se usa unicamente cuando no existe
# la variable de entorno SECRET_KEY ni un archivo .env que la defina (ver
# mas abajo). NO es apta para produccion: es un valor fijo, publico, que
# cualquiera que tenga este repositorio puede leer. En Render (o
# cualquier despliegue real) hay que definir SECRET_KEY como variable de
# entorno real -- ver backend/.env.example y render.yaml.
_SECRET_KEY_DEV_DEFAULT = "dev-only-insecure-secret-key-CAMBIAR-EN-PRODUCCION"


class Settings(BaseSettings):
    APP_NAME: str = "Core ERP - Almacen de Exportacion"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./erp_almacen.db")

    # FASE 3 (CORS seguro): origenes explicitos permitidos para el
    # Frontend, separados por coma (ej. "https://mi-frontend.onrender.com,
    # https://mi-dominio.com"). Vacio por defecto: en ese caso app/main.py
    # NO usa "*" -- en su lugar aplica una regla adicional solo para
    # desarrollo local (localhost/127.0.0.1, cualquier puerto), pensada
    # para no requerir configuracion manual en una instalacion local
    # limpia. Definir esta variable es obligatorio para cualquier
    # despliegue real (Render u otro) cuyo Frontend no corra en
    # localhost -- ver backend/.env.example y render.yaml.
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    # Regla de negocio fija: nombre del unico almacen central del sistema.
    ALMACEN_CENTRAL_NOMBRE: str = "Almacen Central"

    # FASE 1 (seguridad operativa perecibles): dias de anticipacion para
    # marcar un lote como PROXIMO_VENCER (ver m03_inventario.service.
    # calcular_estado_lote). No afecta el bloqueo de lotes VENCIDOS, que
    # es independiente de este valor.
    DIAS_ALERTA_VENCIMIENTO: int = 30

    # FASE 2 (control gerencial de inventario perecible): factor sobre
    # stock_minimo que define el nivel AMARILLO del semaforo de stock
    # (ver m03_inventario.service.calcular_semaforo_stock). Con el valor
    # por defecto 1.2, un producto entra en AMARILLO cuando su stock cae
    # dentro del 20% por encima de su stock_minimo, y en ROJO cuando
    # queda igual o por debajo del stock_minimo. No afecta el booleano
    # bajo_stock_minimo ya existente (m01_dashboard, m03/m19 reportes),
    # que sigue calculandose exactamente igual que antes.
    FACTOR_ALERTA_STOCK_CERCANO: float = 1.2

    # FASE 3 (inteligencia de inventario para perecibles): ventana de
    # dias por defecto para calcular consumo real, consumo promedio y
    # rotacion de inventario (ver m22_inteligencia_inventario.service).
    # Se puede sobreescribir por request via query param 'dias_analisis'.
    DIAS_ANALISIS_INVENTARIO_DEFAULT: int = 90

    # FASE 3: umbrales (en dias) para puntuar el factor "vencimiento"
    # del riesgo de merma, a partir de Lote.fecha_vencimiento.
    UMBRAL_DIAS_VENCER_CRITICO: int = 7
    UMBRAL_DIAS_VENCER_ALTO: int = 30
    UMBRAL_DIAS_VENCER_MEDIO: int = 90

    # FASE 3: umbrales para puntuar el factor "rotacion" del riesgo de
    # merma (rotacion = consumo real del periodo / stock promedio).
    UMBRAL_ROTACION_BAJA: float = 0.5
    UMBRAL_ROTACION_MEDIA: float = 1.0

    # FASE 3: umbrales (en dias) para puntuar el factor "dias de
    # inventario" del riesgo de merma (dias_inventario = stock actual /
    # consumo promedio diario).
    UMBRAL_DIAS_INVENTARIO_MEDIO: float = 30
    UMBRAL_DIAS_INVENTARIO_ALTO: float = 60
    UMBRAL_DIAS_INVENTARIO_CRITICO: float = 90

    # FASE 3: puntaje minimo (score acumulado, ver m22_inteligencia_
    # inventario.service.evaluar_riesgo_merma) para clasificar un
    # producto en cada nivel de riesgo de merma. El score maximo posible
    # es 12 (4 vencimiento + 3 rotacion + 3 dias_inventario + 2 stock
    # inmovilizado).
    SCORE_RIESGO_MERMA_MEDIO: int = 2
    SCORE_RIESGO_MERMA_ALTO: int = 5
    SCORE_RIESGO_MERMA_CRITICO: int = 8

    # FASE 4C (reportes gerenciales de inventario): umbral por defecto
    # (en dias) de inactividad de Kardex para que un producto aparezca
    # en el reporte "Productos sin rotacion" (ver
    # m24_reportes_gerenciales_inventario.service). Se puede
    # sobreescribir por request via query param 'dias_sin_rotacion'. No
    # afecta ningun umbral existente de Fase 1/2/3.
    UMBRAL_DIAS_SIN_ROTACION: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

if not settings.SECRET_KEY:
    # Sin SECRET_KEY definida (ni por variable de entorno ni por .env):
    # se usa un valor por defecto FIJO de solo-desarrollo para que el
    # backend arranque sin friccion en una instalacion local limpia
    # (venv -> pip install -> seed.py -> uvicorn, sin pasos extra).
    #
    # Este fallback nunca debe llegar a produccion: si DATABASE_URL no es
    # SQLite local (es decir, parece un despliegue real) se sube el
    # mensaje a error visible en vez de una advertencia silenciable.
    settings.SECRET_KEY = _SECRET_KEY_DEV_DEFAULT
    _es_sqlite_local = settings.DATABASE_URL.startswith("sqlite:///./") or settings.DATABASE_URL.startswith(
        "sqlite:///" + os.getcwd()
    )
    _prefijo = "ADVERTENCIA" if _es_sqlite_local else "ERROR DE CONFIGURACION"
    print(
        f"{_prefijo}: SECRET_KEY no esta configurada. Usando una clave de "
        "desarrollo INSEGURA y fija (valida solo para correr el proyecto "
        "en local). Definir SECRET_KEY real (por ejemplo en backend/.env, "
        "ver .env.example) es OBLIGATORIO antes de cualquier despliegue "
        "real o de exponer este backend fuera de tu máquina."
    )
