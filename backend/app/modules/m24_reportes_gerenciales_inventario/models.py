"""Modelos del modulo m24_reportes_gerenciales_inventario (Fase 4C - backend).

Este modulo NO define tablas propias. Los Reportes Gerenciales de
Inventario son, en esta fase, vistas de solo lectura que agregan y
consolidan indicadores ya calculados y persistidos por otros modulos:

  - m03_inventario              (Inventario, ProductoInventario, Lote,
                                  MovimientoKardex -- unica fuente para
                                  "ultimo movimiento" / dias sin rotacion,
                                  que ningun modulo expone todavia)
  - m19_reportes                (inventario valorizado, por lote,
                                  proximos a vencer)
  - m22_inteligencia_inventario (rotacion, consumo, riesgo de merma)
  - m23_dashboard_inventario    (resumen ejecutivo ya consolidado)

Igual que m23_dashboard_inventario, este archivo se deja sin modelos
ORM a proposito: crear tablas aca implicaria duplicar datos que ya
existen en esos modulos, en contra de la regla de esta fase ("no
recalcular ni duplicar logica"). Se mantiene el archivo presente para
no romper el patron Repository -> Service -> Router -> Schemas ->
Validators -> Models que sigue el resto del ERP, y para que fases
futuras (ej. snapshots historicos de reportes gerenciales) tengan
donde agregar tablas propias de forma aditiva.

Como no hay clases declaradas aca, app/main.py NO necesita importar
este archivo en la seccion de "Modelos" (no hay nada que registrar en
Base.metadata).
"""
