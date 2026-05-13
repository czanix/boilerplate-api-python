# Czanix Boilerplate — API Python

> Padrões de engenharia validados em produção. A formalização do que funciona — para que você não descubra o caminho errado em produção.

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tech Reference](https://img.shields.io/badge/Czanix-Tech%20Reference-gold)](https://czanix.com/pt/stack)

---

## O problema que isso resolve

Toda API Python nova começa com as mesmas armadilhas:
- `print()` em vez de logger estruturado — sem rastreabilidade em produção
- Configuração hardcoded — vaza credencial no repositório
- Exceção para tudo — fluxo de negócio misturado com erro real
- Conexão nova por request — pool esgotado sob carga
- Zero health check — descobre que caiu pelo usuário

Este boilerplate já resolveu tudo isso. Você começa com a fundação certa.

---

## Estrutura

```
src/
├── domain/                     # Regras de negócio puras — zero dependências externas
│   ├── entities/               # O que o sistema representa
│   │   └── order.py            # Entidade com validação e lógica de negócio
│   ├── repositories/           # Contratos (ABCs) — não implementações
│   │   └── order_repository.py
│   └── result.py               # Result[T] — sucesso ou falha explícita
│
├── application/                # O que o sistema FAZ (casos de uso)
│   ├── use_cases/
│   │   ├── create_order.py
│   │   └── cancel_order.py
│   └── dtos/                   # Contratos de entrada/saída
│       └── order_dto.py
│
├── infrastructure/             # Como o sistema se conecta ao mundo externo
│   ├── database/
│   │   ├── factory.py          # Pool PostgreSQL + SQL Server com retry
│   │   └── migrations/         # Schema SQL versionado (Alembic)
│   ├── repositories/           # Implementações concretas
│   │   └── pg_order_repository.py
│   └── cache/
│       └── redis_client.py
│
└── presentation/               # Como o mundo fala com o sistema (FastAPI)
    ├── routes/
    │   └── order_routes.py
    ├── middlewares/
    │   ├── auth.py             # JWT validation
    │   └── rate_limit.py       # Rate limiting por IP
    └── validators/
        └── order_validator.py

tests/
├── unit/                       # Sem banco, sem rede — rápido e isolado
│   └── test_cancel_order.py
└── integration/                # Com banco de test real
    └── test_order_repository.py
```

---

## Início rápido

```bash
# Clone e configure
git clone https://github.com/czanix/boilerplate-api-python.git meu-projeto
cd meu-projeto
cp .env.example .env

# Ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Sobe banco e cache
docker compose up -d

# Migrations
alembic upgrade head

# Desenvolvimento
uvicorn src.presentation.app:app --reload
```

---

## O que está embutido e por quê

### Result Pattern — sem exceção para fluxo de negócio

```python
# domain/result.py — o tipo que força tratamento explícito
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')

@dataclass(frozen=True)
class Ok(Generic[T]):
    value: T
    ok: bool = True

@dataclass(frozen=True)
class Err:
    error: str
    ok: bool = False

Result = Ok | Err

# Uso — o chamador VÊ que pode falhar (ao contrário de try/except escondido)
def cancelar_pedido(pedido_id: str) -> Result[Pedido]:
    pedido = repo.buscar(pedido_id)
    if not pedido:
        return Err("PEDIDO_NAO_ENCONTRADO")        # fluxo de negócio
    if pedido.status == "entregue":
        return Err("PEDIDO_JA_ENTREGUE")           # outra regra
    pedido.cancelar()
    repo.salvar(pedido)
    return Ok(pedido)                              # sucesso

# No controller — forçado a lidar com ambos os casos
resultado = cancelar_pedido(pedido_id)
if not resultado.ok:
    raise HTTPException(status_code=422, detail=resultado.error)
return resultado.value
```

### Pool de conexões — o que salva você sob carga

```python
# infrastructure/database/factory.py
# Pool criado UMA vez na startup, reusado por TODOS os requests

# Sem pool (errado):
# Cada request: nova conexão (~100ms) → query → fecha
# 100 requests simultâneos = 100 conexões novas = timeout garantido

# Com pool (correto):
# Startup: cria 2-10 conexões
# Request: pega conexão do pool → query → devolve ao pool
# 100 requests simultâneos = max 10 conexões = estável

def init_postgres_pool(settings: Settings) -> None:
    global _pg_pool
    _pg_pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=settings.db_pool_min,   # sempre abertas
        maxconn=settings.db_pool_max,   # máximo sob carga
        dsn=settings.database_url,
    )

# Context manager garante devolução ao pool mesmo em erro
with DatabaseFactory.postgres() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE public_id = %s", (public_id,))
```

### Settings validadas na startup

```python
# config/settings.py — falha na inicialização, não em produção
class Settings(BaseSettings):
    database_url: str      # sem default = obrigatório
    secret_key: str        # sem default = obrigatório
    app_env: str = "development"

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env == "production" and len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY muito curta para produção")
        return self

# Se DATABASE_URL não estiver no ambiente → erro claro na startup
# Sem isso: aplicação sobe, tenta conectar no banco, falha 30min depois
```

---

## Monitoramento — obrigatório desde o primeiro deploy

> "Dado que você não monitora é dado que não existe para você."

Um sistema que você não monitora é um sistema que vai te surpreender da pior forma — e você vai descobrir pelo usuário, não pelo alerta.

### Health check (já implementado)

```python
# presentation/routes/health.py
@router.get("/health")
async def health():
    """
    Endpoint verificado pelo orquestrador (Kubernetes, Cloud Run, ECS).
    Se retornar 5xx, o orquestrador reinicia a instância.
    """
    db_ok = await check_database()
    cache_ok = await check_redis()

    status = "healthy" if (db_ok and cache_ok) else "degraded"
    code = 200 if status == "healthy" else 503

    return JSONResponse(status_code=code, content={
        "status": status,
        "version": settings.app_version,
        "checks": {
            "database": db_ok,
            "cache": cache_ok,
        }
    })
```

### As 4 métricas que importam para escalar

| O que medir | Por que importa | Ferramenta grátis |
|-------------|-----------------|-------------------|
| Disponibilidade do /health | Você sabe antes do usuário | Uptime Robot |
| Latência P95/P99 das rotas | Onde está o gargalo | Prometheus + Grafana |
| Taxa de erro (5xx/total) | Qualidade em produção | Sentry (tier grátis) |
| Uso de conexões do pool | Antes de esgotar | Prometheus |

**Regra:** configure o Uptime Robot no mesmo dia do primeiro deploy. É grátis. Sem isso, você descobre que o sistema caiu pelo usuário, não pelo alerta.

### Por que monitoramento = escalabilidade

```
Sem monitoramento:
  Aumentar escala → mais instâncias → mesmo gargalo escalado
  Resultado: gasta mais, resolve menos

Com monitoramento:
  Identifica o gargalo real (banco? cache? CPU? I/O?)
  Resolve o gargalo → DEPOIS escala
  Resultado: escala com eficiência

Escala horizontal sem monitoramento é jogar dinheiro em cima de problema invisível.
```

---

## Schema SQL (também aqui)

```sql
-- Toda tabela transacional segue esse padrão
-- Veja: czanix.com/pt/stack/dados para o raciocínio completo

CREATE TABLE orders (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    public_id   UUID NOT NULL DEFAULT gen_random_uuid(),
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    deleted_at  TIMESTAMPTZ NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_orders_public_id UNIQUE (public_id)
);

-- Índice filtrado — só o que importa para queries reais
CREATE INDEX ix_orders_customer_active
    ON orders (customer_id, created_at DESC)
    WHERE deleted_at IS NULL;
```

---

## Architecture Decision Records (ADRs)

Decisões arquiteturais documentadas com contexto, motivo e trade-offs:

- [ADR-001: INT/BIGINT PK + UUID público](docs/adrs/001-bigint-pk-uuid-public.md)
- [ADR-002: Result Pattern vs Exceptions](docs/adrs/002-result-pattern-over-exceptions.md)
- [ADR-003: Clean Architecture com limites pragmáticos](docs/adrs/003-clean-architecture-boundaries.md)
- [ADR-004: Princípios de Modelagem de Dados](docs/adrs/004-database-design-principles.md)
- [ADR-005: Partitioning para Tabelas de Alto Volume](docs/adrs/005-table-partitioning.md)
- [ADR-006: Connection Pooling e Pool Sizing](docs/adrs/006-connection-pooling.md)
- [ADR-007: VACUUM, Autovacuum e Bloat Prevention](docs/adrs/007-vacuum-autovacuum.md)
- [ADR-008: Read Replicas e Separação de Leitura/Escrita](docs/adrs/008-read-replicas.md)
---

## Referência completa

- [czanix.com/pt/stack/backend](https://czanix.com/pt/stack/backend) — Clean Architecture, SOLID
- [czanix.com/pt/stack/dados](https://czanix.com/pt/stack/dados) — Padrões SQL
- [czanix.com/pt/stack/devops](https://czanix.com/pt/stack/devops) — CI/CD e monitoramento

---

<div align="center">
<sub>Desenvolvido e mantido por <a href="https://czanix.com">Cesar Zanis</a> — Czanix</sub>
</div>
