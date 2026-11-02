{#- Teste genérico: falha se o filtro encontrar alguma linha. Útil para os alertas (severity: warn). -#}
{% test sem_linhas(model, filtro, column_name=none) %}
select * from {{ model }} where {{ filtro }}
{% endtest %}
