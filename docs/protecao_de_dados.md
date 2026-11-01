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

## Regra de publicação

**Qualquer painel ou arquivo publicado deve usar apenas os agregados protegidos:**
`agregado_looker_nacionalidade.csv` e `agregado_looker_territorio.csv`, da pasta
[`publicacao/`](../publicacao/) (fonte oficial dos painéis, versionada no repositório), gerados por
[`src/sismigra/divulgacao.py`](../src/sismigra/divulgacao.py) com limiar k = 5.

| Uso | Fonte permitida |
|---|---|
| Painel Power BI publicado (`.pbix`, Power BI Service, "Publicar na Web") | Só os agregados protegidos |
| Painel Looker Studio | Só os agregados protegidos |
| CSV, planilha ou imagem compartilhada | Só os agregados protegidos (ou gráficos feitos a partir deles) |
| Validação, exploração e testes locais | Esquema estrela da camada ouro e camada prata |

- O esquema estrela completo (`data/gold/parquet/` e `data/gold/csv/`) e a camada prata contêm
  registros individuais e células com menos de 5 registros. **Não podem ser publicados**, nem
  embutidos num `.pbix` compartilhado.
- Um número calculado localmente sobre o esquema estrela só pode ser publicado se passar pelo
  mesmo controle de divulgação (nenhuma célula de 1 a 4 registros).
- No Power BI, as duas tabelas protegidas entram como tabelas independentes, sem relacionamento,
  e as células suprimidas (contagem vazia) são ignoradas na soma.

## Riscos residuais e medidas adotadas

| Risco | Medida |
|---|---|
| Reidentificação por combinação rara de atributos (ex.: nacionalidade pouco frequente em UF pequena) | Os painéis públicos usam só os agregados com **controle de divulgação (k = 5)**: sem município, sem idade exata, país e UF em tabelas separadas, e nenhuma célula publicada com 1 a 4 registros. As células pequenas são agrupadas e, se ainda pequenas, suprimidas (`src/sismigra/divulgacao.py`, coberto por testes). |
| Inferência por diferença (total conhecido menos células publicadas) | O README publica o total exato de cada ano. A **supressão secundária** garante que nenhum ano tenha exatamente uma célula suprimida: quando isso aconteceria, a menor célula publicada do mesmo ano também é suprimida, e a subtração revela só a soma de duas ou mais células (testado). |
| Redistribuição dos microdados | Nenhum dado bruto, da prata ou do esquema estrela é versionado (`.gitignore` bloqueia `data/`, `*.csv`, `*.zip` e `*.parquet`). A única exceção são os CSVs de `publicacao/`, já protegidos. Cada pessoa baixa os microdados da fonte original. |
| `id_registro` interpretado como identificador pessoal | É um identificador técnico (hash do arquivo + número da linha), só para rastrear a linha de origem. Não se liga a nenhuma pessoa. |
| Uso discriminatório das análises | As análises são agregadas e descritivas, voltadas a políticas públicas e à proteção de pessoas migrantes e refugiadas. |

## Base legal e conformidade

- O tratamento de dados **anonimizados** não está sujeito à LGPD (Lei 13.709/2018, art. 12), desde
  que a anonimização não seja revertida com esforço razoável.
- Este projeto não usa dados de nenhum empregador, parceiro ou sistema interno. Só fontes públicas.

## O que fica no repositório

Versionados: código, SQL, testes, documentação, tabelas de referência (`ref/`), o inventário
estrutural (`reports/inventario/`, só estatísticas por coluna), o relatório de qualidade (só contagens)
e os agregados protegidos de `publicacao/` (k = 5).

Não versionados: os ZIPs e CSVs do SISMIGRA e todas as saídas das camadas bronze, prata e ouro.
