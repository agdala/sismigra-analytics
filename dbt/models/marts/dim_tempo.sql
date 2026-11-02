{#- Um ano por linha. Atende dois papéis: ano do registro e ano de entrada no Brasil. -#}
with anos as (
    select distinct ano_registro as ano from {{ ref('int_registros_enriquecidos') }}
    union
    select distinct ano_entrada from {{ ref('int_registros_enriquecidos') }} where ano_entrada is not null
)

select
    a.ano as sk_tempo,
    a.ano,
    (a.ano // 10) * 10 as decada,
    f.cobertura as cobertura_registro,
    f.ano_completo,
    f.ano is not null as ano_com_registros
from anos a
left join {{ ref('fontes') }} f on f.ano = a.ano

union all

select -1, null, null, null, null, false
