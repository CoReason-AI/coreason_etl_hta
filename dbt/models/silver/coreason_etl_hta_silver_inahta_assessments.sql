{{ config(materialized='table', schema='silver') }}

with source_data as (

    select
        assessment_hash_id,
        coreason_id,
        raw_data,
        -- The content_hash must be computed natively in Postgres using md5(raw_data::text)
        md5(raw_data::text) as content_hash

    from {{ source('bronze', 'coreason_etl_hta_bronze_inahta_assessments') }}

),

parsed as (

    select
        assessment_hash_id,
        coreason_id,
        content_hash,

        -- Extract from JSONB. Using ->> extracts as text.
        raw_data->>'Title' as raw_title,
        raw_data->>'Agency' as raw_agency,
        raw_data->>'Country' as raw_country,
        raw_data->>'Year' as raw_year,
        raw_data->>'Type' as raw_type

    from source_data

)

select
    assessment_hash_id,
    coreason_id,
    content_hash,

    -- String cleaning: strip whitespace, newlines, and basic HTML artifacts.
    -- BTRIM removes spaces. REGEXP_REPLACE strips '\n' or HTML tags.
    trim(regexp_replace(raw_title, '[\n\r]+|<[^>]*>', ' ', 'g')) as title,
    trim(regexp_replace(raw_agency, '[\n\r]+|<[^>]*>', ' ', 'g')) as agency_name,
    trim(regexp_replace(raw_country, '[\n\r]+|<[^>]*>', ' ', 'g')) as country,

    -- Cast Year to integer (using NULLIF to handle empty strings gracefully)
    cast(nullif(trim(raw_year), '') as integer) as publication_year,

    trim(regexp_replace(raw_type, '[\n\r]+|<[^>]*>', ' ', 'g')) as assessment_type

from parsed
