-- A03: toda grafia de país da fonte (nascimento e nacionalidade) existe em ref/paises.csv.
select distinct p as pais_fonte
from (
    select unnest([pais_nascimento_fonte, pais_nacionalidade_fonte]) as p
    from {{ ref('int_registros_enriquecidos') }}
)
where p not in (select nome_fonte from {{ ref('paises') }})
