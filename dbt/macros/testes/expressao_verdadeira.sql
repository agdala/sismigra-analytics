{#- Teste genérico: falha nas linhas em que a expressão é falsa (sem depender de pacotes externos). -#}
{% test expressao_verdadeira(model, expressao, onde=none, column_name=none) %}
select *
from {{ model }}
where not ({{ expressao }})
{%- if onde %} and ({{ onde }}){% endif %}
{% endtest %}
