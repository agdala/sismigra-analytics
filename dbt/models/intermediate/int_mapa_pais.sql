{#- De cada grafia de país da fonte para a chave do país padronizado (-1 = Não informado). -#}
select r.nome_fonte, coalesce(d.sk_pais, -1) as sk_pais
from {{ ref('paises') }} r
left join {{ ref('int_paises') }} d
    on d.pais = r.nome_padronizado and r.nome_padronizado <> 'Não informado'
