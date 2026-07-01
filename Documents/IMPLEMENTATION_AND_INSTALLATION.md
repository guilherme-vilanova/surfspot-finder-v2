# Implementation And Installation

## Requisitos
- Python 3.9+
- acesso a internet para Google Geocoding, Google Places e Open-Meteo
- chave valida da Google Maps Platform com Geocoding API e Places API habilitadas

## Dependencias atuais
Definidas em [`requirements.txt`](/requirements.txt):
- `Flask`
- `requests`
- `gunicorn`
- `python-dotenv`
- `mcp`
- `Flask-Limiter` (rate limiting)

Dependencias de desenvolvimento em [`requirements-dev.txt`](/requirements-dev.txt) (inclui `pytest`).

## Instalacao local
1. Entrar na pasta do projeto.
2. Criar ambiente virtual.
3. Instalar dependencias.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Configurar Google API
1. Criar projeto no Google Cloud Console.
2. Habilitar `Geocoding API`.
3. Habilitar `Places API`.
4. Habilitar `Maps Embed API` se quiser que o quadro lateral do mapa use o `place_id` exato da praia vencedora.
5. Criar uma API key em `APIs & Services > Credentials`.
6. Restringir a key para `Geocoding API`, `Places API` e `Maps Embed API`.
7. Definir a variavel `GOOGLE_MAPS_API_KEY`.

Use como base [`.env.example`](/.env.example), que agora tambem inclui:
- `SECRET_KEY` (**obrigatoria em producao** - o app nao sobe sem ela quando `FLASK_ENV=production`);
- `MARINE_PROVIDER`, `FORECAST_PROVIDER`, `GEOCODING_PROVIDER`, `PLACES_PROVIDER` (qual adaptador usar em cada capacidade);
- `RANKING_STRATEGY` (qual algoritmo de pontuacao usar);
- `CACHE_PATH`, `CACHE_TTL_SECONDS`;
- `RATELIMIT_STORAGE_URI`, `RATELIMIT_DEFAULT`, `RATE_LIMIT_SEARCH`, `RATE_LIMIT_AUTOCOMPLETE`.

Exemplo minimo de `.env` para desenvolvimento local:

```env
GOOGLE_MAPS_API_KEY=your_google_key_here
FLASK_ENV=development
SECRET_KEY=any-value-for-local-dev
```

O app e os MCP servers carregam esse arquivo por caminho absoluto a partir da raiz do projeto (`surfweb/config.py`), entao funcionam mesmo se o comando for executado de outro diretorio. Se `python-dotenv` nao estiver disponivel no ambiente, o projeto usa `env_loader.py` como fallback.

## Executar o app
```bash
source .venv/bin/activate
python app.py
```

O app sobe por padrao na porta `5001`, salvo override via `PORT`. Em desenvolvimento, defina `FLASK_ENV=development` (ou deixe `SECRET_KEY` vazio apenas fora de producao) - em producao (`FLASK_ENV=production`, o padrao), `SECRET_KEY` e obrigatoria.

## Executar os MCP servers
```bash
source .venv/bin/activate
python -m mcp_server.server           # Google: geocode_address, reverse_geocode
python -m mcp_server.weather_server   # Open-Meteo: get_marine_conditions, get_forecast_conditions
```

## Executar testes
```bash
source .venv/bin/activate
python -m pytest tests/
# ou, sem pytest instalado:
python -m unittest discover -s tests
```

## Estrategia de implementacao atual
### Backend
- `surfweb/` monta o app Flask (config, seguranca, rate limiting, rotas) e delega tudo de negocio para `services/`;
- `services/` orquestra `providers/` (dados externos) e `ranking/` (pontuacao);
- `providers/` isola cada API externa atras de uma interface (`providers/ports.py`), com adaptadores trocaveis por config;
- `ranking/` isola o algoritmo de pontuacao, tambem trocavel por config;
- `persistent_cache.py` + `cache/ttl.py` persistem caches de busca, mar e clima em disco;
- a origem continua dinamica (texto ou coordenadas).

### Frontend
- sem mudanca de comportamento: campo livre `location_query`, autocomplete remoto via Google Places, campos ocultos para coordenadas/metadados, chamada AJAX para reverse geocoding, submit automatico no fluxo de geolocalizacao;
- `templates/error.html` (novo) cobre erros 404/429/500 sem expor detalhes internos.

### Integracao Google
- HTTP concentrado em `mcp_server/google_client.py`;
- normalizado por `mcp_server/location_service.py`;
- exposto tanto como MCP tool (`mcp_server/server.py`) quanto como adaptador in-process para o app (`providers/google.py`).

### Integracao Open-Meteo
- HTTP concentrado em `providers/openmeteo.py`;
- exposto tanto como MCP tool (`mcp_server/weather_server.py`, sem cache) quanto como adaptador cacheado para o app (`services/caching.py`).

## Deploy
Para producao:
- definir `SECRET_KEY` e `GOOGLE_MAPS_API_KEY` no ambiente do servidor (o app recusa subir sem `SECRET_KEY` quando `FLASK_ENV=production`);
- habilitar `Places API` no mesmo projeto da chave usada pelo app;
- restringir a key por HTTP referrer, ja que o embed do mapa usa essa chave no frontend;
- manter liberado acesso HTTP de saida para Google Places e Open-Meteo;
- nao commitar `.env`;
- se rodar mais de um worker/processo, apontar `RATELIMIT_STORAGE_URI` para Redis em vez do padrao `memory://` (senao cada worker tem seu proprio contador de rate limit);
- reiniciar o servico apos configurar variaveis;
- se usar Render ou similar, manter a chave apenas nas environment variables da plataforma.

## Leitura complementar
- setup detalhado da Google API em [`README_GOOGLE_SETUP.md`](/README_GOOGLE_SETUP.md)
- MCP servers em [`mcp_server/README.md`](/mcp_server/README.md)
- arquitetura completa em [`INFRASTRUCTURE.md`](/Documents/INFRASTRUCTURE.md)
