-- Camada ouro: esquema estrela.
--
-- Grão do fato: 1 linha = 1 registro migratório (CRNM ou DP-RNM) do SISMIGRA.
-- Os dados NÃO são agregados na fonte; a medida qtd_registros vale 1 em cada linha.
-- Linhas idênticas são mantidas: sem identificador pessoal, elas representam pessoas distintas.
--
-- Entrada: prata, ref_* (carregadas por src/sismigra/silver.py)
-- Chaves substitutas: -1 = membro "Não informado" em todas as dimensões.

-- ---------------------------------------------------------------- dim_tempo
-- Um ano por linha. Atende dois papéis: ano do registro e ano de entrada no Brasil.
CREATE OR REPLACE TABLE dim_tempo AS
WITH anos AS (
    SELECT DISTINCT ano_registro AS ano FROM prata
    UNION SELECT DISTINCT ano_entrada FROM prata WHERE ano_entrada IS NOT NULL
)
SELECT
    a.ano AS sk_tempo,
    a.ano,
    (a.ano // 10) * 10 AS decada,
    f.cobertura AS cobertura_registro,
    f.ano_completo,
    f.ano IS NOT NULL AS ano_com_registros
FROM anos a
LEFT JOIN ref_fontes f ON f.ano = a.ano
UNION ALL
SELECT -1, NULL, NULL, NULL, NULL, false;

-- ---------------------------------------------------------------- dim_pais
-- Grão: país padronizado. Grafias diferentes da fonte (ex.: KUAITE e KUWEIT) viram um só país.
-- O continente vem da própria fonte, que o associa ao país de nascimento.
CREATE OR REPLACE TABLE dim_pais AS
WITH continente AS (
    SELECT r.nome_padronizado, mode(p.continente_fonte) AS continente
    FROM prata p JOIN ref_paises r ON r.nome_fonte = p.pais_nascimento_fonte
    GROUP BY 1
),
paises AS (
    SELECT DISTINCT nome_padronizado, nullif(iso3, '') AS iso3
    FROM ref_paises WHERE nome_padronizado <> 'Não informado'
)
SELECT
    CAST(row_number() OVER (ORDER BY p.nome_padronizado) AS INTEGER) AS sk_pais,
    p.nome_padronizado AS pais,
    p.iso3,
    coalesce(c.continente, 'NÃO ESPECIFICADO') AS continente
FROM paises p LEFT JOIN continente c USING (nome_padronizado)
UNION ALL
SELECT -1, 'Não informado', NULL, 'NÃO ESPECIFICADO';

CREATE OR REPLACE TABLE map_pais AS
SELECT r.nome_fonte, coalesce(d.sk_pais, -1) AS sk_pais
FROM ref_paises r LEFT JOIN dim_pais d ON d.pais = r.nome_padronizado AND r.nome_padronizado <> 'Não informado';

-- ---------------------------------------------------------------- dim_localidade
-- Grão: município IBGE. Para registros sem município, um membro por UF ("Não especificado"
-- ou "Sem correspondência no IBGE"); para UF ausente, o membro -1.
CREATE OR REPLACE TABLE dim_localidade AS
WITH usados AS (
    SELECT DISTINCT
        uf_sigla,
        cod_municipio_ibge,
        CASE municipio_status
            WHEN 'não especificado' THEN 'Não especificado'
            WHEN 'sem correspondência' THEN 'Sem correspondência no IBGE'
        END AS rotulo,
        CASE WHEN municipio_status IN ('ibge', 'exceção manual') THEN 'município IBGE' ELSE municipio_status END
            AS tipo_membro
    FROM prata
    WHERE municipio_status <> 'uf não informada'
)
SELECT
    CAST(row_number() OVER (ORDER BY u.uf_sigla, u.cod_municipio_ibge NULLS LAST, u.tipo_membro) AS INTEGER)
        AS sk_localidade,
    u.cod_municipio_ibge,
    coalesce(m.municipio, u.rotulo) AS municipio,
    u.uf_sigla,
    uf.uf_nome,
    uf.cod_uf,
    uf.regiao,
    u.tipo_membro
FROM usados u
JOIN ref_uf uf ON uf.uf_sigla = u.uf_sigla
LEFT JOIN ref_municipios m ON m.cod_municipio_ibge = u.cod_municipio_ibge
UNION ALL
SELECT -1, NULL, 'Não informado', NULL, 'Não informado', NULL, 'Não informado', 'uf não informada';

-- ---------------------------------------------------------------- dim_perfil
-- Dimensão "junk": combinações de sexo, faixa etária e estado civil.
CREATE OR REPLACE TABLE dim_perfil AS
WITH combos AS (SELECT DISTINCT sexo, faixa_etaria, estado_civil FROM prata)
SELECT
    CAST(row_number() OVER (ORDER BY sexo, faixa_etaria, estado_civil) AS INTEGER) AS sk_perfil,
    sexo,
    faixa_etaria,
    CASE faixa_etaria
        WHEN '0 a 14 anos' THEN 1 WHEN '15 a 24 anos' THEN 2 WHEN '25 a 39 anos' THEN 3
        WHEN '40 a 64 anos' THEN 4 WHEN '65 anos ou mais' THEN 5 ELSE 9
    END AS ordem_faixa_etaria,
    estado_civil
FROM combos;

-- ---------------------------------------------------------------- dim_amparo
-- Grão: código de amparo. A hierarquia analítica (categoria_ampla > subgrupo > tipologia)
-- vem de ref/amparos.csv, revisada pela responsável pelo projeto.
CREATE OR REPLACE TABLE dim_amparo AS
WITH obs AS (
    SELECT amparo_codigo, mode(classificacao_revisada) AS classificacao_revisada
    FROM prata GROUP BY 1
)
SELECT
    o.amparo_codigo AS sk_amparo,
    o.amparo_codigo,
    coalesce(r.descricao_recente, 'Código sem referência') AS descricao_recente,
    coalesce(r.classificacao, 'Não informado') AS classificacao,
    o.classificacao_revisada,
    coalesce(r.tipologia_fonte, 'Não informado') AS tipologia_fonte,
    coalesce(r.tipologia_ajustada, 'Não mapeado') AS tipologia_ajustada,
    coalesce(r.categoria_ampla, 'Não mapeado') AS categoria_ampla,
    coalesce(nullif(r.subgrupo_protecao, ''), 'Não se aplica') AS subgrupo_protecao
FROM obs o LEFT JOIN ref_amparos r ON r.codigo = o.amparo_codigo;

-- Texto da norma por ano (o mesmo código muda de portaria ao longo do tempo).
CREATE OR REPLACE TABLE amparo_descricao_ano AS
SELECT amparo_codigo, ano_registro AS ano, amparo_descricao, count(*) AS registros
FROM prata GROUP BY ALL;

-- ---------------------------------------------------------------- dim_ocupacao
CREATE OR REPLACE TABLE dim_ocupacao AS
SELECT CAST(row_number() OVER (ORDER BY profissao) AS INTEGER) AS sk_ocupacao, profissao AS ocupacao
FROM (SELECT DISTINCT profissao FROM prata);

-- ---------------------------------------------------------------- fato_registro
CREATE OR REPLACE TABLE fato_registro AS
SELECT
    p.id_registro,
    p.ano_registro AS sk_ano_registro,
    coalesce(p.ano_entrada, -1) AS sk_ano_entrada,
    coalesce(mn.sk_pais, -1) AS sk_pais_nascimento,
    coalesce(mc.sk_pais, -1) AS sk_pais_nacionalidade,
    coalesce(l.sk_localidade, -1) AS sk_localidade,
    pf.sk_perfil,
    p.amparo_codigo AS sk_amparo,
    o.sk_ocupacao,
    p.status,
    p.status = 'Ativo' AS status_ativo,
    p.idade,
    p.faixa_etaria_origem,
    p.municipio_status,
    p.flag_duplicata_exata,
    len(p.correcoes) > 0 AS flag_corrigido,
    1 AS qtd_registros
FROM prata p
LEFT JOIN map_pais mn ON mn.nome_fonte = p.pais_nascimento_fonte
LEFT JOIN map_pais mc ON mc.nome_fonte = p.pais_nacionalidade_fonte
LEFT JOIN dim_localidade l
    ON l.uf_sigla = p.uf_sigla
   AND l.cod_municipio_ibge IS NOT DISTINCT FROM p.cod_municipio_ibge
   AND l.tipo_membro = CASE WHEN p.municipio_status IN ('ibge', 'exceção manual') THEN 'município IBGE'
                            ELSE p.municipio_status END
JOIN dim_perfil pf USING (sexo, faixa_etaria, estado_civil)
JOIN dim_ocupacao o ON o.ocupacao = p.profissao;

-- ---------------------------------------------------------------- agregado para Looker Studio
-- Tabela larga e leve: contagem por ano, território, nacionalidade, perfil e amparo.
CREATE OR REPLACE TABLE agregado_looker AS
SELECT
    f.sk_ano_registro AS ano_registro,
    t.cobertura_registro AS cobertura,
    t.ano_completo,
    l.regiao,
    l.uf_sigla,
    pn.pais AS pais_nacionalidade,
    pn.iso3 AS iso3_nacionalidade,
    pn.continente AS continente_nacionalidade,
    pf.sexo,
    pf.faixa_etaria,
    pf.ordem_faixa_etaria,
    a.categoria_ampla,
    a.subgrupo_protecao,
    a.tipologia_ajustada,
    a.classificacao,
    f.status_ativo,
    sum(f.qtd_registros) AS qtd_registros
FROM fato_registro f
JOIN dim_tempo t ON t.sk_tempo = f.sk_ano_registro
JOIN dim_localidade l ON l.sk_localidade = f.sk_localidade
JOIN dim_pais pn ON pn.sk_pais = f.sk_pais_nacionalidade
JOIN dim_perfil pf ON pf.sk_perfil = f.sk_perfil
JOIN dim_amparo a ON a.sk_amparo = f.sk_amparo
GROUP BY ALL
ORDER BY ALL;
