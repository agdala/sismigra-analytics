{#-
  Grão: município IBGE. Para registros sem município, um membro por UF ("Não especificado" ou
  "Sem correspondência no IBGE"); para UF ausente, o membro -1.
-#}
with usados as (
    select distinct
        uf_sigla,
        cod_municipio_ibge,
        case municipio_status
            when 'não especificado' then 'Não especificado'
            when 'sem correspondência' then 'Sem correspondência no IBGE'
        end as rotulo,
        case when municipio_status in ('ibge', 'exceção manual') then 'município IBGE' else municipio_status end
            as tipo_membro
    from {{ ref('int_registros_enriquecidos') }}
    where municipio_status <> 'uf não informada'
)

select
    cast(row_number() over (order by u.uf_sigla, u.cod_municipio_ibge nulls last, u.tipo_membro) as integer)
        as sk_localidade,
    u.cod_municipio_ibge,
    coalesce(m.municipio, u.rotulo) as municipio,
    u.uf_sigla,
    uf.uf_nome,
    uf.cod_uf,
    uf.regiao,
    u.tipo_membro
from usados u
join {{ ref('uf') }} uf on uf.uf_sigla = u.uf_sigla
left join {{ ref('municipios_ibge') }} m on m.cod_municipio_ibge = u.cod_municipio_ibge

union all

select -1, null, 'Não informado', null, 'Não informado', null, 'Não informado', 'uf não informada'
