{#- Texto da norma por ano: o mesmo código muda de portaria ao longo do tempo (alerta A06). -#}
select amparo_codigo, ano_registro as ano, amparo_descricao, count(*) as registros
from {{ ref('int_registros_enriquecidos') }}
group by all
