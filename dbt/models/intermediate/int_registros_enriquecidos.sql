{{ config(materialized="table") }}

{#-
  Registro completo e padronizado (equivalente à antiga camada prata), com a lista das correções
  aplicadas a cada linha. Alimenta o esquema estrela e o relatório de qualidade.
-#}
select
    c.*,
    (
        case when c.ano_entrada is null then ['C01'] else []::varchar[] end ||
        case when c.municipio_status = 'uf não informada' then ['C02'] else []::varchar[] end ||
        case when c.municipio_status = 'exceção manual' then ['C03'] else []::varchar[] end ||
        case when c.sexo = 'Não informado' then ['C04'] else []::varchar[] end ||
        case when c.faixa_etaria = 'Não especificado' then ['C05'] else []::varchar[] end ||
        case when c.idade_fonte is not null and c.idade is null then ['C06'] else []::varchar[] end ||
        case when c.estado_civil = 'Não informado' then ['C07'] else []::varchar[] end ||
        case when c.estado_civil_fonte like '%\_%' escape '\' then ['C08'] else []::varchar[] end ||
        case when c.classificacao_registro = 'Não informado' then ['C09'] else []::varchar[] end
    ) as correcoes
from {{ ref('int_registros_municipio') }} c
