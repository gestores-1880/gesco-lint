# gesco-lint

Linters de las convenciones de código de Gesco. Es un plugin de [flake8](https://flake8.pycqa.org/)
que registra códigos `GES` y se distribuye como hook de [pre-commit](https://pre-commit.com/).

Ruff no admite plugins: las reglas propias viven aquí y se ejecutan junto a ruff, limitadas a los
códigos `GES`.

## Uso con pre-commit

```yaml
  - repo: https://github.com/gestores-1880/gesco-lint
    rev: v0.1.1
    hooks:
      - id: gesco-lint
        files: ^backend/
```

### Repos con código previo

`--changed-only` reporta solo las líneas añadidas o modificadas:

```yaml
      - id: gesco-lint
        args: [--changed-only]
```

- En CI con `pre-commit run --from-ref <base> --to-ref <head>`, compara con `PRE_COMMIT_FROM_REF`.
- En un commit local, compara con `HEAD` (pre-commit ya ha apartado los cambios no staged).

Cuando el repo esté limpio, quita `--changed-only`.

## Uso desde la línea de comandos

```bash
pip install "gesco-lint @ git+https://github.com/gestores-1880/gesco-lint@v0.1.1"

gesco-lint backend/                              # todo
gesco-lint --diff-base origin/develop backend/   # solo lo cambiado respecto a develop
flake8 --select=GES backend/                     # o flake8 directamente
```

## Excepciones

Se usa el `noqa` estándar de flake8, con el motivo detrás del código:

```python
pagination_class = None  # noqa: GES191 catálogo acotado de 12 meses
```

Con ruff, declara los códigos como externos para que `RUF100` no borre esos `noqa`:

```toml
[tool.ruff.lint]
external = ["GES"]
```

## Códigos

### GES1 — API Django REST Framework

Cada código cita el default que incumple (`API-n`). La convención completa vive en la rule
`drf-api.mdc` de `agent-config`.

| Código | Default | Detecta |
|--------|---------|---------|
| `GES111` | API-1 CRUD con generics/mixins | `http_method_names` en una clase |
| `GES121` | API-2 Filtros con django-filter | `query_params.get(...)` o `query_params[...]` fuera de `filters` / `pagination`. `Serializer(data=request.query_params)` no se marca |
| `GES131` | API-3 Entrada con serializer | `request.data[...]` o `request.data.get(...)` |
| `GES151` | API-5 Librería `validators` | Tabla de letras de control del DNI |
| `GES171` | API-7 Sin literales HTTP | `status_code == 200`, `Response(status=201)` |
| `GES172` | API-7 Sin literales HTTP | `request.method == "POST"`, `method in ("PUT", "PATCH")` |
| `GES181` | API-8 Sin N+1 | Lookup `__in` con una lista, set o generador materializado |
| `GES191` | API-9 Listados paginados | `pagination_class = None` |

API-4 (salida con serializer), API-6 (framework antes que mecanismos propios) y la carga de
relaciones de API-8 no se detectan en el AST: se revisan en el plan y en la review.

### GES2 — Modelos Django

Cada código cita la rule de `agent-config` que incumple. No se aplican a ficheros bajo
`migrations/` (ahí el esquema histórico copia los kwargs del campo).

| Código | Rule | Detecta |
|--------|------|---------|
| `GES211` | `django-model-indexes` | `db_index=True` o `db_index=False` en un campo (`*Field` / `ForeignKey`) |
| `GES221` | `django-models` | `unique=True` en un campo; la unicidad va en `Meta.constraints` con `UniqueConstraint` |

### GES3 — Migraciones Django

Cada código cita la rule de `agent-config` que incumple. Solo se aplican a ficheros bajo
`migrations/`.

| Código | Rule | Detecta |
|--------|------|---------|
| `GES311` | `django-migrations` | `RunPython(...)` sin keyword `elidable=` |
| `GES321` | `django-migrations` | `from …models import …` (o equivalente) dentro de una función usada por `RunPython` |

## Añadir un linter

1. Una familia por dominio: `GES1` es DRF; `GES2` es modelos; `GES3` es migraciones; la siguiente será `GES4`.
2. Módulo `gesco_lint/<familia>.py` con un checker de flake8 (`__init__(tree, filename)` + `run()`).
3. Entry point en `pyproject.toml`, en `[project.entry-points."flake8.extension"]`.
4. Tests en `tests/gesco_lint/test_<familia>.py`: uno que reporta y uno que no, por código.
5. Tabla de códigos en este README y nueva versión (`vX.Y.Z`) con tag.

## Desarrollo

```bash
python -m venv .venv && .venv/bin/pip install -e ".[test]"
.venv/bin/pytest
pre-commit run --all-files
```
