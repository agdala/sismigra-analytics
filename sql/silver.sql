-- Camada prata: padronização, tipos, chaves IBGE/ISO, ausentes e regras de qualidade.
--
-- Entrada (criada por src/sismigra/silver.py):
--   bruto            todas as colunas como texto + arquivo_csv, linha_origem, ano_arquivo, sha12
--   ref_uf, ref_municipios, ref_excecoes, ref_paises, ref_amparos
--
-- Saída:
--   prata            registros aceitos, padronizados, com lista de correções aplicadas
--   rejeitados       registros rejeitados, com o motivo
--
-- Convenção dos códigos de regra (ver src/sismigra/quality.py):
--   Rxx = rejeição (o registro sai da prata)
--   Cxx = correção com marcação (o registro fica; o valor é padronizado ou vira "Não informado")

-- Normalização para comparar nomes: maiúsculas, sem acento, só letras.
CREATE OR REPLACE MACRO norm_nome(x) AS regexp_replace(upper(strip_accents(x)), '[^A-Z]', '', 'g');

-- Texto vazio, "-", "--" e "####" significam ausência na fonte.
CREATE OR REPLACE MACRO ausente(x) AS (x IS NULL OR trim(x) IN ('', '-', '--', '####'));

CREATE OR REPLACE TABLE base AS
SELECT
    b.*,
    TRY_CAST(trim(b.DATAREGISTRO) AS INTEGER) AS _ano_registro,
    TRY_CAST(trim(b.AMPARO) AS INTEGER)       AS _amparo,
    TRY_CAST(trim(b.DATAENTRADA) AS INTEGER)  AS _ano_entrada,
    TRY_CAST(trim(b.IDADE) AS INTEGER)        AS _idade
FROM bruto b;

-- ---------------------------------------------------------------- rejeições
CREATE OR REPLACE TABLE rejeitados AS
SELECT
    arquivo_csv, linha_origem, ano_arquivo,
    CASE
        WHEN _ano_registro IS NULL THEN 'R01'
        WHEN _ano_registro <> ano_arquivo THEN 'R02'
        WHEN _amparo IS NULL THEN 'R03'
    END AS regra,
    DATAREGISTRO, AMPARO
FROM base
WHERE _ano_registro IS NULL OR _ano_registro <> ano_arquivo OR _amparo IS NULL;

-- ---------------------------------------------------------------- padronização
CREATE OR REPLACE TABLE prata AS
WITH aceitos AS (
    SELECT * FROM base
    WHERE _ano_registro IS NOT NULL AND _ano_registro = ano_arquivo AND _amparo IS NOT NULL
),
padronizado AS (
    SELECT
        a.sha12 || '-' || lpad(CAST(a.linha_origem AS VARCHAR), 7, '0') AS id_registro,
        a.arquivo_csv,
        a.linha_origem,
        a._ano_registro AS ano_registro,

        -- amparo legal
        a._amparo AS amparo_codigo,
        nullif(trim(a.AMPARO_DESCRICAO), '-') AS amparo_descricao,
        CASE WHEN ausente(a.CLASSIFICACAO_REGISTRO) THEN 'Não informado' ELSE trim(a.CLASSIFICACAO_REGISTRO) END
            AS classificacao_registro,
        CASE WHEN ausente(a.CLASSIFICACAO_REVISADA) THEN 'Não informado' ELSE trim(a.CLASSIFICACAO_REVISADA) END
            AS classificacao_revisada,
        trim(a.TIPOLOGIA_AMPAROS) AS tipologia_fonte,

        -- ano de entrada: válido entre 1900 e o ano do registro
        CASE WHEN a._ano_entrada BETWEEN 1900 AND a._ano_registro THEN a._ano_entrada END AS ano_entrada,
        nullif(trim(a.DATAENTRADA), '') AS ano_entrada_fonte,

        -- localidade
        CASE WHEN ausente(a.UNIDADE_FED_RESIDENCIA) THEN NULL ELSE upper(trim(a.UNIDADE_FED_RESIDENCIA)) END
            AS uf_sigla,
        trim(a.MUNICIPIO_RESIDENCIA) AS municipio_fonte,

        -- países
        trim(a.PAIS_NASCIMENTO) AS pais_nascimento_fonte,
        trim(a.PAIS_NACIONALIDADE) AS pais_nacionalidade_fonte,
        trim(a.CONTINENTE) AS continente_fonte,

        -- perfil
        CASE upper(strip_accents(trim(coalesce(a.SEXO, ''))))
            WHEN 'MASCULINO' THEN 'Masculino'
            WHEN 'FEMININO' THEN 'Feminino'
            ELSE 'Não informado'
        END AS sexo,
        a.SEXO AS sexo_fonte,
        CASE WHEN a._idade BETWEEN 0 AND 120 THEN a._idade END AS idade,
        a.IDADE AS idade_fonte,
        a.FAIXA_ETARIA AS faixa_etaria_fonte,
        CASE
            WHEN ausente(a.ESTADO_CIVIL) OR upper(trim(a.ESTADO_CIVIL)) = 'DESCONHECIDO' THEN 'Não informado'
            ELSE replace(upper(trim(a.ESTADO_CIVIL)), '_', ' ')
        END AS estado_civil,
        a.ESTADO_CIVIL AS estado_civil_fonte,
        CASE WHEN ausente(a.PROFISSAO) THEN 'Não informado' ELSE trim(a.PROFISSAO) END AS profissao,
        CASE WHEN ausente(a.STATUS) THEN 'Não informado' ELSE trim(a.STATUS) END AS status,

        -- duplicata exata: mesma linha inteira repetida no mesmo arquivo (é mantida)
        count(*) OVER (PARTITION BY a.arquivo_csv, a.DATAREGISTRO, a.AMPARO, a.AMPARO_DESCRICAO,
            a.CLASSIFICACAO_REGISTRO, a.DATAENTRADA, a.UNIDADE_FED_RESIDENCIA, a.MUNICIPIO_RESIDENCIA,
            a.PAIS_NASCIMENTO, a.PAIS_NACIONALIDADE, a.CONTINENTE, a.FAIXA_ETARIA, a.IDADE, a.SEXO,
            a.ESTADO_CIVIL, a.PROFISSAO, a.STATUS, a.CLASSIFICACAO_REVISADA, a.TIPOLOGIA_AMPAROS) > 1
            AS flag_duplicata_exata
    FROM aceitos a
),
com_faixa AS (
    SELECT
        p.*,
        -- faixa etária com os mesmos cortes da fonte: [0,15) [15,25) [25,40) [40,65) [65,+)
        CASE
            WHEN p.faixa_etaria_fonte IS NOT NULL THEN
                CASE trim(p.faixa_etaria_fonte)
                    WHEN '0 |-- 15 anos'  THEN '0 a 14 anos'
                    WHEN '15 |-- 25 anos' THEN '15 a 24 anos'
                    WHEN '25 |-- 40 anos' THEN '25 a 39 anos'
                    WHEN '40 |-- 65 anos' THEN '40 a 64 anos'
                    WHEN '65 |-- anos'    THEN '65 anos ou mais'
                    ELSE 'Não especificado'
                END
            WHEN p.idade IS NULL THEN 'Não especificado'
            WHEN p.idade < 15 THEN '0 a 14 anos'
            WHEN p.idade < 25 THEN '15 a 24 anos'
            WHEN p.idade < 40 THEN '25 a 39 anos'
            WHEN p.idade < 65 THEN '40 a 64 anos'
            ELSE '65 anos ou mais'
        END AS faixa_etaria,
        CASE WHEN p.faixa_etaria_fonte IS NOT NULL THEN 'fonte' ELSE 'derivada da idade' END
            AS faixa_etaria_origem
    FROM padronizado p
),
com_municipio AS (
    SELECT
        f.*,
        coalesce(m.cod_municipio_ibge, CASE WHEN e.cod_municipio_ibge <> '' THEN e.cod_municipio_ibge END)
            AS cod_municipio_ibge,
        CASE
            WHEN f.uf_sigla IS NULL OR f.uf_sigla NOT IN (SELECT uf_sigla FROM ref_uf) THEN 'uf não informada'
            WHEN upper(f.municipio_fonte) = 'NÃO ESPECIFICADO' OR ausente(f.municipio_fonte) THEN 'não especificado'
            WHEN m.cod_municipio_ibge IS NOT NULL THEN 'ibge'
            WHEN e.cod_municipio_ibge <> '' THEN 'exceção manual'
            ELSE 'sem correspondência'
        END AS municipio_status
    FROM com_faixa f
    LEFT JOIN ref_municipios m
        ON m.uf_sigla = f.uf_sigla AND m.nome_norm = norm_nome(f.municipio_fonte)
    LEFT JOIN ref_excecoes e
        ON e.uf = f.uf_sigla AND upper(e.municipio_fonte) = upper(f.municipio_fonte)
)
SELECT
    c.*,
    -- lista das correções aplicadas a cada registro (alimenta o relatório de qualidade)
    (
        CASE WHEN c.ano_entrada IS NULL THEN ['C01'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.municipio_status = 'uf não informada' THEN ['C02'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.municipio_status = 'exceção manual' THEN ['C03'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.sexo = 'Não informado' THEN ['C04'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.faixa_etaria = 'Não especificado' THEN ['C05'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.idade_fonte IS NOT NULL AND c.idade IS NULL THEN ['C06'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.estado_civil = 'Não informado' THEN ['C07'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.estado_civil_fonte LIKE '%\_%' ESCAPE '\' THEN ['C08'] ELSE []::VARCHAR[] END ||
        CASE WHEN c.classificacao_registro = 'Não informado' THEN ['C09'] ELSE []::VARCHAR[] END
    ) AS correcoes
FROM com_municipio c;
