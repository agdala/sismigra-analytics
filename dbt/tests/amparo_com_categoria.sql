-- A04: todo código de amparo dos dados tem categoria em ref/amparos.csv.
select distinct amparo_codigo
from {{ ref('int_registros_enriquecidos') }}
where amparo_codigo not in (select codigo from {{ ref('amparos') }})
