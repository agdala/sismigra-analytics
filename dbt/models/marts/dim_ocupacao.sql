select cast(row_number() over (order by profissao) as integer) as sk_ocupacao, profissao as ocupacao
from (select distinct profissao from {{ ref('int_registros_enriquecidos') }})
