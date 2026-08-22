#!/bin/bash
# Chequeo de salud del fine-tuning, pensado para correr cada 12hs vía
# crontab del sistema (no depende de que quede una sesión de Claude Code
# abierta). Invoca una sesión `claude -p` nueva y sin contexto previo con
# el prompt de scripts/train/health_check_prompt.md — ver ese archivo
# para el detalle de qué hace.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."
PROMPT="$(cat scripts/train/health_check_prompt.md)"
/Users/renzodemarco/.local/bin/claude -p "$PROMPT" --dangerously-skip-permissions \
  >> logs/cron_health.log 2>&1
