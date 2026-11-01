# Agregados protegidos: fonte oficial dos painéis

Esta é a **única pasta com dados versionada** no repositório, e a **única fonte permitida** para
painéis e arquivos publicados (Power BI, Looker Studio, planilhas, imagens). Os microdados, a
camada prata e o esquema estrela completo ficam fora do Git e não podem ser publicados.

| Arquivo | Conteúdo | Linhas |
|---|---|---|
| `agregado_looker_nacionalidade.csv` | Ano × país de nacionalidade × perfil × amparo (sem território) | cerca de 10,6 mil |
| `agregado_looker_territorio.csv` | Ano × UF de residência × perfil × amparo (sem país) | cerca de 9,8 mil |
| `metadados.json` | Data de geração, hashes SHA-256 dos arquivos de origem e resultado do controle de divulgação | |

Os arquivos são gerados por `python -m sismigra.pipeline` (ver o [README](../README.md)) e
substituídos a cada execução.

## Controle de divulgação (k = 5)

Nenhuma célula publicada tem de 1 a 4 registros. O método tem três passos
([`src/sismigra/divulgacao.py`](../src/sismigra/divulgacao.py)):

1. **Agrupamento:** as células pequenas têm atributos trocados por "Agrupado", em etapas.
2. **Supressão primária:** o que continuar abaixo de 5 fica com `qtd_registros` vazio e `suprimido = true`.
3. **Supressão secundária:** nenhum ano fica com uma única célula suprimida. Sem isso, o valor
   escondido poderia ser deduzido subtraindo as células publicadas do total do ano.

## Formato

| Item | Valor |
|---|---|
| Separador | vírgula (`,`) |
| Codificação | UTF-8, sem BOM |
| Separador decimal | ponto (`.`). Hoje todas as colunas numéricas são inteiras |
| Aspas | `"` só quando o valor contém vírgula |
| Booleano | `true` / `false` |
| Nulo | campo vazio |

## Colunas

Colunas comuns aos dois arquivos:

| Coluna | Tipo | Exemplo | Descrição |
|---|---|---|---|
| `ano_registro` | inteiro | `2025` | Ano do registro migratório (2021 a 2026) |
| `cobertura` | texto | `jan-dez` | Período coberto pelo arquivo do ano: `jan-dez` ou `jan-set` (2026) |
| `ano_completo` | booleano | `true` | `false` só em 2026. **Filtro obrigatório nas comparações de volume** |
| `sexo` | texto | `Feminino` | Masculino, Feminino, Não informado, Agrupado |
| `faixa_etaria` | texto | `25 a 39 anos` | 0 a 14, 15 a 24, 25 a 39, 40 a 64, 65 anos ou mais, Não especificado, Agrupada |
| `ordem_faixa_etaria` | inteiro | `3` | 1 a 5 na ordem das faixas; 9 = Não especificado ou Agrupada. Use para ordenar os gráficos |
| `categoria_ampla` | texto | `Proteção internacional e humanitária` | 6 categorias de amparo, Não informado ou Agrupada |
| `subgrupo_protecao` | texto | `Solicitantes de refúgio` | Solicitantes de refúgio, Refugiados reconhecidos, Acolhida de venezuelanos, Acolhida humanitária, Não se aplica, Agrupado |
| `tipologia_ajustada` | texto | `REUNIÃO FAMILIAR` | Tipologia do amparo (11 valores) ou Agrupada |
| `status_ativo` | booleano | `true` | Registro ativo. **Vazio quando o perfil foi agrupado** |
| `qtd_registros` | inteiro | `128` | **Medida.** Número de registros (sempre 5 ou mais). **Vazio quando suprimido** |
| `nivel_agrupamento` | inteiro | `0` | 0 = célula original; 1 a 6 = etapa em que foi agrupada |
| `suprimido` | booleano | `false` | `true` = contagem omitida pelo controle de divulgação |

Só em `agregado_looker_nacionalidade.csv`:

| Coluna | Tipo | Exemplo | Descrição |
|---|---|---|---|
| `pais_nacionalidade` | texto | `Venezuela` | País de nacionalidade padronizado; também `Outros países (ÁSIA)`, `Outros países`, `Não informado` |
| `iso3_nacionalidade` | texto | `VEN` | ISO 3166-1 alfa-3. Vazio em "Outros países", "Não informado" e "Ilhas Virgens (não especificado)" |
| `continente_nacionalidade` | texto | `AMÉRICA DO SUL` | Continente (como na fonte) ou Agrupado |

Só em `agregado_looker_territorio.csv`:

| Coluna | Tipo | Exemplo | Descrição |
|---|---|---|---|
| `regiao` | texto | `Sudeste` | Região geográfica ou Não informado |
| `uf_sigla` | texto | `SP` | Sigla da UF de residência ou Não informado |

## Como usar nos painéis

- **Medida:** sempre `SUM(qtd_registros)`. As células suprimidas ficam vazias e são ignoradas na soma.
- **Volumes:** filtre `ano_completo = true` (2021 a 2025). Use 2026 só em percentuais, rotulado como parcial.
- **Duas fontes separadas:** não junte nem relacione as duas tabelas, porque os totais seriam somados duas vezes.
- **"Agrupado":** mantenha esse valor visível nos gráficos por sexo, faixa etária ou amparo, para os totais não parecerem menores.
- **Mapa:** use `uf_sigla` como região geográfica do Brasil (subdivisão de país, ISO 3166-2 sem o prefixo `BR-`).
