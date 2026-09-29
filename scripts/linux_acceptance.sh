#!/usr/bin/env bash
set -euo pipefail
# GitHub-hosted disposable Ubuntu only. No deployment or cloud credentials.
BASELINE=2be952be024a2e46d7ba2b2b83a9d1ebc85baa49
ROOT=$(pwd)
OUT="$ROOT/reports/acceptance"
WORK="$RUNNER_TEMP/layaas-acceptance"
mkdir -p "$OUT" "$WORK/baseline"
git archive "$BASELINE" server.py release.py release.json requirements-linux.lock deploy/preload.py | tar -x -C "$WORK/baseline"
python -m venv "$WORK/baseline-venv"
python -m venv "$WORK/candidate-venv"
"$WORK/baseline-venv/bin/pip" install --disable-pip-version-check -r "$WORK/baseline/requirements-linux.lock" -r requirements-test.txt
"$WORK/candidate-venv/bin/pip" install --disable-pip-version-check -r requirements-linux.lock -r requirements-test.txt
"$WORK/baseline-venv/bin/pip" check
"$WORK/candidate-venv/bin/pip" check
export HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
# Populate the old cache with the baseline client; candidate prepares its own fresh cache.
HF_HOME="$WORK/baseline-cache" PYTHONPATH="$WORK/baseline" "$WORK/baseline-venv/bin/python" "$WORK/baseline/deploy/preload.py"
sudo env CI_RUNTIME_USER="$USER" HF_HOME="$WORK/candidate-cache" HF_HUB_DISABLE_IMPLICIT_TOKEN=1 PYTHONDONTWRITEBYTECODE=1 "$WORK/candidate-venv/bin/python" scripts/ci_model_prepare.py "$OUT/preparation.json"
# Drop root after creating network namespace. There is no route or network interface.
sudo unshare --net -- runuser -u "$USER" -- env HF_HOME="$WORK/baseline-cache" HF_HUB_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 "$WORK/baseline-venv/bin/python" "$ROOT/scripts/acceptance.py" run --runtime "$WORK/baseline" --role baseline --commit "$BASELINE" --output "$OUT/baseline.json"
sudo unshare --net -- runuser -u "$USER" -- env HF_HOME="$WORK/empty-offline-cache" HF_HUB_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 "$WORK/candidate-venv/bin/python" "$ROOT/scripts/acceptance.py" run --runtime "$ROOT" --role candidate --commit "$GITHUB_SHA" --output "$OUT/candidate.json"
sudo unshare --net -- runuser -u "$USER" -- env HF_HOME="$WORK/empty-offline-cache" HF_HUB_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 "$WORK/candidate-venv/bin/python" "$ROOT/scripts/acceptance.py" run --runtime "$ROOT" --role restart --commit "$GITHUB_SHA" --output "$OUT/restart.json"
"$WORK/candidate-venv/bin/python" scripts/acceptance.py compare "$OUT/baseline.json" "$OUT/candidate.json"
