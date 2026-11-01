# Dicionário de dados

Este dicionário documenta **apenas campos que existem de fato** nos arquivos do SISMIGRA
(inventário completo em [`reports/inventario/inventario.md`](../reports/inventario/inventario.md))
e os campos derivados pelo pipeline, com a regra aplicada a cada um.

- **Sistema de origem:** SISMIGRA (Sistema de Registro Nacional Migratório), Polícia Federal.
- **Distribuidor:** OBMigra/UnB (Observatório das Migrações Internacionais), arquivos anuais em ZIP.
- **Cobertura:** 2021 a 2025 completos; 2026 de janeiro a setembro.
- **Grão:** 1 linha = 1 registro migratório (Carteira de Registro Nacional Migratório ou Documento
  Provisório de Registro Nacional Migratório). **Os dados não são agregados na fonte**: não existe
  coluna de quantidade, e cada linha conta como 1.
- **Sem identificador pessoal:** linhas idênticas são pessoas distintas com os mesmos atributos e
  são mantidas (regra A01).

Códigos de regra citados (R = rejeição, C = correção, A = alerta) estão em
[`src/sismigra/quality.py`](../src/sismigra/quality.py) e no relatório de qualidade.

---

## 1. Campos da fonte (camada bronze)

Todos chegam como texto, em UTF-8, separados por `;`. Nomes exatamente como no cabeçalho original.

| Campo | Definição | Anos | Observações do inventário |
|---|---|---|---|
| `DATAREGISTRO` | Ano em que o registro foi feito | 2021-2026 | Só o ano (ex.: `2025`), sem dia ou mês |
| `AMPARO` | Código do fundamento legal do registro | 2021-2026 | 90 códigos; às vezes com zero à esquerda (`049`) |
| `AMPARO_DESCRICAO` | Código e texto da norma | 2021-2026 | 12 códigos mudam de norma entre anos (ex.: 279 tem 6 portarias) |
| `CLASSIFICACAO_REGISTRO` | Tipo de registro: Temporário, Provisório, Residente, Fronteiriço | 2021-2026 | Determinado pelo código de amparo |
| `DATAENTRADA` | Ano de entrada no Brasil | 2021-2026 | Só o ano; contém `--`, `-`, `####`, vazios e anos impossíveis (`0007`, `1111`, futuros) |
| `UNIDADE_FED_RESIDENCIA` | Sigla da UF de residência | 2021-2026 | Contém `-` e vazios |
| `MUNICIPIO_RESIDENCIA` | Nome do município de residência, em maiúsculas | 2021-2026 | **Sem código IBGE**; cerca de 10% "NÃO ESPECIFICADO"; apóstrofos removidos (`HERVAL DOESTE`) |
| `PAIS_NASCIMENTO` | País de nascimento, por extenso | 2021-2026 | Sem código; grafias variadas (`KUAITE` e `KUWEIT`); inclui `BRASIL` |
| `PAIS_NACIONALIDADE` | País de nacionalidade, por extenso | 2021-2026 | Mesmas observações; inclui `APÁTRIDA` e `NACIONALIDADE INDEFINIDA` |
| `CONTINENTE` | Continente | 2021-2026 | Associado ao **país de nascimento** (não à nacionalidade) |
| `FAIXA_ETARIA` | Faixa etária | **2021-2025** | `0 \|-- 15 anos`, `15 \|-- 25`, `25 \|-- 40`, `40 \|-- 65`, `65 \|-- anos`, `NÃO ESPECIFICADO` |
| `IDADE` | Idade em anos | **2026** | Substitui `FAIXA_ETARIA`; 17% nulo; 693 valores negativos (até -2000) |
| `SEXO` | Sexo | 2021-2026 | Masculino, Feminino e 5 grafias de não informado |
| `ESTADO_CIVIL` | Estado civil | 2021-2026 | `SEPARADO_JUDICIALMENTE` e `SEPARADO JUDICIALMENTE` coexistem |
| `PROFISSAO` | Ocupação declarada (93 categorias) | 2021-2026 | Categorias fechadas, texto longo |
| `STATUS` | Situação do registro | 2021-2026 | Ativo (99,7%), Prazo vencido, Cancelado, Excluído, Inativo, Erro de Ofício |
| `CLASSIFICACAO_REVISADA` | Classificação recalculada pela fonte | 2021-2026 | Marca o amparo 290 como "NÃO APLICÁVEL" |
| `TIPOLOGIA_AMPAROS` | Agrupamento analítico do amparo, feito pela fonte (11 grupos) | 2021-2026 | Marca o amparo 290 como "NÃO APLICÁVEL" |

### Metadados da bronze (`data/bronze/manifest.json`)

| Campo | Definição | Origem |
|---|---|---|
| `arquivo_original` | Nome do ZIP ou CSV colocado em `data/landing/` | Sistema de arquivos |
| `sha256` | Hash do arquivo original (prova de integridade e de versão) | Calculado |
| `tamanho_bytes` | Tamanho do original | Sistema de arquivos |
| `csv`, `csv_sha256`, `caminho_bronze` | CSV extraído, seu hash e onde ficou | Calculado |
| `ingerido_em` | Data e hora da ingestão, em UTC | Relógio do sistema |
| `url_origem`, `distribuidor`, `ano`, `cobertura`, `ano_completo` | Procedência declarada | [`ref/fontes.csv`](../ref/fontes.csv) |

---

## 2. Camada prata (`data/silver/registros.parquet`)

| Campo | Tipo | Definição | Origem | Regra |
|---|---|---|---|---|
| `id_registro` | texto | Identificador técnico do registro | Derivado | 12 primeiros caracteres do SHA-256 do arquivo + número da linha. **Não identifica pessoa** |
| `arquivo_csv` | texto | CSV de origem | Bronze | Nome do arquivo |
| `linha_origem` | inteiro | Linha de dados no CSV (1 = primeira após o cabeçalho) | Bronze | Ordem de leitura |
| `ano_registro` | inteiro | Ano do registro | `DATAREGISTRO` | Inteiro; rejeita se ausente (R01) ou diferente do ano do arquivo (R02) |
| `amparo_codigo` | inteiro | Código do amparo legal | `AMPARO` | Inteiro (`049` vira 49); rejeita se ausente (R03) |
| `amparo_descricao` | texto | Norma do amparo, como na fonte | `AMPARO_DESCRICAO` | `-` vira nulo |
| `classificacao_registro` | texto | Tipo de registro | `CLASSIFICACAO_REGISTRO` | Ausente ou `-` vira "Não informado" (C09) |
| `classificacao_revisada` | texto | Classificação revisada da fonte | `CLASSIFICACAO_REVISADA` | Ausente vira "Não informado" |
| `tipologia_fonte` | texto | Tipologia da fonte, sem alteração | `TIPOLOGIA_AMPAROS` | Sem alteração |
| `ano_entrada` | inteiro | Ano de entrada no Brasil | `DATAENTRADA` | Válido entre 1900 e o ano do registro; senão nulo (C01) |
| `ano_entrada_fonte` | texto | Valor original de entrada | `DATAENTRADA` | Preservado para auditoria |
| `uf_sigla` | texto | UF de residência | `UNIDADE_FED_RESIDENCIA` | Maiúsculas; `-` ou vazio vira nulo (C02) |
| `municipio_fonte` | texto | Município como na fonte | `MUNICIPIO_RESIDENCIA` | Sem alteração |
| `cod_municipio_ibge` | texto(7) | Código IBGE do município | Derivado | Casamento por UF + nome normalizado (maiúsculas, sem acento, só letras) com a DTB; senão [`ref/excecoes_municipios.csv`](../ref/excecoes_municipios.csv) (C03) |
| `municipio_status` | texto | Resultado do casamento | Derivado | `ibge`, `exceção manual`, `não especificado`, `sem correspondência` (A02), `uf não informada` |
| `pais_nascimento_fonte` | texto | País de nascimento como na fonte | `PAIS_NASCIMENTO` | Sem alteração; ligado a ISO na ouro |
| `pais_nacionalidade_fonte` | texto | Nacionalidade como na fonte | `PAIS_NACIONALIDADE` | Sem alteração; ligado a ISO na ouro |
| `continente_fonte` | texto | Continente como na fonte | `CONTINENTE` | Sem alteração |
| `sexo` | texto | Sexo padronizado | `SEXO` | Masculino, Feminino ou "Não informado" (C04) |
| `idade` | inteiro | Idade em anos (só 2026) | `IDADE` | Válida entre 0 e 120; senão nula (C06) |
| `faixa_etaria` | texto | Faixa etária padronizada | `FAIXA_ETARIA` ou `IDADE` | `0 a 14`, `15 a 24`, `25 a 39`, `40 a 64`, `65 anos ou mais`, "Não especificado" (C05). Em 2026, derivada da idade com os mesmos cortes da fonte |
| `faixa_etaria_origem` | texto | Como a faixa foi obtida | Derivado | `fonte` (2021-2025) ou `derivada da idade` (2026) |
| `estado_civil` | texto | Estado civil padronizado | `ESTADO_CIVIL` | `_` vira espaço (C08); ausente, `-` ou DESCONHECIDO vira "Não informado" (C07) |
| `profissao` | texto | Ocupação | `PROFISSAO` | Ausente vira "Não informado" |
| `status` | texto | Situação do registro | `STATUS` | Ausente vira "Não informado" |
| `flag_duplicata_exata` | booleano | Pertence a um grupo de linhas idênticas no mesmo arquivo | Derivado | Alerta A01; **o registro é mantido** |
| `correcoes` | lista | Códigos das correções aplicadas ao registro | Derivado | Alimenta o relatório de qualidade |
| `sexo_fonte`, `idade_fonte`, `faixa_etaria_fonte`, `estado_civil_fonte` | texto | Valores originais | Fonte | Preservados para auditoria |

Registros rejeitados vão para `data/silver/rejeitados.parquet` com `arquivo_csv`, `linha_origem`,
`ano_arquivo` e `regra` (R00 a R03).

---

## 3. Camada ouro: esquema estrela (`data/gold/`)

Exportada em Parquet (`data/gold/parquet/`) e CSV (`data/gold/csv/`, separador `;`, UTF-8 com BOM
para o Excel). Chave `-1` = membro "Não informado" em todas as dimensões.

### `fato_registro`: grão = 1 registro migratório

| Campo | Definição | Regra |
|---|---|---|
| `id_registro` | Identificador técnico (ver prata) | Chave do fato |
| `sk_ano_registro` | Ano do registro | FK para `dim_tempo` |
| `sk_ano_entrada` | Ano de entrada no Brasil | FK para `dim_tempo`; -1 se inválido |
| `sk_pais_nascimento` | País de nascimento | FK para `dim_pais`; -1 se ausente |
| `sk_pais_nacionalidade` | País de nacionalidade | FK para `dim_pais`; -1 se ausente |
| `sk_localidade` | Município ou UF de residência | FK para `dim_localidade`; -1 se UF ausente |
| `sk_perfil` | Combinação de sexo, faixa etária e estado civil | FK para `dim_perfil` |
| `sk_amparo` | Código do amparo | FK para `dim_amparo` |
| `sk_ocupacao` | Ocupação | FK para `dim_ocupacao` |
| `status` | Situação do registro | Degenerada |
| `status_ativo` | `status = 'Ativo'` | Para o filtro padrão dos painéis |
| `idade` | Idade (só 2026) | Nula nos demais anos |
| `faixa_etaria_origem`, `municipio_status` | Rastreabilidade das derivações | Ver prata |
| `flag_duplicata_exata`, `flag_corrigido` | Indicadores de qualidade | `flag_corrigido` = recebeu ao menos uma correção C |
| `qtd_registros` | Medida | Sempre 1. Somar dá o número de registros |

### `dim_tempo`: grão = ano (papéis: ano do registro e ano de entrada)

| Campo | Definição | Origem / regra |
|---|---|---|
| `sk_tempo` | Chave = o próprio ano | -1 = não informado |
| `ano`, `decada` | Ano e década | Derivado |
| `cobertura_registro` | Período coberto pelo arquivo daquele ano (`jan-dez`, `jan-set`) | `ref/fontes.csv` |
| `ano_completo` | O ano de registro tem os 12 meses | `ref/fontes.csv`. **Use para não comparar 2026 parcial com anos completos** |
| `ano_com_registros` | Existe arquivo de registros desse ano | Derivado |

### `dim_pais`: grão = país padronizado (papéis: nascimento e nacionalidade)

| Campo | Definição | Origem / regra |
|---|---|---|
| `sk_pais` | Chave substituta | Ordem alfabética |
| `pais` | Nome padronizado em português | [`ref/paises.csv`](../ref/paises.csv): um nome por código ISO |
| `iso3` | Código ISO 3166-1 alfa-3 | Casamento automático com nomes ISO em português ou tabela manual. Exceções documentadas: `YUG` e `ANT` (históricos), `XXA` (apátrida, padrão ICAO), nulo para "Ilhas Virgens" (ambíguo) |
| `continente` | Continente | Valor mais frequente de `CONTINENTE` na fonte para esse país de nascimento |

### `dim_localidade`: grão = município IBGE (+ membros por UF)

| Campo | Definição | Origem / regra |
|---|---|---|
| `sk_localidade` | Chave substituta | Ordem por UF e código |
| `cod_municipio_ibge` | Código de 7 dígitos | DTB 2023 do IBGE ([`ref/municipios_ibge.csv`](../ref/municipios_ibge.csv)) |
| `municipio` | Nome oficial | DTB; ou "Não especificado" / "Sem correspondência no IBGE" |
| `uf_sigla`, `uf_nome`, `cod_uf`, `regiao` | UF e região geográfica | [`ref/uf.csv`](../ref/uf.csv) |
| `tipo_membro` | `município IBGE`, `não especificado`, `sem correspondência` | Derivado |

### `dim_perfil`: grão = sexo × faixa etária × estado civil

| Campo | Definição |
|---|---|
| `sk_perfil` | Chave substituta |
| `sexo`, `faixa_etaria`, `estado_civil` | Valores padronizados da prata |
| `ordem_faixa_etaria` | 1 a 5 para ordenar as faixas nos gráficos; 9 = não especificado |

### `dim_amparo`: grão = código de amparo

Hierarquia analítica revisada pela responsável pelo projeto em
[`ref/amparos.csv`](../ref/amparos.csv) (justificativa linha a linha em
[`docs/revisao/amparos_revisao.csv`](revisao/amparos_revisao.csv)).

| Campo | Definição | Origem / regra |
|---|---|---|
| `sk_amparo`, `amparo_codigo` | Código do amparo | Fonte |
| `descricao_recente` | Norma vigente no ano mais recente | Fonte; por ano em `amparo_descricao_ano` |
| `classificacao`, `classificacao_revisada`, `tipologia_fonte` | Como na fonte | Fonte |
| `tipologia_ajustada` | Tipologia corrigida | O amparo 290 deixa de ser "NÃO APLICÁVEL" e vira "SOLICITAÇÃO DE REFÚGIO (DP-RNM)" |
| `categoria_ampla` | Proteção internacional e humanitária; Mobilidade regional e acordos; Família; Trabalho e investimento; Estudo; Outros | Regra de negócio |
| `subgrupo_protecao` | Solicitantes de refúgio (290); Refugiados reconhecidos (287); Acolhida de venezuelanos (273, 299); Acolhida humanitária | Só para a categoria de proteção; demais = "Não se aplica" |

### `dim_ocupacao`

| Campo | Definição |
|---|---|
| `sk_ocupacao` | Chave substituta |
| `ocupacao` | Categoria de profissão da fonte (93 valores) |

### `amparo_descricao_ano`

Texto da norma de cada código por ano (`amparo_codigo`, `ano`, `amparo_descricao`, `registros`).
Necessária porque o mesmo código muda de portaria ao longo do tempo (alerta A06).

### `agregado_looker.csv`: tabela larga para o Looker Studio

Contagem de registros (`qtd_registros`) por `ano_registro`, `cobertura`, `ano_completo`, `regiao`,
`uf_sigla`, `pais_nacionalidade`, `iso3_nacionalidade`, `continente_nacionalidade`, `sexo`,
`faixa_etaria`, `ordem_faixa_etaria`, `categoria_ampla`, `subgrupo_protecao`,
`tipologia_ajustada`, `classificacao` e `status_ativo`. Separador vírgula. A soma de
`qtd_registros` é igual ao número de linhas do fato (testado).
