#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${SHORTS_MODEL_DIR:-}" && -x "$SHORTS_MODEL_DIR/llama-b12776/llama-server" ]]; then
  "$SHORTS_MODEL_DIR/llama-b12776/llama-server" -m "$SHORTS_MODEL_DIR/model.gguf" \
    --host 127.0.0.1 --port 18171 -t 4 -c 4096 -np 1 --no-ui \
    >"$SHORTS_MODEL_DIR/server.log" 2>&1 &
  writer_pid=$!
  trap 'kill "$writer_pid" 2>/dev/null || true' EXIT
  for attempt in {1..30}; do
    if curl --silent --fail --max-time 1 http://127.0.0.1:18171/health >/dev/null; then
      export SHORTS_LOCAL_WRITER=1
      break
    fi
    kill -0 "$writer_pid" 2>/dev/null || break
    sleep 1
  done
  if [[ "${SHORTS_LOCAL_WRITER:-}" != 1 ]]; then
    echo "Local story writer did not start. The reviewed reserve is available."
  fi
fi
"$@"
