"""Modelos del modulo m23_dashboard_inventario (Fase 4A - base).

Este modulo NO define tablas propias. El Dashboard Gerencial de
Inventario es, en esta fase, una vista de solo lectura que agrega
indicadores ya calculados y persistidos por otros modulos:

  - m03_inventario              (Inventario, ProductoInventario, Lote,
                                  MovimientoKardex)
  - m19_reportes                (reportes de inventario valorizado, por
                                  lote y proximos a vencer)
  - m22_inteligencia_inventario (riesgo de merma)

Este archivo se deja sin modelos ORM a proposito: crear una tabla
nueva aca implicaria duplicar datos que ya existen en esos modulos,
en contra de la regla de esta fase ("no recalcular ni duplicar
logica"). Se mantiene el archivo presente para no romper el patron
Repository -> Service -> Router -> Schemas -> Validators -> Models
que sigue el resto del ERP, y para que fases futuras (si se aprueba
persistir algo propio de este dashboard, ej. snapshots historicos)
tengan donde agregarlo de forma aditiva.

Como no hay clases declaradas aca, app/main.py NO necesita importar
este archivo en la seccion de "Modelos" (no hay nada que registrar en
Base.metadata). Si una fase futura agrega una tabla propia, se debera
sumar el import correspondiente en main.py en ese momento, de forma
aditiva.
"""
