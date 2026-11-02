-- Todo ano com registros tem cobertura declarada; só anos parciais (jan-set) têm ano_completo = false.
select ano, cobertura_registro, ano_completo
from {{ ref('dim_tempo') }}
where ano_com_registros
  and (cobertura_registro is null
       or ano_completo is null
       or ano_completo <> (cobertura_registro = 'jan-dez'))
