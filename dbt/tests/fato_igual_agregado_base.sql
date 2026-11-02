-- A base dos agregados soma exatamente o número de registros do fato.
select
    (select count(*) from {{ ref('fato_registro') }}) as registros_fato,
    (select sum(qtd_registros) from {{ ref('agregado_base') }}) as soma_agregado
where (select count(*) from {{ ref('fato_registro') }})
   <> (select sum(qtd_registros) from {{ ref('agregado_base') }})
