from decision_engine.feature_extractor import (
    FeatureCandidate,
    FeatureExtractionRequest,
    HeuristicFeatureExtractor,
    PredictorFeatureExtractor,
)


def test_heuristic_extractor_uses_explicit_fallback_values() -> None:
    result = HeuristicFeatureExtractor().extract(
        FeatureExtractionRequest(
            order_id='1',
            text='urgent Python integration',
            fallback_complexity=0.2,
            fallback_urgency=0.3,
            candidates=(FeatureCandidate('7', ('python',)),),
        )
    )

    assert result.complexity == 0.2
    assert result.urgency == 0.3
    assert result.skill_match_scores['7'] > 0.0


def test_predictor_adapter_maps_classifier_labels_to_numbers() -> None:
    class Predictor:
        def predict(self, text: str) -> dict[str, str]:
            return {
                'language': 'ru',
                'urgency': 'critical',
                'complexity': 'complex',
                'estimated_effort': 'over_8h',
            }

    result = PredictorFeatureExtractor(Predictor()).extract(
        FeatureExtractionRequest(order_id='1', text='F5>EB', candidates=())
    )

    assert result.urgency == 1.0
    assert result.complexity == 2.0 / 3.0
    assert result.estimated_effort == 'over_8h'
