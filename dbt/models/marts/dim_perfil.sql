{#- Dimensão "junk": combinações de sexo, faixa etária e estado civil. -#}
with combos as (
    select distinct sexo, faixa_etaria, estado_civil from {{ ref('int_registros_enriquecidos') }}
)

select
    cast(row_number() over (order by sexo, faixa_etaria, estado_civil) as integer) as sk_perfil,
    sexo,
    faixa_etaria,
    case faixa_etaria
        when '0 a 14 anos' then 1 when '15 a 24 anos' then 2 when '25 a 39 anos' then 3
        when '40 a 64 anos' then 4 when '65 anos ou mais' then 5 else 9
    end as ordem_faixa_etaria,
    estado_civil
from combos
