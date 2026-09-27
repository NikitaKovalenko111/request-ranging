from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

from .classifier.predict import DEFAULT_MODEL_DIR, RequestPredictor
from .matching.keyword_filter import is_valid_keyword, merge_keywords
from .matching.preprocess import clean_text, split_into_sections
from .matching.skill_matching import calculate_matching
from .schemas import ExtractedFeatures, FeatureExtractionRequest


DEFAULT_EMBEDDING_MODEL_DIR = (
    Path(__file__).resolve().parents[3]
    / "models"
    / "feature-extractor"
    / "matching"
    / "paraphrase-multilingual-MiniLM-L12-v2"
)


class MLFeatureExtractor:
    """Classifier + KeyBERT + SentenceTransformer feature extraction."""

    _complexity_values = {
        "simple": 0.0,
        "medium": 1.0 / 3.0,
        "complex": 2.0 / 3.0,
        "very_complex": 1.0,
    }
    _urgency_values = {
        "low": 0.0,
        "normal": 1.0 / 3.0,
        "high": 2.0 / 3.0,
        "critical": 1.0,
    }

    def __init__(
        self,
        predictor: RequestPredictor,
        embedding_model: Any,
        *,
        top_n_per_section: int = 10,
        max_keywords: int = 20,
        ngram_range: tuple[int, int] = (1, 3),
        diversity: float = 0.5,
    ) -> None:
        if top_n_per_section <= 0 or max_keywords <= 0:
            raise ValueError("keyword limits must be positive")
        from keybert import KeyBERT

        self._predictor = predictor
        self._embedding_model = embedding_model
        self._keyword_model = KeyBERT(model=embedding_model)
        self._top_n_per_section = top_n_per_section
        self._max_keywords = max_keywords
        self._ngram_range = ngram_range
        self._diversity = diversity
        self.last_diagnostics: dict[str, Any] = {}

    @classmethod
    def from_local_models(
        cls,
        *,
        classifier_dir: Path = DEFAULT_MODEL_DIR,
        embedding_model_dir: Path = DEFAULT_EMBEDDING_MODEL_DIR,
        device: str | None = None,
        **kwargs: Any,
    ) -> MLFeatureExtractor:
        from sentence_transformers import SentenceTransformer

        predictor = RequestPredictor(
            model_dir=classifier_dir,
            device=device,
        )
        embedding_model = SentenceTransformer(
            str(embedding_model_dir),
            local_files_only=True,
            device=device,
        )
        return cls(predictor, embedding_model, **kwargs)

    def extract(self, request: FeatureExtractionRequest) -> ExtractedFeatures:
        total_started = perf_counter()

        classifier_started = perf_counter()
        labels = self._predictor.predict(request.text)
        classifier_seconds = perf_counter() - classifier_started

        keyword_started = perf_counter()
        processed_text = clean_text(request.text)
        sections = split_into_sections(processed_text)
        section_results: list[dict[str, Any]] = []
        for section in sections:
            extracted = self._keyword_model.extract_keywords(
                section["text"],
                keyphrase_ngram_range=self._ngram_range,
                stop_words=None,
                top_n=self._top_n_per_section,
                use_mmr=True,
                diversity=self._diversity,
            )
            section_results.append(
                {
                    "section_title": section["title"],
                    "keywords": [
                        {"phrase": phrase, "weight": round(float(weight), 4)}
                        for phrase, weight in extracted
                        if is_valid_keyword(phrase)
                    ],
                }
            )
        keyword_records = merge_keywords(section_results)[: self._max_keywords]
        keyword_seconds = perf_counter() - keyword_started

        matching_started = perf_counter()
        matching_details: list[dict[str, Any]] = []
        skill_match_scores: dict[str, float] = {}
        for candidate in request.candidates:
            detail = calculate_matching(
                self._embedding_model,
                keyword_records,
                {
                    "id": candidate.executor_id,
                    "skills": list(candidate.skills),
                },
            )
            score = min(1.0, max(0.0, float(detail["score"])))
            detail["score"] = score
            matching_details.append(detail)
            skill_match_scores[candidate.executor_id] = score
        matching_seconds = perf_counter() - matching_started

        complexity = self._complexity_values.get(
            labels.get("complexity"),
            request.fallback_complexity if request.fallback_complexity is not None else 0.5,
        )
        urgency = self._urgency_values.get(
            labels.get("urgency"),
            request.fallback_urgency if request.fallback_urgency is not None else 0.5,
        )
        self.last_diagnostics = {
            "classifier_labels": dict(labels),
            "processed_text": processed_text,
            "sections": section_results,
            "keyword_records": keyword_records,
            "matching_details": matching_details,
            "timings_seconds": {
                "classifier_inference": classifier_seconds,
                "keybert_extraction": keyword_seconds,
                "embedding_skill_matching": matching_seconds,
                "feature_extractor_total": perf_counter() - total_started,
            },
        }
        return ExtractedFeatures(
            complexity=complexity,
            urgency=urgency,
            language=labels.get("language"),
            estimated_effort=labels.get("estimated_effort"),
            keywords=tuple(item["phrase"] for item in keyword_records),
            skill_match_scores=skill_match_scores,
        )
