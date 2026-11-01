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
| Reidentificação por combinação rara de atributos (ex.: nacionalidade pouco frequente em município pequeno, com idade exata) | Os painéis públicos usam o `agregado_looker.csv`, sem município e sem idade exata. Recomenda-se não publicar células com menos de 5 registros. |
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
