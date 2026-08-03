# FASE 2 — Seguridad de Credenciales (.env)

**Fecha:** 2026-08-03
**Alcance:** Exclusivo — variables de entorno y control de versiones.
**No incluye:** módulos funcionales del ERP, lógica de autenticación, JWT, usuarios, permisos ni roles (sin cambios, confirmado por diff — ver sección de verificación).

---

## 1. Hallazgo de auditoría atendido

El ZIP entregado en la Fase 1 (Transacciones Atómicas) incluía `backend/.env` con credenciales reales (SECRET_KEY de firma JWT y ADMIN_PASSWORD), lo que significa que esas credenciales quedaron expuestas en un entregable distribuido. Este hallazgo se resuelve en su totalidad en esta fase.

## 2. Cambios realizados

### 2.1 Rotación de credenciales
Se generó una nueva `SECRET_KEY` (64 bytes aleatorios, `secrets.token_urlsafe`) y una nueva `ADMIN_PASSWORD` para el archivo `backend/.env` de desarrollo local, invalidando las credenciales que viajaron en el ZIP de la Fase 1.

- Los tokens JWT firmados con la `SECRET_KEY` anterior dejan de ser válidos tras este cambio (comportamiento esperado y deseado de una rotación: fuerza el re-login).
- El algoritmo de firma (HS256), la lógica de `security.py`/`deps.py` y el flujo de autenticación **no se modificaron**.

### 2.2 Exclusión de `backend/.env` del entregable y del control de versiones
Se creó `/.gitignore` en la raíz del proyecto (no existía ninguno previamente) con reglas para:
- Excluir `backend/.env` y cualquier `*.env` real de Git, preservando explícitamente `*.env.example`.
- Excluir artefactos no versionables ya presentes en el proyecto (`__pycache__/`, `*.db`, entornos virtuales, logs), que antes viajaban sin control.

El ZIP final de esta fase (`ERP_FASE2_seguridad_credenciales.zip`) se generó **excluyendo explícitamente `backend/.env`** de su contenido. Se verificó con `unzip -l` que el archivo no está presente en el paquete; solo se incluye `backend/.env.example`.

### 2.3 Plantilla `.env.example`
Se revisó `backend/.env.example`: ya cumplía el rol de plantilla sin valores reales (variables `SECRET_KEY=`, `ADMIN_PASSWORD=`, `DATABASE_URL=` vacías/de ejemplo, con instrucciones de generación). **No requirió cambios.**

## 3. Archivos modificados/agregados (lista exacta)

Comparado contra el ZIP de entrada de la Fase 1 (`diff -rq`):

| Archivo | Acción | Tipo |
|---|---|---|
| `backend/.env` | Modificado (rotación de `SECRET_KEY` y `ADMIN_PASSWORD`) | Credencial local, no distribuida |
| `.gitignore` | Creado (nuevo) | Configuración de control de versiones |

**Ningún otro archivo del proyecto fue tocado.** No hubo cambios en `backend/app/config.py`, `security.py`, `deps.py`, ni en ningún módulo de negocio, router, schema, modelo, frontend o base de datos.

## 4. Justificación técnica de cada cambio

- **`backend/.env` (rotación):** las credenciales previas se consideran comprometidas por haber viajado dentro de un ZIP entregado. Rotarlas es la única forma de neutralizar el hallazgo sin tocar el mecanismo de autenticación en sí. El formato del archivo (`CLAVE=valor`, sin comillas) se mantuvo idéntico para no afectar el parseo por `pydantic-settings`.
- **`.gitignore` (creación):** el proyecto no tenía ningún archivo de exclusión, por lo que cualquier `git init`/`git add .` futuro habría vuelto a versionar `backend/.env` con credenciales reales. Es la corrección estructural que evita que el hallazgo se repita en el futuro, no solo en este entregable puntual.
- **`backend/.env.example` (sin cambios):** ya diseñado correctamente como plantilla; modificarlo no era necesario y hubiera estado fuera del alcance autorizado.

## 5. Verificación

- **Diff exacto contra la Fase 1:** confirmado con `diff -rq` — únicos cambios: `backend/.env` (contenido) y `.gitignore` (nuevo). Cero cambios en módulos funcionales.
- **Sintaxis de módulos backend no tocados:** verificada con `py_compile` sobre `config.py`, `main.py`, `deps.py`, `security.py`, `database.py`, `seed.py` — sin errores.
- **Parseo del nuevo `.env`:** verificado manualmente (formato `CLAVE=valor`) — las tres variables (`SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`) se leen correctamente y con longitud/formato válidos para `Settings` (`app/config.py`).
- **Contenido del ZIP final:** verificado con `unzip -l` que `backend/.env` NO está incluido y que `backend/.env.example` sí lo está.
- **Arranque real del servidor (uvicorn):** **no pudo ejecutarse en este entorno de trabajo** por no tener acceso a red para instalar las dependencias de `requirements.txt` (fastapi, pydantic-settings, etc. no están preinstaladas en este sandbox). Esta es una limitación del entorno de esta sesión, no del cambio en sí — el cambio no toca ninguna línea de código de la aplicación, solo el valor de dos variables de entorno y la adición de un `.gitignore`. Recomendación: al recibir este ZIP, correr `uvicorn app.main:app --reload` localmente como último paso de aceptación (5 pasos ya documentados en `.env.example`) para confirmar arranque end-to-end antes de dar por cerrada la fase.

## 6. Nota de trazabilidad

Esta fase no modifica ni reabre la Fase 1 (Transacciones Atómicas), que permanece integrada sin cambios. La auditoría general de verificación queda pendiente, a ejecutarse recién cuando también esté finalizada la siguiente fase (CORS), para validar ambas correcciones en conjunto, según lo indicado.
