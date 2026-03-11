# Python / Django / FastAPI / Flask — Code Review Checklist

- **Type hints**: all function signatures use type hints; `mypy` or `pyright` passes without errors
- **Async correctness**: `async def` used only where truly async; blocking I/O not called from async context
- **ORM queries**: Django ORM / SQLAlchemy used correctly; `select_related`/`prefetch_related` used to avoid N+1
- **Pydantic / serializers**: input validated via Pydantic models (FastAPI) or DRF serializers (Django); no raw dict access from request
- **Exception handling**: specific exceptions caught, not bare `except:`; exceptions not swallowed silently
- **Settings management**: secrets and config loaded from environment via `django-environ`, `python-decouple`, or Pydantic `BaseSettings`; not hardcoded
- **Migrations** *(Django)*: migrations generated and reviewed; no raw SQL in application code unless necessary
