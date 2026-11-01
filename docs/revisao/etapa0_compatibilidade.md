# Etapa 0: compatibilidade entre anos (2021 a 2026)

Gerado a partir de `reports/inventario/inventario.json`. Seis arquivos, 1.361.391 registros.

## Volumes e cobertura

| Ano | Arquivo | Registros | Cobertura | Duplicatas exatas |
|---|---|---|---|---|
| 2021 | sismigra_2021.csv | 168.321 | jan-dez | 54,1% |
| 2022 | sismigra_2022.csv | 243.675 | jan-dez | 61,9% |
| 2023 | sismigra_2023.csv | 232.193 | jan-dez | 61,5% |
| 2024 | sismigra_2024.csv | 248.167 | jan-dez | 60,4% |
| 2025 | sismigra_janeiro_dezembro_2025.csv | 265.523 | jan-dez | 59,8% |
| 2026 | sismgra_janeiro_setembro_2026.csv | 203.512 | **jan-set (parcial)** | 35,3% |

Todos os arquivos: UTF-8, separador `;`, 17 colunas, `DATAREGISTRO` contém apenas o ano.

## Matriz de colunas

16 colunas são idênticas em nome nos seis anos. Única quebra de layout:

| Coluna | 2021 a 2025 | 2026 |
|---|---|---|
| `FAIXA_ETARIA` | presente (5 faixas + NÃO ESPECIFICADO) | **ausente** |
| `IDADE` | ausente | **presente** (inteiro; 17,4% nulo; 693 negativos, até -2000) |

Harmonização: em 2026 a faixa etária é derivada da idade com os mesmos cortes da fonte
(`0 |-- 15`, `15 |-- 25`, `25 |-- 40`, `40 |-- 65`, `65 |--`). Idade nula ou negativa vira
NÃO ESPECIFICADO, com motivo registrado. A idade exata é mantida só para 2026.

A queda de duplicatas em 2026 (35% contra cerca de 60%) coincide com a troca da faixa pela
idade exata: é evidência de que as duplicatas são pessoas distintas com atributos iguais.

## Variações de valores entre anos

| Coluna | Variação | Tratamento |
|---|---|---|
| SEXO | `Não especificado`, `Não Declarado`, `Nao Declarado`, `-`, nulo | unificar em "Não informado" |
| ESTADO_CIVIL | `SEPARADO_JUDICIALMENTE` (2025+), `-`, nulo | unificar grafia; "Não informado" |
| CONTINENTE | `ANTÁRCTICA` (1 registro em 2026); `NÃO ESPECIFICADO` some em 2026 | manter; alerta |
| CLASSIFICACAO_REGISTRO | `-` (1 registro em 2022) | "Não informado" |
| AMPARO | 90 códigos; código `0` (1 registro em 2022); zeros à esquerda (`049`) | chave inteira |
| AMPARO_DESCRICAO | 12 códigos mudam de norma entre anos (ex.: 279 tem 6 portarias) | descrição por ano de vigência |

Cada código de amparo tem uma única tipologia e uma única classificação nos seis anos.

## Municípios x IBGE (DTB 2023)

| Ano | Especificados que casaram |
|---|---|
| 2021 | 99,96% |
| 2022 | 99,94% |
| 2023 | 99,89% |
| 2024 | 99,91% |
| 2025 | 99,94% |
| 2026 | 99,94% |

Os 7 nomes restantes estão em `ref/excecoes_municipios.csv`.

## Países

262 nomes distintos (nascimento e nacionalidade, todos os anos). Mapeamento para ISO 3166
será feito em `ref/paises.csv`.

## Ingestão

Os links do SharePoint do OBMigra exigem autenticação institucional (HTTP 401 em teste
automatizado). Decisão: ingestão manual via `data/landing/`, com hash SHA-256 por arquivo.
