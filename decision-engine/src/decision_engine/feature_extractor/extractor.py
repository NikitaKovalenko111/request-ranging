from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import re
from typing import Protocol

from .schemas import ExtractedFeatures, FeatureCandidate, FeatureExtractionRequest


class FeatureExtractor(Protocol):
    def extract(self, request: FeatureExtractionRequest) -> ExtractedFeatures: ...


class LabelPredictor(Protocol):
    def predict(self, text: str) -> Mapping[str, str]: ...


class HeuristicFeatureExtractor:
    '''Lightweight local extractor and fallback when model artifacts are absent.'''

    _token_pattern = re.compile(r'[\w+#.-]+', re.UNICODE)
    _urgent_words = frozenset(
        {
            'urgent',
            'immediately',
            'critical',
            'asap',
            '\u0441\u0440\u043e\u0447\u043d\u043e',
            '\u043d\u0435\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u043e',
            '\u043a\u0440\u0438\u0442\u0438\u0447\u043d\u043e',
            '\u0430\u0432\u0430\u0440\u0438\u044f',
        }
    )
    _complex_words = frozenset(
        {
            'architecture',
            'integration',
            'migration',
            'distributed',
            '\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u0430',
            '\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f',
            '\u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f',
        }
    )
    _stop_words = frozenset(
        {
            'the',
            'and',
            'for',
            'with',
            'this',
            'that',
            '\u0438\u043b\u0438',
            '\u0434\u043b\u044f',
            '\u043a\u0430\u043a',
            '\u044d\u0442\u043e',
            '\u043f\u0440\u0438',
            '\u043d\u0443\u0436\u043d\u043e',
        }
    )

    def __init__(self, *, max_keywords: int = 12) -> None:
        if max_keywords <= 0:
            raise ValueError('max_keywords must be positive')
        self._max_keywords = max_keywords

    def extract(self, request: FeatureExtractionRequest) -> ExtractedFeatures:
        tokens = [token.lower() for token in self._token_pattern.findall(request.text)]
        keywords = self._keywords(tokens)
        complexity = request.fallback_complexity
        if complexity is None:
            complexity = self._complexity(tokens)
        urgency = request.fallback_urgency
        if urgency is None:
            urgency = self._urgency(tokens)
        return ExtractedFeatures(
            complexity=complexity,
            urgency=urgency,
            language=self._language(request.text),
            estimated_effort=self._effort(complexity),
            keywords=keywords,
            skill_match_scores={
                candidate.executor_id: self._skill_match(keywords, candidate)
                for candidate in request.candidates
            },
        )

    def _keywords(self, tokens: list[str]) -> tuple[str, ...]:
        counts = Counter(
            token for token in tokens if len(token) >= 3 and token not in self._stop_words
        )
        ordered = sorted(counts, key=lambda token: (-counts[token], token))
        return tuple(ordered[: self._max_keywords])

    def _complexity(self, tokens: list[str]) -> float:
        if not tokens:
            return 0.5
        length_component = min(len(tokens) / 250.0, 1.0)
        signal_component = min(
            sum(token in self._complex_words for token in tokens) / 3.0,
            1.0,
        )
        return round(0.35 + 0.35 * length_component + 0.30 * signal_component, 4)

    def _urgency(self, tokens: list[str]) -> float:
        signals = sum(token in self._urgent_words for token in tokens)
        if signals == 0:
            return 0.5
        return min(1.0, 0.6 + 0.15 * signals)

    @staticmethod
    def _language(text: str) -> str | None:
        if not text.strip():
            return None
        cyrillic = sum('\u0400' <= character <= '\u04ff' for character in text)
        latin = sum('a' <= character.lower() <= 'z' for character in text)
        return 'ru' if cyrillic >= latin else 'en'

    @staticmethod
    def _effort(complexity: float) -> str:
        if complexity < 0.25:
            return 'up_to_1h'
        if complexity < 0.5:
            return '1_to_4h'
        if complexity < 0.75:
            return '4_to_8h'
        return 'over_8h'

    @staticmethod
    def _skill_match(keywords: tuple[str, ...], candidate: FeatureCandidate) -> float:
        if not keywords or not candidate.skills:
            return 0.0
        keyword_set = set(keywords)
        skill_tokens = {
            token.lower()
            for skill in candidate.skills
            for token in re.findall(r'[\w+#.-]+', skill, re.UNICODE)
        }
        return round(len(keyword_set & skill_tokens) / len(keyword_set), 4)


class PredictorFeatureExtractor(HeuristicFeatureExtractor):
    '''Adapter for the existing text classifier with a heuristic fallback for keywords.'''

    _complexity_values = {
        'simple': 0.0,
        'medium': 1.0 / 3.0,
        'complex': 2.0 / 3.0,
        'very_complex': 1.0,
    }
    _urgency_values = {
        'low': 0.0,
        'normal': 1.0 / 3.0,
        'high': 2.0 / 3.0,
        'critical': 1.0,
    }

    def __init__(self, predictor: LabelPredictor, *, max_keywords: int = 12) -> None:
        super().__init__(max_keywords=max_keywords)
        self._predictor = predictor

    def extract(self, request: FeatureExtractionRequest) -> ExtractedFeatures:
        baseline = super().extract(request)
        if not request.text.strip():
            return baseline
        labels = self._predictor.predict(request.text)
        return ExtractedFeatures(
            complexity=self._complexity_values.get(labels.get('complexity'), baseline.complexity),
            urgency=self._urgency_values.get(labels.get('urgency'), baseline.urgency),
            language=labels.get('language', baseline.language),
            estimated_effort=labels.get('estimated_effort', baseline.estimated_effort),
            keywords=baseline.keywords,
            skill_match_scores=baseline.skill_match_scores,
        )
