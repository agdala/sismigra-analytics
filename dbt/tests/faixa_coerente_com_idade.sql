-- C05/C06: em 2026 a faixa etária é derivada da idade com os mesmos cortes da fonte.
select id_registro, idade, faixa_etaria
from {{ ref('stg_registros') }}
where faixa_etaria_origem = 'derivada da idade'
  and faixa_etaria <> case
        when idade is null then 'Não especificado'
        when idade < 15 then '0 a 14 anos'
        when idade < 25 then '15 a 24 anos'
        when idade < 40 then '25 a 39 anos'
        when idade < 65 then '40 a 64 anos'
        else '65 anos ou mais'
      end
