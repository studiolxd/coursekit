# Contribuir

- Activa el hook: `git config core.hooksPath .githooks`. Antes de cada commit comprueba que no se
  publica ningún término de la lista privada (`tools/check_terms.py`).
- La lista no se versiona: créala en `.forbidden-terms` (ignorado por git), un término por línea.
  En GitHub está en el secreto `FORBIDDEN_TERMS` y la CI falla si encuentra alguno.
- Entorno: `uv sync --group dev`, después `uv run pytest` y `uv run ruff check .`.
