# coreason-etl-hta Architectural Roadmap

## Decomposed List of Atomic Units

1. **Atomic Unit 1: Project Setup, Dependencies, & Pydantic Configuration**
   - Implement `pyproject.toml` with `dlt`, `beautifulsoup4`, `requests`, `urllib3`, `polars`, `dbt-postgres`, `pydantic`, `pytest`, `responses`, and `ruff`.
   - Implement `config.py` handling INAHTA base URL, crawl delay, and retry limits using Pydantic.
   - Write comprehensive unit tests for configuration models.

2. **Atomic Unit 2: Resilient Web Scraper Implementation**
   - Implement polite web scraping logic with `requests.Session()`, `HTTPAdapter`, and `urllib3.util.Retry`.
   - Implement `time.sleep()` based on `crawl_delay` configuration.
   - Implement HTML parsing using `BeautifulSoup4` to gracefully extract unstructured records into lists of dictionaries without raising `NoneType` errors.

3. **Atomic Unit 3: Polars Identity Resolution Logic**
   - Implement Polars pipeline to generate `assessment_hash_id` (MD5 of Title, Agency, Year).
   - Implement `.map_batches()` logic to generate `coreason_id` using `uuid.uuid5(NAMESPACE_INAHTA, assessment_hash_id)`.
   - Structure output to perfectly match `{"assessment_hash_id": hash_id, "coreason_id": coreason_id, "raw_data": scraped_dict}`.

4. **Atomic Unit 4: dlt Bronze Layer Ingestion**
   - Configure dlt with `max_table_nesting=0` to store `raw_data` intact as `JSONB`.
   - Implement `write_disposition="merge"` utilizing `assessment_hash_id` as the merge key.

5. **Atomic Unit 5: dbt Silver Layer Transformations**
   - Create `bronze.inahta_assessments_raw` source definition.
   - Implement native Postgres `content_hash` computation using `md5(raw_data::text)`.
   - Implement string cleaning, strong typing, and extracting fields from JSONB payload via dbt SQL.

6. **Atomic Unit 6: dbt Gold Layer Product Models**
   - Implement `gold_inahta_global_coverage` (aggregating volume by country and year).
   - Implement `gold_inahta_search_index` (clean text-searchable view for RAG vector databases).

7. **Atomic Unit 7: Automated Data Validation**
   - Create `schema.yml` inside the dbt directory.
   - Implement strict data tests (e.g., `not_null` on `title`, `unique` on `coreason_id`) to fail pipeline on scraper degradation.
