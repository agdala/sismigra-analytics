# Relatório de qualidade: SISMIGRA

Gerado em 2026-11-01T23:38:16+00:00 (UTC) pelo pipeline `python -m sismigra.pipeline`.

## Resumo

- Linhas lidas: **1.361.391**
- Aceitas na prata: **1.361.391** (100.0%)
- Rejeitadas: **0**
- Municípios especificados com código IBGE: **99.991%**

## Leitura por arquivo

| Arquivo | Ano | Lidas | Aceitas | Rejeitadas | Motivos |
|---|---|---|---|---|---|
| sismgra_janeiro_setembro_2026.csv | 2026 | 203.512 | 203.512 | 0 | nenhum |
| sismigra_2021.csv | 2021 | 168.321 | 168.321 | 0 | nenhum |
| sismigra_2022.csv | 2022 | 243.675 | 243.675 | 0 | nenhum |
| sismigra_2023.csv | 2023 | 232.193 | 232.193 | 0 | nenhum |
| sismigra_2024.csv | 2024 | 248.167 | 248.167 | 0 | nenhum |
| sismigra_janeiro_dezembro_2025.csv | 2025 | 265.523 | 265.523 | 0 | nenhum |

## Regras de rejeição

| Regra | Descrição |
|---|---|
| R00 | Linha malformada (número de colunas diferente do cabeçalho) |
| R01 | DATAREGISTRO ausente ou não numérico |
| R02 | DATAREGISTRO diferente do ano declarado para o arquivo em ref/fontes.csv |
| R03 | AMPARO ausente ou não numérico |

## Correções aplicadas (registros por ano)

| Regra | Descrição | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| C01 | Ano de entrada ausente, inválido (ex.: '--', '####', '0007') ou posterior ao registro: vira nulo | 16.707 | 26.977 | 16.663 | 24.575 | 41.285 | 35.889 |
| C02 | UF ausente ou inválida: localidade 'Não informado' | 358 | 563 | 745 | 1.087 | 2.104 | 1.964 |
| C03 | Município casado por exceção manual (ref/excecoes_municipios.csv) | 65 | 139 | 208 | 169 | 117 | 76 |
| C04 | Sexo ausente ou não declarado (5 grafias na fonte): 'Não informado' | 46 | 57 | 77 | 108 | 96 | 82 |
| C05 | Faixa etária não especificada na fonte ou idade ausente/inválida | 20.420 | 27.057 | 16.734 | 24.674 | 41.344 | 36.006 |
| C06 | Idade fora de 0 a 120 anos (ex.: negativa): descartada | 0 | 0 | 0 | 0 | 0 | 693 |
| C07 | Estado civil ausente, '-' ou DESCONHECIDO: 'Não informado' | 135 | 493 | 383 | 1.151 | 1.567 | 1.099 |
| C08 | Estado civil com '_' no lugar de espaço (ex.: SEPARADO_JUDICIALMENTE) | 0 | 0 | 0 | 0 | 83 | 57 |
| C09 | Classificação do registro ausente: 'Não informado' | 0 | 1 | 0 | 0 | 0 | 0 |

## Alertas

| Regra | Descrição | Resultado |
|---|---|---|
| A01 | Registros que pertencem a um grupo de linhas idênticas no mesmo arquivo (mantidos: sem identificador, são pessoas distintas) | 2021: 107.718, 2022: 172.453, 2023: 164.664, 2024: 174.556, 2025: 186.125, 2026: 88.486 |
| A02 | Município informado sem correspondência no IBGE nem exceção | MT/JUREMA (105) |
| A03 | País da fonte sem mapeamento em ref/paises.csv | nenhum |
| A04 | Código de amparo sem categoria em ref/amparos.csv | nenhum |
| A05 | Profissão 'MENOR' com faixa etária de 25 anos ou mais | 138 registros |
| A06 | Mesmo código de amparo com mais de uma descrição no mesmo ano | 49 em 2023 (2), 239 em 2023 (2), 265 em 2022 (2), 271 em 2022 (3), 271 em 2023 (2), 278 em 2022 (2), 278 em 2023 (2), 279 em 2022 (3), 279 em 2023 (2), 315 em 2023 (2), 315 em 2025 (2), 316 em 2023 (2), 318 em 2022 (2), 318 em 2023 (2), 319 em 2022 (2), 319 em 2023 (2) |

## Controle de divulgação (agregados do Looker Studio)

Nenhuma célula publicada tem de 1 a 4 registros. Células pequenas são primeiro agrupadas (atributos trocados por 'Agrupado', em etapas) e só o que continua abaixo do limiar é suprimido.

| Tabela | Limiar | Células publicadas | Células suprimidas | Registros suprimidos | % publicado |
|---|---|---|---|---|---|
| agregado_looker_nacionalidade | 5 | 10.562 | 6 | 24 | 99.998% |
| agregado_looker_territorio | 5 | 9.839 | 87 | 253 | 99.981% |

| Tabela | Etapa | Colunas agrupadas | Células agrupadas | Registros agrupados |
|---|---|---|---|---|
| agregado_looker_nacionalidade | 1 | tipologia_ajustada | 12.272 | 20.923 |
| agregado_looker_nacionalidade | 2 | subgrupo_protecao | 12.080 | 20.786 |
| agregado_looker_nacionalidade | 3 | sexo, faixa_etaria, ordem_faixa_etaria, status_ativo | 11.856 | 20.538 |
| agregado_looker_nacionalidade | 4 | categoria_ampla | 1.985 | 4.371 |
| agregado_looker_nacionalidade | 5 | pais_nacionalidade, iso3_nacionalidade | 582 | 1.438 |
| agregado_looker_nacionalidade | 6 | pais_nacionalidade, continente_nacionalidade | 10 | 31 |
| agregado_looker_territorio | 1 | tipologia_ajustada | 6.054 | 11.305 |
| agregado_looker_territorio | 2 | subgrupo_protecao | 5.773 | 10.965 |
| agregado_looker_territorio | 3 | sexo, faixa_etaria, ordem_faixa_etaria, status_ativo | 4.974 | 9.803 |
| agregado_looker_territorio | 4 | categoria_ampla | 220 | 572 |

## Municípios por situação

| Situação | Registros |
|---|---|
| ibge | 1.215.816 |
| não especificado | 137.875 |
| uf não informada | 6.821 |
| exceção manual | 774 |
| sem correspondência | 105 |
