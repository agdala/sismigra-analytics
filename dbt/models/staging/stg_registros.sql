{#-
  Registros aceitos, com tipos, datas e categorias padronizados.
  Regras de correção aplicadas aqui: C01 (ano de entrada), C04 (sexo), C05/C06 (faixa e idade),
  C07/C08 (estado civil), C09 (classificação). Rejeições (R01 a R03) ficam em stg_rejeitados.
-#}
with base as (
    select
        b.*,
        try_cast(trim(b.DATAREGISTRO) as integer) as _ano_registro,
        try_cast(trim(b.AMPARO) as integer)       as _amparo,
        try_cast(trim(b.DATAENTRADA) as integer)  as _ano_entrada,
        try_cast(trim(b.IDADE) as integer)        as _idade
    from {{ source('bronze', 'registros_brutos') }} b
),

aceitos as (
    select * from base
    where _ano_registro is not null and _ano_registro = ano_arquivo and _amparo is not null
),

padronizado as (
    select
        a.sha12 || '-' || lpad(cast(a.linha_origem as varchar), 7, '0') as id_registro,
        a.arquivo_csv,
        a.linha_origem,
        a._ano_registro as ano_registro,

        -- amparo legal
        a._amparo as amparo_codigo,
        nullif(trim(a.AMPARO_DESCRICAO), '-') as amparo_descricao,
        case when {{ ausente('a.CLASSIFICACAO_REGISTRO') }} then 'Não informado'
             else trim(a.CLASSIFICACAO_REGISTRO) end as classificacao_registro,
        case when {{ ausente('a.CLASSIFICACAO_REVISADA') }} then 'Não informado'
             else trim(a.CLASSIFICACAO_REVISADA) end as classificacao_revisada,
        trim(a.TIPOLOGIA_AMPAROS) as tipologia_fonte,

        -- ano de entrada: válido entre 1900 e o ano do registro (C01)
        case when a._ano_entrada between 1900 and a._ano_registro then a._ano_entrada end as ano_entrada,
        nullif(trim(a.DATAENTRADA), '') as ano_entrada_fonte,

        -- localidade
        case when {{ ausente('a.UNIDADE_FED_RESIDENCIA') }} then null
             else upper(trim(a.UNIDADE_FED_RESIDENCIA)) end as uf_sigla,
        trim(a.MUNICIPIO_RESIDENCIA) as municipio_fonte,

        -- países
        trim(a.PAIS_NASCIMENTO) as pais_nascimento_fonte,
        trim(a.PAIS_NACIONALIDADE) as pais_nacionalidade_fonte,
        trim(a.CONTINENTE) as continente_fonte,

        -- perfil
        case upper(strip_accents(trim(coalesce(a.SEXO, ''))))
            when 'MASCULINO' then 'Masculino'
            when 'FEMININO' then 'Feminino'
            else 'Não informado'
        end as sexo,
        a.SEXO as sexo_fonte,
        case when a._idade between 0 and 120 then a._idade end as idade,
        a.IDADE as idade_fonte,
        a.FAIXA_ETARIA as faixa_etaria_fonte,
        case
            when {{ ausente('a.ESTADO_CIVIL') }} or upper(trim(a.ESTADO_CIVIL)) = 'DESCONHECIDO' then 'Não informado'
            else replace(upper(trim(a.ESTADO_CIVIL)), '_', ' ')
        end as estado_civil,
        a.ESTADO_CIVIL as estado_civil_fonte,
        case when {{ ausente('a.PROFISSAO') }} then 'Não informado' else trim(a.PROFISSAO) end as profissao,
        case when {{ ausente('a.STATUS') }} then 'Não informado' else trim(a.STATUS) end as status,

        -- duplicata exata: mesma linha inteira repetida no mesmo arquivo (é mantida; alerta A01)
        count(*) over (partition by a.arquivo_csv, a.DATAREGISTRO, a.AMPARO, a.AMPARO_DESCRICAO,
            a.CLASSIFICACAO_REGISTRO, a.DATAENTRADA, a.UNIDADE_FED_RESIDENCIA, a.MUNICIPIO_RESIDENCIA,
            a.PAIS_NASCIMENTO, a.PAIS_NACIONALIDADE, a.CONTINENTE, a.FAIXA_ETARIA, a.IDADE, a.SEXO,
            a.ESTADO_CIVIL, a.PROFISSAO, a.STATUS, a.CLASSIFICACAO_REVISADA, a.TIPOLOGIA_AMPAROS) > 1
            as flag_duplicata_exata
    from aceitos a
)

select
    p.*,
    -- faixa etária com os mesmos cortes da fonte: [0,15) [15,25) [25,40) [40,65) [65,+)
    case
        when p.faixa_etaria_fonte is not null then
            case trim(p.faixa_etaria_fonte)
                when '0 |-- 15 anos'  then '0 a 14 anos'
                when '15 |-- 25 anos' then '15 a 24 anos'
                when '25 |-- 40 anos' then '25 a 39 anos'
                when '40 |-- 65 anos' then '40 a 64 anos'
                when '65 |-- anos'    then '65 anos ou mais'
                else 'Não especificado'
            end
        when p.idade is null then 'Não especificado'
        when p.idade < 15 then '0 a 14 anos'
        when p.idade < 25 then '15 a 24 anos'
        when p.idade < 40 then '25 a 39 anos'
        when p.idade < 65 then '40 a 64 anos'
        else '65 anos ou mais'
    end as faixa_etaria,
    case when p.faixa_etaria_fonte is not null then 'fonte' else 'derivada da idade' end
        as faixa_etaria_origem
from padronizado p
