{#-
  Países padronizados (um por código ISO), com chave substituta e continente.
  Grafias diferentes da fonte (ex.: KUAITE e KUWEIT) viram um só país. O continente vem da fonte,
  que o associa ao país de nascimento.
-#}
with continente as (
    select r.nome_padronizado, mode(p.continente_fonte) as continente
    from {{ ref('int_registros_enriquecidos') }} p
    join {{ ref('paises') }} r on r.nome_fonte = p.pais_nascimento_fonte
    group by 1
),

paises as (
    select distinct nome_padronizado, nullif(iso3, '') as iso3
    from {{ ref('paises') }}
    where nome_padronizado <> 'Não informado'
)

select
    cast(row_number() over (order by p.nome_padronizado) as integer) as sk_pais,
    p.nome_padronizado as pais,
    p.iso3,
    coalesce(c.continente, 'NÃO ESPECIFICADO') as continente
from paises p
left join continente c using (nome_padronizado)

union all

select -1, 'Não informado', null, 'NÃO ESPECIFICADO'
