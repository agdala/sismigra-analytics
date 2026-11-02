-- O código IBGE atribuído (direto ou por exceção) pertence à UF informada no registro.
select r.id_registro, r.uf_sigla, r.cod_municipio_ibge, m.uf_sigla as uf_do_codigo
from {{ ref('int_registros_enriquecidos') }} r
join {{ ref('municipios_ibge') }} m on m.cod_municipio_ibge = r.cod_municipio_ibge
where m.uf_sigla <> r.uf_sigla
