{#-
  Contagem por ano, território, nacionalidade, perfil e amparo. NÃO pode ser publicada: é a entrada
  do controle de divulgação (k = 5), aplicado em Python por src/sismigra/divulgacao.py, que gera os
  agregados protegidos de publicacao/.
-#}
select
    f.sk_ano_registro as ano_registro,
    t.cobertura_registro as cobertura,
    t.ano_completo,
    l.regiao,
    coalesce(l.uf_sigla, 'Não informado') as uf_sigla,
    pn.pais as pais_nacionalidade,
    pn.iso3 as iso3_nacionalidade,
    pn.continente as continente_nacionalidade,
    pf.sexo,
    pf.faixa_etaria,
    pf.ordem_faixa_etaria,
    a.categoria_ampla,
    a.subgrupo_protecao,
    a.tipologia_ajustada,
    a.classificacao,
    f.status_ativo,
    sum(f.qtd_registros) as qtd_registros
from {{ ref('fato_registro') }} f
join {{ ref('dim_tempo') }} t on t.sk_tempo = f.sk_ano_registro
join {{ ref('dim_localidade') }} l on l.sk_localidade = f.sk_localidade
join {{ ref('dim_pais') }} pn on pn.sk_pais = f.sk_pais_nacionalidade
join {{ ref('dim_perfil') }} pf on pf.sk_perfil = f.sk_perfil
join {{ ref('dim_amparo') }} a on a.sk_amparo = f.sk_amparo
group by all
order by all
