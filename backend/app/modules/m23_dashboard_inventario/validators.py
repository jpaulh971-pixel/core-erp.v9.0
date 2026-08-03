"""Validadores del modulo m23_dashboard_inventario (Fase 4A - base).

El unico endpoint de esta fase (GET /api/dashboard-inventario/resumen)
no recibe parametros de entrada del usuario, por lo que no hay datos
externos que validar todavia. Se deja este archivo presente para
respetar el patron Repository -> Service -> Router -> Schemas ->
Validators que sigue el resto del ERP, y para que las siguientes fases
(4B en adelante -- ej. filtros por inventario_id o rango de fechas)
agreguen aca sus validaciones sin romper la estructura ya aprobada.
"""
