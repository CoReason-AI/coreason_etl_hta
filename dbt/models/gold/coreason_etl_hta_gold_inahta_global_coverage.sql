{{ config(materialized='view', schema='gold') }}

-- Aggregating HTA volume by country and publication_year for geographic analysis
select
    country,
    publication_year,
    count(coreason_id) as total_assessments

from {{ ref('coreason_etl_hta_silver_inahta_assessments') }}
where country is not null and country != ''
group by country, publication_year
order by country, publication_year desc
