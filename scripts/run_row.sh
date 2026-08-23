#!/usr/bin/env bash
# Run one row of the experiment matrix (docs/experiment_matrix.md).
#
# The ONLY thing that varies between rows is the synthesizer model. Graph, embedder,
# max_chars, scenario set, rubric and judge are identical everywhere — that is the
# controlled-experiment rule, and hard-coding the rows here is what keeps it true.
#
#   ./scripts/run_row.sh 1          # generate narratives for row 1 (the ceiling)
#   ./scripts/run_row.sh 1 --fresh  # regenerate rather than resume
#
# Outputs land in experiments/results/<run_tag>/, namespaced by backend+model, so no
# row can overwrite another. Judge afterwards with:
#   conda run -n xai python -m caie.evaluation.report --run <run_tag>
set -euo pipefail
cd "$(dirname "$0")/.."

ROW="${1:-}"          # capture BEFORE shift; `set -u` bites otherwise
case "$ROW" in
  0) BACKEND=ollama; MODEL=llama3.1:8b        ; NOTE="local anchor (Ollama)" ;;
  1) BACKEND=openai; MODEL=openai/gpt-5.5     ; NOTE="CEILING — frontier" ;;
  2) BACKEND=openai; MODEL=qwen/qwen3-235b-a22b-2507      ; NOTE="open, large MoE" ;;
  3) BACKEND=openai; MODEL=meta-llama/llama-3.3-70b-instruct ; NOTE="open, ~70B" ;;
  4) BACKEND=openai; MODEL=qwen/qwen3-32b     ; NOTE="open, ~30B" ;;
  5) BACKEND=openai; MODEL=meta-llama/llama-3.1-8b-instruct ; NOTE="hosting control — same weights as row 0" ;;
  *) echo "usage: $0 <row 0-5> [--fresh]"; exit 2 ;;
esac
shift || true

case "$MODEL" in anthropic/*|*claude*)
  echo "REFUSED: judge is Claude; a Claude synthesizer breaks the §7.6 independence rule."
  exit 1 ;;
esac

export CAIE_SYNTH_BACKEND="$BACKEND" CAIE_SYNTH_MODEL="$MODEL"
echo "row $ROW: $NOTE"
echo "  backend=$BACKEND  model=$MODEL"
conda run -n xai --no-capture-output python -m caie.evaluation.tiers "$@"
