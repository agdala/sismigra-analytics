{#- Registros que não entram na prata, com a regra de rejeição (R00 a R03). -#}
with base as (
    select
        arquivo_csv, linha_origem, ano_arquivo, DATAREGISTRO, AMPARO,
        try_cast(trim(DATAREGISTRO) as integer) as _ano_registro,
        try_cast(trim(AMPARO) as integer)       as _amparo
    from {{ source('bronze', 'registros_brutos') }}
)

select
    arquivo_csv, linha_origem, ano_arquivo,
    case
        when _ano_registro is null then 'R01'
        when _ano_registro <> ano_arquivo then 'R02'
        when _amparo is null then 'R03'
    end as regra,
    DATAREGISTRO, AMPARO
from base
where _ano_registro is null or _ano_registro <> ano_arquivo or _amparo is null

union all

select arquivo_csv, linha_origem, ano_arquivo, 'R00' as regra, null as DATAREGISTRO, null as AMPARO
from {{ source('bronze', 'linhas_malformadas') }}
