"""Data for the Cashflow game: professions, card decks, board layouts, dreams."""

PROFESSIONS = [
    {
        "id": "janitor",
        "name": "Conserje",
        "icon": "🧹",
        "color": "#a0522d",
        "salary": 1600,
        "savings": 620,
        "expenses": {"taxes": 300, "mortgage": 400, "schoolLoan": 0, "carLoan": 100, "creditCards": 60, "retail": 50, "other": 110, "children": 0},
        "liabilities": {"mortgage": 38000, "schoolLoan": 0, "carLoan": 12000, "creditCards": 4000},
    },
    {
        "id": "truck_driver",
        "name": "Camionero",
        "icon": "🚛",
        "color": "#e67e22",
        "salary": 2500,
        "savings": 1000,
        "expenses": {"taxes": 470, "mortgage": 600, "schoolLoan": 50, "carLoan": 200, "creditCards": 70, "retail": 100, "other": 160, "children": 0},
        "liabilities": {"mortgage": 59000, "schoolLoan": 8000, "carLoan": 21000, "creditCards": 6000},
    },
    {
        "id": "security",
        "name": "Guardia de seguridad",
        "icon": "🔒",
        "color": "#7f8c8d",
        "salary": 3000,
        "savings": 870,
        "expenses": {"taxes": 560, "mortgage": 700, "schoolLoan": 0, "carLoan": 200, "creditCards": 90, "retail": 130, "other": 160, "children": 0},
        "liabilities": {"mortgage": 69000, "schoolLoan": 0, "carLoan": 24000, "creditCards": 8000},
    },
    {
        "id": "teacher",
        "name": "Profesora",
        "icon": "👩‍🏫",
        "color": "#4aa8ff",
        "salary": 3500,
        "savings": 400,
        "expenses": {"taxes": 650, "mortgage": 800, "schoolLoan": 0, "carLoan": 250, "creditCards": 110, "retail": 150, "other": 200, "children": 0},
        "liabilities": {"mortgage": 79000, "schoolLoan": 0, "carLoan": 27000, "creditCards": 10000},
    },
    {
        "id": "nurse",
        "name": "Enfermera",
        "icon": "👩‍⚕️",
        "color": "#2ecc71",
        "salary": 4400,
        "savings": 750,
        "expenses": {"taxes": 820, "mortgage": 1000, "schoolLoan": 0, "carLoan": 300, "creditCards": 130, "retail": 200, "other": 300, "children": 0},
        "liabilities": {"mortgage": 96000, "schoolLoan": 0, "carLoan": 32000, "creditCards": 12000},
    },
    {
        "id": "police",
        "name": "Policía",
        "icon": "🚔",
        "color": "#3498db",
        "salary": 5000,
        "savings": 800,
        "expenses": {"taxes": 940, "mortgage": 1150, "schoolLoan": 0, "carLoan": 350, "creditCards": 140, "retail": 230, "other": 340, "children": 0},
        "liabilities": {"mortgage": 108000, "schoolLoan": 0, "carLoan": 36000, "creditCards": 14000},
    },
    {
        "id": "programmer",
        "name": "Programador",
        "icon": "👨‍💻",
        "color": "#9b59b6",
        "salary": 6000,
        "savings": 1500,
        "expenses": {"taxes": 1120, "mortgage": 1450, "schoolLoan": 600, "carLoan": 400, "creditCards": 170, "retail": 270, "other": 350, "children": 0},
        "liabilities": {"mortgage": 120000, "schoolLoan": 26000, "carLoan": 28000, "creditCards": 15000},
    },
    {
        "id": "pilot",
        "name": "Piloto",
        "icon": "✈️",
        "color": "#1abc9c",
        "salary": 8500,
        "savings": 1600,
        "expenses": {"taxes": 1600, "mortgage": 2000, "schoolLoan": 0, "carLoan": 550, "creditCards": 210, "retail": 350, "other": 490, "children": 0},
        "liabilities": {"mortgage": 168000, "schoolLoan": 0, "carLoan": 48000, "creditCards": 16000},
    },
    {
        "id": "engineer",
        "name": "Ingeniero",
        "icon": "👷",
        "color": "#f39c12",
        "salary": 7200,
        "savings": 1100,
        "expenses": {"taxes": 1360, "mortgage": 1750, "schoolLoan": 0, "carLoan": 500, "creditCards": 180, "retail": 300, "other": 450, "children": 0},
        "liabilities": {"mortgage": 148000, "schoolLoan": 0, "carLoan": 43000, "creditCards": 15000},
    },
    {
        "id": "manager",
        "name": "Gerente",
        "icon": "💼",
        "color": "#e74c3c",
        "salary": 9000,
        "savings": 2000,
        "expenses": {"taxes": 1740, "mortgage": 2200, "schoolLoan": 0, "carLoan": 600, "creditCards": 220, "retail": 380, "other": 520, "children": 0},
        "liabilities": {"mortgage": 183000, "schoolLoan": 0, "carLoan": 52000, "creditCards": 18000},
    },
    {
        "id": "lawyer",
        "name": "Abogada",
        "icon": "⚖️",
        "color": "#8e44ad",
        "salary": 13000,
        "savings": 2300,
        "expenses": {"taxes": 2540, "mortgage": 3200, "schoolLoan": 0, "carLoan": 900, "creditCards": 300, "retail": 500, "other": 650, "children": 0},
        "liabilities": {"mortgage": 260000, "schoolLoan": 0, "carLoan": 68000, "creditCards": 20000},
    },
    {
        "id": "doctor",
        "name": "Médico",
        "icon": "🩺",
        "color": "#c0392b",
        "salary": 16500,
        "savings": 2500,
        "expenses": {"taxes": 3250, "mortgage": 4100, "schoolLoan": 0, "carLoan": 1000, "creditCards": 400, "retail": 700, "other": 800, "children": 0},
        "liabilities": {"mortgage": 310000, "schoolLoan": 0, "carLoan": 76000, "creditCards": 22000},
    },
]

PROFESSIONS_BY_ID = {p["id"]: p for p in PROFESSIONS}

DREAMS = [
    {"id": "beach", "name": "Casa de ensueño en la playa", "cost": 120000},
    {"id": "island", "name": "Isla privada", "cost": 2000000},
    {"id": "classic_car", "name": "Coche clásico de colección", "cost": 45000},
    {"id": "art_gallery", "name": "Galería de arte", "cost": 300000},
    {"id": "vineyard", "name": "Viñedo familiar", "cost": 500000},
    {"id": "restaurant", "name": "Restaurante propio", "cost": 250000},
    {"id": "cruise", "name": "Vuelta al mundo en crucero", "cost": 180000},
    {"id": "ranch", "name": "Granja autosuficiente", "cost": 350000},
]

# ---------------------------------------------------------------------------
# Rat race board: 24 spaces (index order, clockwise, index 0 at top = Payday)
# ---------------------------------------------------------------------------
RAT_RACE_BOARD = [
    "PAYDAY", "SMALL", "SMALL", "BIG", "DOODAD", "SMALL",
    "MARKET", "BIG", "CHARITY", "SMALL", "BIG", "SMALL",
    "PAYDAY", "BIG", "DOODAD", "SMALL", "CHARITY", "BABY",
    "BIG", "MARKET", "SMALL", "BIG", "DOODAD", "DOWNSIZE",
]

RAT_RACE_SPACE_LABELS = {
    "PAYDAY": "Día de Pago",
    "SMALL": "Oportunidad\nmenor",
    "BIG": "Oportunidad\nmayor",
    "MARKET": "Mercado",
    "DOODAD": "Baratijas",
    "CHARITY": "Caridad",
    "BABY": "Bebé",
    "DOWNSIZE": "Despido",
}

RAT_RACE_COLORS = {
    "PAYDAY": "#e8e8e8",
    "SMALL": "#8cc63f",
    "BIG": "#4aa3df",
    "MARKET": "#ed1c24",
    "DOODAD": "#f7931e",
    "CHARITY": "#f15aa0",
    "BABY": "#8e44ad",
    "DOWNSIZE": "#fcee21",
}

# ---------------------------------------------------------------------------
# Fast track board: 12 spaces
# ---------------------------------------------------------------------------
FAST_TRACK_BOARD = [
    "CASHFLOW", "OPPORTUNITY", "DREAM", "OPPORTUNITY", "MARKET", "OPPORTUNITY",
    "CASHFLOW", "OPPORTUNITY", "DOODAD", "OPPORTUNITY", "DOWNSIZE", "DREAM",
]

FAST_TRACK_SPACE_LABELS = {
    "CASHFLOW": "Día de Flujo\nde Efectivo",
    "OPPORTUNITY": "Oportunidad",
    "DREAM": "Tu Sueño",
    "MARKET": "Mercado",
    "DOODAD": "Baratijas",
    "DOWNSIZE": "Crisis",
}

FAST_TRACK_COLORS = {
    "CASHFLOW": "#e8e8e8",
    "OPPORTUNITY": "#7a4fb5",
    "DREAM": "#ffd700",
    "MARKET": "#ed1c24",
    "DOODAD": "#f7931e",
    "DOWNSIZE": "#fcee21",
}

# ---------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------

SMALL_DEALS = [
    # Real estate (green)
    {"kind": "realEstate", "name": "Casa 3 dorm. / 2 baños", "cost": 50000, "down": 5000, "cashFlow": 100, "resale": [45000, 65000], "tags": ["house"]},
    {"kind": "realEstate", "name": "Casa 3/2 en buena zona", "cost": 55000, "down": 6000, "cashFlow": 150, "resale": [50000, 70000], "tags": ["house"]},
    {"kind": "realEstate", "name": "Casa 2/1 económica", "cost": 35000, "down": 3500, "cashFlow": 40, "resale": [32000, 45000], "tags": ["house"]},
    {"kind": "realEstate", "name": "Dúplex 4/2", "cost": 80000, "down": 12000, "cashFlow": 150, "resale": [75000, 95000], "tags": ["duplex"]},
    {"kind": "realEstate", "name": "Casa prefabricada con terreno", "cost": 25000, "down": 2500, "cashFlow": 25, "resale": [20000, 35000], "tags": ["house"]},
    {"kind": "realEstate", "name": "Condominio 1 dorm.", "cost": 45000, "down": 5000, "cashFlow": 50, "resale": [40000, 55000], "tags": ["condo"]},
    {"kind": "realEstate", "name": "Condominio de lujo", "cost": 60000, "down": 7000, "cashFlow": 100, "resale": [55000, 75000], "tags": ["condo"]},
    {"kind": "realEstate", "name": "Pequeño edificio 4 unidades", "cost": 90000, "down": 14000, "cashFlow": 250, "resale": [85000, 110000], "tags": ["apartment"]},
    # Stocks
    {"kind": "stock", "name": "Microsoft (MSFT)", "symbol": "MSFT", "price": 30},
    {"kind": "stock", "name": "Apple (AAPL)", "symbol": "AAPL", "price": 40},
    {"kind": "stock", "name": "Google (GOOG)", "symbol": "GOOG", "price": 100},
    {"kind": "stock", "name": "Amazon (AMZN)", "symbol": "AMZN", "price": 120},
    {"kind": "stock", "name": "Tesla (TSLA)", "symbol": "TSLA", "price": 200},
    {"kind": "stock", "name": "Netflix (NFLX)", "symbol": "NFLX", "price": 250},
    {"kind": "stock", "name": "PepsiCo (PEP)", "symbol": "PEP", "price": 70},
    {"kind": "stock", "name": "Banco Global (BGK)", "symbol": "BGK", "price": 25},
]

BIG_DEALS = [
    # Real estate
    {"kind": "realEstate", "name": "Edificio pequeño de apartamentos", "cost": 100000, "down": 20000, "cashFlow": 500, "resale": [90000, 120000], "tags": ["apartment"]},
    {"kind": "realEstate", "name": "Edificio mediano (12 unid.)", "cost": 200000, "down": 40000, "cashFlow": 1000, "resale": [180000, 250000], "tags": ["apartment"]},
    {"kind": "realEstate", "name": "Centro comercial local", "cost": 500000, "down": 100000, "cashFlow": 3000, "resale": [450000, 650000], "tags": ["commercial"]},
    {"kind": "realEstate", "name": "Terreno comercial", "cost": 150000, "down": 30000, "cashFlow": 600, "resale": [130000, 180000], "tags": ["commercial"]},
    {"kind": "realEstate", "name": "Complejo de 8 unidades", "cost": 250000, "down": 50000, "cashFlow": 1400, "resale": [230000, 300000], "tags": ["apartment"]},
    {"kind": "realEstate", "name": "Hotel boutique", "cost": 350000, "down": 70000, "cashFlow": 1800, "resale": [320000, 420000], "tags": ["commercial"]},
    # Businesses
    {"kind": "business", "name": "Franquicia de comida rápida", "cost": 120000, "down": 25000, "cashFlow": 800},
    {"kind": "business", "name": "Lavandería automática", "cost": 80000, "down": 15000, "cashFlow": 450},
    {"kind": "business", "name": "Empresa de software", "cost": 60000, "down": 10000, "cashFlow": 400},
    {"kind": "business", "name": "Negocio de internet", "cost": 40000, "down": 8000, "cashFlow": 250},
    {"kind": "business", "name": "Videoclub", "cost": 55000, "down": 11000, "cashFlow": 300},
    {"kind": "business", "name": "Kiosco de prensa", "cost": 30000, "down": 6000, "cashFlow": 150},
    {"kind": "business", "name": "Fábrica de velas artesanales", "cost": 90000, "down": 18000, "cashFlow": 500},
]

MARKET_CARDS = [
    # Real estate buyers
    {"kind": "buy", "title": "Mercado inmobiliario en auge", "text": "Un inversor quiere comprar una CASA y ofrece entre $45.000 y $65.000.", "buyTags": ["house"]},
    {"kind": "buy", "title": "Demanda de condominios", "text": "Un comprador busca CONDOMINIOS y ofrece entre $50.000 y $70.000.", "buyTags": ["condo"]},
    {"kind": "buy", "title": "Inversor de apartamentos", "text": "Un fondo busca APARTAMENTOS y ofrece entre $85.000 y $120.000.", "buyTags": ["apartment"]},
    {"kind": "buy", "title": "Compra de propiedades comerciales", "text": "Un mall busca COMERCIALES y ofrece entre $150.000 y $250.000.", "buyTags": ["commercial"]},
    {"kind": "buyBusiness", "title": "Interesados en negocios", "text": "Un empresario quiere comprar tu NEGOCIO. Ofrece entre 1,5x y 2x tu flujo mensual por 12 meses.", "multiplier": [1.5, 2.0]},
    # Stock sell
    {"kind": "stockSell", "title": "Microsoft se dispara", "text": "MSFT sube con fuerza. Un corredor ofrece comprarte acciones entre $45 y $65.", "symbol": "MSFT", "priceRange": [45, 65]},
    {"kind": "stockSell", "title": "Apple en máximos", "text": "AAPL rompe récords. Te ofrecen entre $60 y $90 por acción.", "symbol": "AAPL", "priceRange": [60, 90]},
    {"kind": "stockSell", "title": "Tesla en la luna", "text": "TSLA se dispara. Te ofrecen entre $300 y $450 por acción.", "symbol": "TSLA", "priceRange": [300, 450]},
    {"kind": "stockSell", "title": "Caída de Amazon", "text": "AMZN baja. Vendé si querés antes de que caiga más: entre $70 y $100.", "symbol": "AMZN", "priceRange": [70, 100]},
    {"kind": "stockSell", "title": "Netflix consolida", "text": "NFLX se estabiliza. Te ofrecen entre $180 y $240 por acción.", "symbol": "NFLX", "priceRange": [180, 240]},
    {"kind": "stockSell", "title": "Banco Global se recupera", "text": "BGK repunta. Te ofrecen entre $30 y $45 por acción.", "symbol": "BGK", "priceRange": [30, 45]},
    # Stock buy tips
    {"kind": "stockBuy", "title": "Oportunidad de compra: MSFT", "text": "Consejo de tu broker: MSFT está barata, comprala a $22 por acción.", "symbol": "MSFT", "price": 22},
    {"kind": "stockBuy", "title": "Oportunidad de compra: GOOG", "text": "Consejo de tu broker: GOOG tiene potencial, comprala a $80 por acción.", "symbol": "GOOG", "price": 80},
    {"kind": "stockBuy", "title": "Oportunidad de compra: PEP", "text": "PEP es estable y barata a $55 por acción.", "symbol": "PEP", "price": 55},
    {"kind": "stockBuy", "title": "Oportunidad de compra: BGK", "text": "BGK en su punto más bajo: $18 por acción.", "symbol": "BGK", "price": 18},
]

DOODADS = [
    {"name": "Televisor 60\" OLED", "cost": 1500, "expense": 0},
    {"name": "Bicicleta de montaña", "cost": 800, "expense": 0},
    {"name": "Barco usado", "cost": 6000, "expense": 250},
    {"name": "Consola de videojuegos", "cost": 500, "expense": 30},
    {"name": "Colección de arte", "cost": 2000, "expense": 0},
    {"name": "Moto de nieve", "cost": 3000, "expense": 100},
    {"name": "Suscripción de streaming", "cost": 300, "expense": 20},
    {"name": "Un perro", "cost": 250, "expense": 50},
    {"name": "Membresía de gimnasio", "cost": 700, "expense": 60},
    {"name": "Sillón de masajes", "cost": 1200, "expense": 0},
]

BABY_CARDS = [
    {"name": "¡Bebé #1!", "expense": 350, "text": "Llega un bebé a la familia. Gastos de hijos +$350/mes."},
    {"name": "¡Bebé!", "expense": 500, "text": "¡Bebé! Gastos de hijos +$500/mes."},
    {"name": "Adopción", "expense": 400, "text": "Adoptás a un nene. Gastos de hijos +$400/mes."},
    {"name": "¡Bebé!", "expense": 300, "text": "¡Sorpresa! Bebé. Gastos de hijos +$300/mes."},
    {"name": "¡Gemelos!", "expense": 650, "text": "¡Gemelos! Gastos de hijos +$650/mes."},
]

DOWNSIZE_CARDS = [
    {"name": "Despido", "turns": 3, "text": "Te despidieron. Perdés tu salario por 3 turnos."},
    {"name": "Reducción de personal", "turns": 2, "text": "Reducción de personal. Perdés tu salario por 2 turnos."},
    {"name": "Despido", "turns": 4, "text": "Te despidieron. Perdés tu salario por 4 turnos."},
]
