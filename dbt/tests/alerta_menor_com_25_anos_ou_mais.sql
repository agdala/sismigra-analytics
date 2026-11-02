{{ config(severity='warn') }}
-- A05 (alerta): profissão "MENOR" com faixa etária de 25 anos ou mais. Não bloqueia o pipeline.
select id_registro, profissao, faixa_etaria
from {{ ref('int_registros_enriquecidos') }}
where profissao like 'MENOR%'
  and faixa_etaria in ('25 a 39 anos', '40 a 64 anos', '65 anos ou mais')
