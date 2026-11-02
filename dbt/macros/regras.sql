{#- Normalização para comparar nomes: maiúsculas, sem acento, só letras. -#}
{% macro norm_nome(x) -%}
    regexp_replace(upper(strip_accents({{ x }})), '[^A-Z]', '', 'g')
{%- endmacro %}

{#- Texto vazio, "-", "--" e "####" significam ausência na fonte. -#}
{% macro ausente(x) -%}
    ({{ x }} IS NULL OR trim({{ x }}) IN ('', '-', '--', '####'))
{%- endmacro %}
