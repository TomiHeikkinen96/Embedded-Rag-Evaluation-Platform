from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_DIR = PROJECT_ROOT / "storage"
INDEXES_DIR = STORAGE_DIR / "indexes"
METADATA_DB_PATH = STORAGE_DIR / "metadata.sqlite"
FILE_TRACKING_DB_PATH = STORAGE_DIR / "files_ingested.sqlite"
BENCHMARK_QUERIES_PATH = PROJECT_ROOT / "benchmark_queries.txt"
VISUALIZATION_DIR = PROJECT_ROOT / "visualization"


def faiss_index_path(model_alias: str, chunker_alias: str = "custom") -> Path:
    return INDEXES_DIR / chunker_alias / f"{model_alias}.faiss"
