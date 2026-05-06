from __future__ import annotations

from typing import Any


class RawFeaturePipeline:
    """Future raw → feature expansion point.

    Current MVP skips this stage because the first backend input is assumed to
    be a feature dictionary. Later, Android logs, wearable files, or daily
    aggregates can be processed here.
    """

    def transform(self, raw_payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "Raw data processing is intentionally omitted in this MVP. "
            "Send precomputed features to /v1/risk-score instead."
        )
