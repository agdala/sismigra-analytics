{% docs __overview__ %}
# SISMIGRA analytics: camada dbt

Modelos dbt sobre os microdados públicos do **SISMIGRA** (Sistema de Registro Nacional Migratório),
2021 a 2026, distribuídos pelo OBMigra/UnB.

**Linhagem:** fontes da bronze (carregadas em Python) → `stg_` (limpeza e padronização) →
`int_` (municípios IBGE, países ISO, correções) → marts (esquema estrela) → `agregado_base` →
controle de divulgação em Python (k = 5) → `publicacao/` → painéis (exposures).

- **Grão do fato:** 1 linha = 1 registro migratório (`qtd_registros` = 1).
- **2026 é parcial (jan-set):** use `ano_completo` para comparar volumes.
- **Publicação:** só os agregados protegidos de `publicacao/` podem ser publicados.

> Este site é gerado no CI a partir de **dados sintéticos**: mostra estrutura, descrições, testes e
> linhagem, sem nenhum dado real.

Repositório: [agdala/sismigra-analytics](https://github.com/agdala/sismigra-analytics)
{% enddocs %}
