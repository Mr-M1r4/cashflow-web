#!/usr/bin/env bash
# Publica el servidor local por un túnel para que jueguen amigos desde internet.
# Uso: ./tunnel.sh [ngrok|tailscale]   (por defecto: detecta el que tengas instalado)
set -e
cd "$(dirname "$0")"

PORT="${PORT:-8000}"

# 1) Levantar el servidor si no está corriendo
if ! (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
  echo "▶ Iniciando servidor en el puerto $PORT…"
  ./run.sh &
  for _ in $(seq 1 30); do
    (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
    sleep 1
  done
fi
echo "✔ Servidor local: http://localhost:$PORT"

MODE="${1:-auto}"
if [ "$MODE" = "auto" ]; then
  if command -v tailscale >/dev/null 2>&1; then MODE="tailscale"
  elif command -v ngrok >/dev/null 2>&1; then MODE="ngrok"
  else echo "✖ Instalá Tailscale o ngrok (ver README)." >&2; exit 1; fi
fi

case "$MODE" in
  tailscale)
    if ! tailscale status >/dev/null 2>&1; then
      echo "▶ Iniciando sesión de Tailscale… (una vez; usá tu cuenta Google/GitHub)"
      sudo tailscale up || tailscale up
    fi
    echo "▶ Publicando con Tailscale…"
    tailscale serve --bg "$PORT" 2>/dev/null || tailscale serve "$PORT"
    FQDN="$(tailscale status --json 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' 2>/dev/null || true)"
    echo "✔ ¡Listo! Compartí: https://${FQDN:-<tu-nombre>.ts.net}/"
    echo "  (más adelante: tailscale serve --bg --https=443 --http=80 $PORT, o tailscale serve reset para despublicar)"
    ;;
  ngrok)
    echo "▶ Publicando con ngrok… (ctrl-C para cortar)"
    ngrok http "$PORT"
    ;;
esac
