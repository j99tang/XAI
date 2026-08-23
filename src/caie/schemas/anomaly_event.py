"""The anomaly-event contract.

This is the model- and XAI-agnostic boundary of the whole system: Layer 1 (IDS)
and Layer 2 (SHAP) PRODUCE one AnomalyEvent; Layer 3 (contextualizer) and the
evaluation harness CONSUME it. Swap the detector or the XAI method, keep this
shape, and nothing downstream has to change.

Kept deliberately tiny and dependency-free (standard library only) so every
agent/notebook can import it as the single source of truth.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field


@dataclass
class FeatureAttribution:
    name: str          # e.g. "Flow IAT Std"  (a FLOW statistic, never a topology field)
    value: float       # the feature's actual value on this flow
    shap: float        # SHAP contribution toward the "attack" prediction


@dataclass
class AnomalyEvent:
    flow_id: str
    src_ip: str
    dst_ip: str
    dst_port: int
    prediction: str            # "attack" | "normal"
    confidence: float          # model probability, 0..1
    top_features: list[FeatureAttribution] = field(default_factory=list)

    def to_json(self, **kw) -> str:
        return json.dumps(asdict(self), indent=2, **kw)

    @classmethod
    def from_dict(cls, d: dict) -> "AnomalyEvent":
        feats = [FeatureAttribution(**f) for f in d.get("top_features", [])]
        return cls(**{**d, "top_features": feats})


if __name__ == "__main__":
    # tiny self-test / example of the contract
    ev = AnomalyEvent(
        flow_id="10.0.0.2-10.0.0.5-62883-2404-6",
        src_ip="10.0.0.5", dst_ip="10.0.0.2", dst_port=2404,
        prediction="attack", confidence=0.97,
        top_features=[
            FeatureAttribution("Flow IAT Std", 3677.24, 0.21),
            FeatureAttribution("Bwd Packet Length Max", 543.0, 0.14),
        ],
    )
    print(ev.to_json())
