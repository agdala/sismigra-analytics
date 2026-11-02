{#-
  Grão: código de amparo. A hierarquia analítica (categoria_ampla > subgrupo > tipologia) vem de
  ref/amparos.csv, revisada pela responsável pelo projeto.
-#}
with obs as (
    select amparo_codigo, mode(classificacao_revisada) as classificacao_revisada
    from {{ ref('int_registros_enriquecidos') }}
    group by 1
)

select
    o.amparo_codigo as sk_amparo,
    o.amparo_codigo,
    coalesce(r.descricao_recente, 'Código sem referência') as descricao_recente,
    coalesce(r.classificacao, 'Não informado') as classificacao,
    o.classificacao_revisada,
    coalesce(r.tipologia_fonte, 'Não informado') as tipologia_fonte,
    coalesce(r.tipologia_ajustada, 'Não mapeado') as tipologia_ajustada,
    coalesce(r.categoria_ampla, 'Não mapeado') as categoria_ampla,
    coalesce(nullif(r.subgrupo_protecao, ''), 'Não se aplica') as subgrupo_protecao
from obs o
left join {{ ref('amparos') }} r on r.codigo = o.amparo_codigo
