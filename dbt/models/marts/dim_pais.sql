select sk_pais, pais, iso3, continente from {{ ref('int_paises') }}
