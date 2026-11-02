# Equivalência: pipeline com dbt versus pipeline anterior (SQL puro)

Comparação executada em 2026-11-02T21:11:18+00:00 (UTC) com os dados reais do SISMIGRA 2021 a 2026 (1.361.391 registros), por `scripts/comparar_equivalencia.py`.

- **Linhas:** contagem de cada tabela.
- **Só antes / Só dbt:** linhas presentes em uma versão e ausentes na outra (`EXCEPT ALL` nos dois sentidos, todas as colunas). Zero nos dois lados = conteúdo idêntico.
- **Totais:** registros por ano, por país de nacionalidade e por UF.
- **publicacao/:** os CSVs protegidos precisam ser idênticos byte a byte.

**Resultado: idêntico em todas as verificações.**

| Tabela antiga | Modelo dbt | Linhas (antes) | Linhas (dbt) | Só antes | Só dbt | Resultado |
|---|---|---|---|---|---|---|
| `prata` | `intermediate.int_registros_enriquecidos` | 1.361.391 | 1.361.391 | 0 | 0 | idêntica |
| `rejeitados` | `staging.stg_rejeitados` | 0 | 0 | 0 | 0 | idêntica |
| `fato_registro` | `marts.fato_registro` | 1.361.391 | 1.361.391 | 0 | 0 | idêntica |
| `dim_tempo` | `marts.dim_tempo` | 101 | 101 | 0 | 0 | idêntica |
| `dim_pais` | `marts.dim_pais` | 219 | 219 | 0 | 0 | idêntica |
| `dim_localidade` | `marts.dim_localidade` | 1.085 | 1.085 | 0 | 0 | idêntica |
| `dim_perfil` | `marts.dim_perfil` | 134 | 134 | 0 | 0 | idêntica |
| `dim_amparo` | `marts.dim_amparo` | 90 | 90 | 0 | 0 | idêntica |
| `dim_ocupacao` | `marts.dim_ocupacao` | 93 | 93 | 0 | 0 | idêntica |
| `amparo_descricao_ano` | `marts.amparo_descricao_ano` | 463 | 463 | 0 | 0 | idêntica |
| `agregado_base` | `marts.agregado_base` | 82.545 | 82.545 | 0 | 0 | idêntica |
| `agregado_looker_nacionalidade` | `agregado_looker_nacionalidade` | 10.562 | 10.562 | 0 | 0 | idêntica |
| `agregado_looker_territorio` | `agregado_looker_territorio` | 9.839 | 9.839 | 0 | 0 | idêntica |

| Total por | Grupos | Grupos com diferença | Resultado |
|---|---|---|---|
| ano | 6 | 0 | idênticos |
| país de nacionalidade | 203 | 0 | idênticos |
| UF | 28 | 0 | idênticos |

| Arquivo de publicacao/ | SHA-256 (antes) | SHA-256 (dbt) | Resultado |
|---|---|---|---|
| `agregado_looker_nacionalidade.csv` | `f36362c0694c84be` | `f36362c0694c84be` | idêntico |
| `agregado_looker_territorio.csv` | `06ddb6c5f1109b47` | `06ddb6c5f1109b47` | idêntico |
