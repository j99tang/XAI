"""ccir — Context-aware Cyber-physical Intrusion Response.

Three-layer pipeline:
  ids            Layer 1  flow-based intrusion detection
  xai            Layer 2  SHAP attribution -> anomaly-event JSON
  contextualizer Layer 3  LightRAG + multi-persona synthesizer
  evaluation              CPAS metric + LLM-as-judge harness
  schemas                 shared data contracts (the JSON boundary)
"""
__version__ = "0.0.1"
