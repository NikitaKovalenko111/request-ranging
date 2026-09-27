r'''Quick manual Feature Extractor run.

Edit TEXT_TO_TEST and EXECUTORS below, then run from the decision-engine root:

    .venv\Scripts\python tests\feature_extractor\manual_run.py
'''

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from decision_engine.feature_extractor import (
    FeatureCandidate,
    FeatureExtractionRequest,
    HeuristicFeatureExtractor,
    PredictorFeatureExtractor,
)


# Replace this value with your order text.
TEXT_TO_TEST = (
    '\u0421\u0440\u043e\u0447\u043d\u043e \u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f '
    '\u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f Python-\u0441\u0435\u0440\u0432\u0438\u0441\u0430 '
    '\u0441 PostgreSQL, \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f '
    '\u0434\u0430\u043d\u043d\u044b\u0445 \u0438 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0435 '
    '\u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u044b REST API.'
)

# Replace or extend this list to check skill matching.
EXECUTORS = (
    FeatureCandidate('101', ('Python', 'PostgreSQL', 'REST API')),
    FeatureCandidate('102', ('Java', 'Kafka', 'Kubernetes')),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run Feature Extractor manually')
    parser.add_argument(
        '--file',
        type=Path,
        help='Read order text from a UTF-8 file instead of TEXT_TO_TEST',
    )
    parser.add_argument(
        '--classifier',
        action='store_true',
        help='Use the trained transformer classifier instead of heuristics',
    )
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    arguments = parse_args()
    text = (
        arguments.file.read_text(encoding='utf-8')
        if arguments.file is not None
        else TEXT_TO_TEST
    )

    if arguments.classifier:
        from decision_engine.feature_extractor.classifier.predict import (
            RequestPredictor,
        )

        extractor = PredictorFeatureExtractor(RequestPredictor())
    else:
        extractor = HeuristicFeatureExtractor()

    result = extractor.extract(
        FeatureExtractionRequest(
            order_id='manual-test',
            text=text,
            candidates=EXECUTORS,
        )
    )
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
