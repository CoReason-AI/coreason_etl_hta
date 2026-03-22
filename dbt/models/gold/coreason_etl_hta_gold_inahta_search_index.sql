{{ config(materialized='view', schema='gold') }}

-- Clean text-searchable view specifically designed for ingestion into downstream RAG vector databases
select
    coreason_id,
    assessment_hash_id,
    title as document_title,
    agency_name as source_agency,
    country as source_country,
    publication_year,
    assessment_type,

    -- Creating a concatenated text chunk for standard RAG ingestion
    concat_ws(' | ',
        'Title: ' || coalesce(title, 'Unknown'),
        'Agency: ' || coalesce(agency_name, 'Unknown'),
        'Country: ' || coalesce(country, 'Unknown'),
        'Year: ' || coalesce(cast(publication_year as text), 'Unknown'),
        'Type: ' || coalesce(assessment_type, 'Unknown')
    ) as search_text,

    content_hash as document_version_hash

from {{ ref('coreason_etl_hta_silver_inahta_assessments') }}
