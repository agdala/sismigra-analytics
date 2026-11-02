{{ config(severity='warn') }}
-- A06 (alerta): mesmo código de amparo com mais de uma descrição de norma no mesmo ano.
select amparo_codigo, ano, count(*) as descricoes
from {{ ref('amparo_descricao_ano') }}
group by 1, 2
having count(*) > 1
