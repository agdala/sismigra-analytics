# Nota de proteção de dados

## Natureza dos dados

- Os microdados do SISMIGRA usados aqui são **públicos**, divulgados pelo OBMigra/UnB
  (Observatório das Migrações Internacionais) a partir do Sistema de Registro Nacional Migratório.
- Os arquivos **não trazem identificadores pessoais**: não há nome, documento, número de registro,
  data de nascimento nem endereço.
- Os atributos são grossos: ano (sem dia ou mês), município, país, faixa etária (idade exata só em
  2026), sexo, estado civil, ocupação e amparo legal.
- A alta proporção de linhas idênticas (cerca de 60% entre 2021 e 2025) é evidência direta de que
  os registros não permitem distinguir pessoas.

## Riscos residuais e medidas adotadas

| Risco | Medida |
|---|---|
| Reidentificação por combinação rara de atributos (ex.: nacionalidade pouco frequente em UF pequena) | Os painéis públicos usam só os agregados com **controle de divulgação (k = 5)**: sem município, sem idade exata, país e UF em tabelas separadas, e nenhuma célula publicada com 1 a 4 registros. As células pequenas são agrupadas e, se ainda pequenas, suprimidas (`src/sismigra/divulgacao.py`, coberto por testes). |
| Inferência por diferença (total conhecido menos células publicadas) | A supressão residual atinge menos de 0,02% dos registros e células espalhadas por vários anos e UFs, o que torna a diferença pouco informativa. Os totais oficiais publicados no README são por ano, não por célula. |
| Redistribuição dos microdados | Nenhum dado bruto ou da prata é versionado (`.gitignore` bloqueia `data/`, `*.csv`, `*.zip` e `*.parquet`). Cada pessoa baixa os arquivos da fonte original. |
| `id_registro` interpretado como identificador pessoal | É um identificador técnico (hash do arquivo + número da linha), só para rastrear a linha de origem. Não se liga a nenhuma pessoa. |
| Uso discriminatório das análises | As análises são agregadas e descritivas, voltadas a políticas públicas e à proteção de pessoas migrantes e refugiadas. |

## Base legal e conformidade

- O tratamento de dados **anonimizados** não está sujeito à LGPD (Lei 13.709/2018, art. 12), desde
  que a anonimização não seja revertida com esforço razoável.
- Este projeto não usa dados de nenhum empregador, parceiro ou sistema interno. Só fontes públicas.

## O que fica no repositório

Versionados: código, SQL, testes, documentação, tabelas de referência (`ref/`), o inventário
estrutural (`reports/inventario/`, só estatísticas por coluna) e o relatório de qualidade (só contagens).

Não versionados: os ZIPs e CSVs do SISMIGRA e todas as saídas das camadas bronze, prata e ouro.
