# Cashflow Online — La Carrera de Ratas

Versión multijugador en web del clásico juego de finanzas personales de Robert Kiyosaki
(estilo *Cashflow 101/202*): **la carrera de ratas** y **la pista rápida**.

## Cómo correrlo

```bash
./run.sh
```

o manualmente:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Abrí `http://localhost:8000` en el navegador. Para jugar con amigos en red, compartí el
código de sala (6 caracteres) que aparece arriba a la derecha, o exponé el puerto.

## Publicar en internet

### Opción A: Render (gratis, recomendada)

1. Subí este proyecto a GitHub.
2. En [render.com](https://render.com) → **New → Blueprint**, elegí el repo. Detecta
   automáticamente `render.yaml` y crea el servicio (plan free, sin tarjeta).
3. Listo: quedás con una URL tipo `https://cashflow-online.onrender.com` con soporte de
   WebSockets incluido.

Nota del plan free: el servicio se duerme tras ~15 min sin tráfico y tarda ~1 min en
despertar cuando alguien entra. Mientras haya una partida conectada no se duerme.

### Opción B: desde tu PC con un túnel (gratis, sin servidor)

La PC debe quedar encendida mientras juegan.

```bash
# Tailscale (URL estable y gratuita; instalá la app una vez)
sudo apt install tailscale && sudo tailscale up
./tunnel.sh tailscale
# → te da una URL https://<tu-nombre>.ts.net/ para compartir

# ngrok (alternativa; requiere cuenta gratis + authtoken)
./tunnel.sh ngrok
```

El script levanta el servidor solo y te imprime la URL. Sin argumento, detecta cuál
túnel tenés instalado.

## Cómo se juega

1. **Crear sala / unirse**: el host crea una sala y comparte el código; los demás se unen.
2. **Elegir profesión**: cada jugador elige su profesión (Conserje, Doctor, Abogada, etc.),
   que define su salario, gastos, deudas y ahorros.
3. **Carrera de ratas** (anillo externo): en cada turno tirás los dados y caés en una casilla:
   - 💵 **Día de Pago**: cobrás tu flujo de caja mensual.
   - 📗/📘 **Oportunidad menor / mayor**: cartas de inmuebles, negocios o acciones. Podés
     comprar (pagando el anticipo con efectivo) o pasar.
   - 📈 **Mercado**: eventos de compra/venta. Los dueños de activos afines pueden vender.
   - 🛍️ **Baratijas**: gastos y tentaciones (opcional).
   - 🤝 **Caridad**: donás el 10% de tu salario y el próximo turno tirás 1 solo dado.
   - 👶 **Bebé**: sumás gastos de hijos.
   - 💼 **Despido**: perdés el salario por algunos turnos.
4. **Escapar**: cuando tu **ingreso pasivo supera tus gastos totales**, salís de la carrera
   de ratas y entrás a la **pista rápida** (anillo interno).
5. **Pista rápida**: conseguís flujo de caja, negocios y bienes. Ganás al **comprar tu
   sueño** (caer en la casilla de Sueño con el efectivo suficiente) o al alcanzar
   **$50.000/mes de flujo de caja**.

Reglas simplificadas respecto al Cashflow de mesa: no hay préstamos bancarios para
anticipos, y el "día de pago" se cobra al **caer** en la casilla (no al pasarla).

## Estructura

```
server.py            Servidor FastAPI + WebSocket + estáticos
game/data.py         Profesiones, cartas, tableros
game/engine.py       Motor del juego (turnos, finanzas, carrera de ratas y pista rápida)
game/rooms.py        Salas, conexiones, chat, estado
public/              Frontend (HTML/CSS/JS plano, sin build)
```

## Tests

```bash
.venv/bin/pip install pytest pytest-asyncio ruff   # dependencias de desarrollo
.venv/bin/python -m pytest tests/test_unit.py tests/test_simulation.py -q   # motor (rápido)
.venv/bin/python -m pytest tests/test_protocol.py -q   # servidor + WebSocket real
.venv/bin/python -m pytest tests/test_frontend.py -q  # navegador headless (requiere Brave/Chromium)
.venv/bin/python -m pytest tests/test_property.py -q  # partidas aleatorias con invariantes (~75s)
```

- `test_protocol.py` levanta su propio servidor uvicorn en un puerto libre.
- `test_frontend.py` levanta un Brave headless y juega de verdad haciendo clic en el DOM;
  verifica que no haya errores de JavaScript.
- Lint: `.venv/bin/ruff check .`
