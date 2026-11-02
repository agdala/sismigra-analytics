-- Reconciliação da leitura: cada linha lida (válida ou malformada) termina aceita ou rejeitada.
with lidas as (
    select (select count(*) from {{ source('bronze', 'registros_brutos') }})
         + (select count(*) from {{ source('bronze', 'linhas_malformadas') }}) as n
),
destino as (
    select (select count(*) from {{ ref('stg_registros') }})
         + (select count(*) from {{ ref('stg_rejeitados') }}) as n
)
select lidas.n as lidas, destino.n as aceitas_mais_rejeitadas
from lidas, destino
where lidas.n <> destino.n
