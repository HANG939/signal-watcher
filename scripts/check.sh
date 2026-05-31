#!/usr/bin/env bash
set -euo pipefail

python3 -m compileall -q src
PYTHONPATH=src python3 -m pytest -q
bash -n scripts/run_loop.sh
bash -n scripts/install_x_cron.sh
bash -n scripts/install_damai_cron.sh

if grep -RInE 'sctp[[:alnum:]]+|OPENAI_API_KEY|sk-[[:alnum:]]|_m_h5_tk=[[:alnum:]]|3347133198@qq.com|ab\.zh1202@gmail\.com' \
  --exclude-dir=.git \
  --exclude-dir=.venv \
  --exclude-dir=.pytest_cache \
  --exclude-dir=venv \
  --exclude-dir=env \
  --exclude=check.sh \
  .; then
  echo "Potential secret or private identifier found." >&2
  exit 1
fi

echo "All checks passed."
