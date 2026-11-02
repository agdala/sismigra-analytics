-- Referência de países: cada código ISO tem um único nome padronizado (evita país duplicado na dimensão).
select iso3, count(distinct nome_padronizado) as nomes
from {{ ref('paises') }}
where iso3 is not null
group by 1
having count(distinct nome_padronizado) > 1
