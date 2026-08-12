from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
INDEX_PATH = STORAGE_DIR / "index.faiss"
METADATA_DB_PATH = STORAGE_DIR / "metadata.sqlite"
FILE_TRACKING_DB_PATH = STORAGE_DIR / "files_ingested.sqlite"
BENCHMARK_QUERIES_PATH = PROJECT_ROOT / "benchmark_queries.txt"
VISUALIZATION_DIR = PROJECT_ROOT / "visualization"
