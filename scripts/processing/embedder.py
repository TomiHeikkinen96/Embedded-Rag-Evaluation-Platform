from __future__ import annotations

import warnings
from typing import Iterable

import numpy as np
try:
    import torch
    from dotenv import load_dotenv
    from sentence_transformers import SentenceTransformer
    from transformers import modeling_utils
except ImportError as exc:
    raise ImportError(
        "Embedding dependencies are missing. Install dependencies with "
        "`pip install -r requirements.txt`."
    ) from exc

from processing.embedding_models import EmbeddingModelConfig
from project_paths import PROJECT_ROOT

try:
    from transformers.utils import loading_report
except ImportError:
    loading_report = None


def _is_only_known_minilm_warning(loading_info: object) -> bool:
    unexpected_keys = getattr(loading_info, "unexpected_keys", set())
    missing_keys = getattr(loading_info, "missing_keys", set())
    mismatched_keys = getattr(loading_info, "mismatched_keys", set())
    error_msgs = getattr(loading_info, "error_msgs", [])
    conversion_errors = getattr(loading_info, "conversion_errors", {})
    return (
        unexpected_keys == {"embeddings.position_ids"}
        and not missing_keys
        and not mismatched_keys
        and not error_msgs
        and not conversion_errors
    )


class TextEmbedder:
    def __init__(self, config: EmbeddingModelConfig) -> None:
        load_dotenv(PROJECT_ROOT / ".env")
        self.config = config
        self.model_name = config.model_id
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        original_modeling_utils_report = getattr(
            modeling_utils, "log_state_dict_report", None
        )
        original_loading_report = (
            getattr(loading_report, "log_state_dict_report", None)
            if loading_report is not None
            else None
        )

        def patched_log_state_dict_report(
            model,
            pretrained_model_name_or_path: str,
            ignore_mismatched_sizes: bool,
            loading_info,
            logger=None,
        ) -> None:
            if _is_only_known_minilm_warning(loading_info):
                return
            if original_loading_report is None:
                return
            original_loading_report(
                model,
                pretrained_model_name_or_path,
                ignore_mismatched_sizes,
                loading_info,
                logger=logger,
            )

        if original_modeling_utils_report is not None:
            modeling_utils.log_state_dict_report = patched_log_state_dict_report
        if loading_report is not None and original_loading_report is not None:
            loading_report.log_state_dict_report = patched_log_state_dict_report
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"optimum is not installed\..*",
                    category=UserWarning,
                )
                self.model = SentenceTransformer(
                    config.model_id,
                    device=self.device,
                    trust_remote_code=config.trust_remote_code,
                )
        finally:
            if original_modeling_utils_report is not None:
                modeling_utils.log_state_dict_report = original_modeling_utils_report
            if loading_report is not None and original_loading_report is not None:
                loading_report.log_state_dict_report = original_loading_report

    def get_embedding_dimension(self) -> int:
        return int(self.model.get_embedding_dimension())

    def embed_texts(
        self,
        texts: Iterable[str],
        *,
        input_type: str = "document",
        batch_size: int = 32,
    ) -> np.ndarray:
        if input_type not in {"document", "query"}:
            raise ValueError("input_type must be either 'document' or 'query'")

        prefix = (
            self.config.query_prefix
            if input_type == "query"
            else self.config.document_prefix
        )
        text_list = [f"{prefix}{text}" for text in texts]
        if not text_list:
            return np.empty((0, self.get_embedding_dimension()), dtype=np.float32)

        embeddings = self.model.encode(
            text_list,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.astype(np.float32)
