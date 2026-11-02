{#- Casamento do município com a DTB do IBGE (UF + nome normalizado) e com as exceções manuais (C03). -#}
with municipios as (
    select *, {{ norm_nome('municipio') }} as nome_norm
    from {{ ref('municipios_ibge') }}
)

select
    r.*,
    coalesce(m.cod_municipio_ibge,
             case when e.cod_municipio_ibge <> '' then e.cod_municipio_ibge end) as cod_municipio_ibge,
    case
        when r.uf_sigla is null or r.uf_sigla not in (select uf_sigla from {{ ref('uf') }}) then 'uf não informada'
        when upper(r.municipio_fonte) = 'NÃO ESPECIFICADO' or {{ ausente('r.municipio_fonte') }} then 'não especificado'
        when m.cod_municipio_ibge is not null then 'ibge'
        when e.cod_municipio_ibge <> '' then 'exceção manual'
        else 'sem correspondência'
    end as municipio_status
from {{ ref('stg_registros') }} r
left join municipios m
    on m.uf_sigla = r.uf_sigla and m.nome_norm = {{ norm_nome('r.municipio_fonte') }}
left join {{ ref('excecoes_municipios') }} e
    on e.uf = r.uf_sigla and upper(e.municipio_fonte) = upper(r.municipio_fonte)
