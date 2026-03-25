import os
import csv
import psycopg2
from coreason_etl_hta.utils.logger import logger

class GoldLayerManager:
    """Manages interactions and extractions from the dbt-built Gold Layer."""
    
    def __init__(self):
        # Securely fetch credentials from the environment, falling back to defaults
        self.host = os.environ.get('PGHOST', 'localhost')
        self.port = os.environ.get('PGPORT', '5432')
        self.user = os.environ.get('PGUSER', 'lisha')
        self.password = os.environ.get('PGPASSWORD', 'mypassword123')
        self.dbname = os.environ.get('PGDATABASE', 'hta')

    def _get_connection(self):
        return psycopg2.connect(
            host=self.host, port=self.port, user=self.user,
            password=self.password, dbname=self.dbname
        )

    def export_search_index(self, output_path: str = "inahta_gold_layer.csv") -> bool:
        """Exports the entire Gold Layer search index to a local CSV file."""
        logger.info("Connecting to Postgres to extract Gold Layer...")
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    # Execute the extraction query
                    cursor.execute("SELECT * FROM public_gold.coreason_etl_hta_gold_inahta_search_index;")
                    columns = [desc[0] for desc in cursor.description]
                    data = cursor.fetchall()

            logger.info(f"Fetched {len(data)} records. Writing to {output_path}...")
            
            # Write to CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(data)

            logger.info(f"✅ Successfully exported Gold Layer to {os.path.abspath(output_path)}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to export Gold Layer: {e}")
            return False
