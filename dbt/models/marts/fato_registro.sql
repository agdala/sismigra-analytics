{#-
  Grão: 1 linha = 1 registro migratório (CRNM ou DP-RNM). A fonte não é agregada: qtd_registros = 1.
  Linhas idênticas são mantidas: sem identificador pessoal, representam pessoas distintas.
-#}
select
    p.id_registro,
    p.ano_registro as sk_ano_registro,
    coalesce(p.ano_entrada, -1) as sk_ano_entrada,
    coalesce(mn.sk_pais, -1) as sk_pais_nascimento,
    coalesce(mc.sk_pais, -1) as sk_pais_nacionalidade,
    coalesce(l.sk_localidade, -1) as sk_localidade,
    pf.sk_perfil,
    p.amparo_codigo as sk_amparo,
    o.sk_ocupacao,
    p.status,
    p.status = 'Ativo' as status_ativo,
    p.idade,
    p.faixa_etaria_origem,
    p.municipio_status,
    p.flag_duplicata_exata,
    len(p.correcoes) > 0 as flag_corrigido,
    1 as qtd_registros
from {{ ref('int_registros_enriquecidos') }} p
left join {{ ref('int_mapa_pais') }} mn on mn.nome_fonte = p.pais_nascimento_fonte
left join {{ ref('int_mapa_pais') }} mc on mc.nome_fonte = p.pais_nacionalidade_fonte
left join {{ ref('dim_localidade') }} l
    on l.uf_sigla = p.uf_sigla
   and l.cod_municipio_ibge is not distinct from p.cod_municipio_ibge
   and l.tipo_membro = case when p.municipio_status in ('ibge', 'exceção manual') then 'município IBGE'
                            else p.municipio_status end
join {{ ref('dim_perfil') }} pf using (sexo, faixa_etaria, estado_civil)
join {{ ref('dim_ocupacao') }} o on o.ocupacao = p.profissao
