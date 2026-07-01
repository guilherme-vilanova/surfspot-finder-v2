# Infrastructure

## Visao geral
O SurfSpot Finder e uma aplicacao web em Flask que recomenda praias de surf a partir de uma origem escolhida pelo usuario. Desde a reestruturacao arquitetural, o app segue um estilo de camadas/portas-e-adaptadores:

- **web** (`surfweb/`): factory do Flask, config, seguranca, rotas (blueprints);
- **services** (`services/`): orquestracao - resolve origem, descobre praias, avalia e ranqueia;
- **ranking** (`ranking/`): algoritmo de pontuacao, isolado de HTTP/Flask/cache;
- **providers** (`providers/`): interfaces (`ports.py`) + adaptadores para cada API externa (Open-Meteo, Google);
- **mcp_server/**: os mesmos adaptadores de `providers/` expostos como ferramentas MCP, reutilizaveis por qualquer agente/cliente MCP;
- **cache** (`cache/`): cache em memoria + persistente em disco, generico e sem conhecimento do dominio.

O template segue em [`templates/index.html`](/templates/index.html) e o entrypoint fino continua em [`app.py`](/app.py), que so chama `surfweb.create_app()`.

## Por que essa estrutura
A motivacao da reestruturacao foi tripla:
1. **Solidez e seguranca**: separar Flask (rotas/validacao/seguranca) de regras de negocio, com testes por camada.
2. **Trocar API sem reescrever o app**: nenhuma parte de `services/` ou `ranking/` importa `requests` ou sabe que a API de mar e a Open-Meteo, ou que a geocodificacao e o Google. Elas dependem apenas das interfaces em `providers/ports.py`.
3. **Iterar no algoritmo de ranking com seguranca**: `ranking/` e um pacote isolado, testado com funcoes puras, para o score poder mudar com frequencia sem risco para o resto do app.

## Componentes principais

### 1. `surfweb/` - camada web (Flask)
Responsavel por:
- `factory.py`: cria o app, registra config, seguranca, rate limiting, error handlers, blueprints, e guarda o `ServiceContainer` em `app.extensions["surfspot_container"]`;
- `config.py`: toda configuracao via variaveis de ambiente (chaves, providers ativos, estrategia de ranking, cache, rate limits);
- `container.py`: composition root - monta providers + ranking + services a partir da config;
- `security.py`: headers de seguranca (CSP, X-Frame-Options, etc.);
- `errors.py`: handlers de 404/429/500 que nunca expoem stack trace ao usuario;
- `validation.py`: valida tudo que vem da requisicao (lat/lon, raio, result_limit, skill_level, texto de busca) antes de chegar nos services;
- `blueprints/pages.py` e `blueprints/api.py`: as rotas HTTP, hoje bem mais finas do que o `app.py` original - so validam entrada, chamam o container e renderizam.

### 2. `services/` - orquestracao
- `location_resolver.py`: resolve a origem (coordenadas do browser ou geocoding de texto);
- `beach_discovery.py`: descobre praias candidatas via `PlacesProvider`, deduplica e filtra por raio;
- `beach_evaluator.py`: combina leituras de mar/vento de um `MarineDataProvider`/`ForecastProvider` com uma `RankingStrategy` para montar a linha de resultado de uma praia;
- `search_orchestrator.py`: pipeline completo - descoberta, avaliacao paralela, ordenacao, fallback de raio, cache de resultado final;
- `caching.py`: decoradores `CachedMarineProvider`/`CachedForecastProvider` que adicionam cache em torno de qualquer provider, sem o provider saber disso;
- `map_links.py`: monta as URLs de embed/link do Google Maps para a praia vencedora.

### 3. `ranking/` - algoritmo de pontuacao
- `ports.py`: interface `RankingStrategy` + `ScoreBreakdown`;
- `classic.py`: a heuristica original (wave/wind/swell score), como uma estrategia entre outras possiveis;
- `presentation.py`: `classify_condition`, `classify_color`, seta de direcao, label de clima - traduz score/leitura em texto/cor para a UI;
- `factory.py`: escolhe a estrategia pelo nome (`RANKING_STRATEGY` no `.env`). Novas estrategias so precisam implementar `RankingStrategy` e se registrar aqui.

### 4. `providers/` - integracoes externas
- `ports.py`: `MarineDataProvider`, `ForecastProvider`, `GeocodingProvider`, `PlacesProvider` + `ProviderError` (erro comum a qualquer provider);
- `openmeteo.py`: `OpenMeteoMarineProvider` e `OpenMeteoForecastProvider` (onda, vento, clima);
- `google.py`: `GoogleGeocodingProvider` e `GooglePlacesProvider`, que delegam para `mcp_server/location_service.py` e traduzem `LocationServiceError` em `ProviderError`;
- `registry.py`: monta o conjunto de providers ativos a partir de nomes vindos da config (`MARINE_PROVIDER`, `FORECAST_PROVIDER`, `GEOCODING_PROVIDER`, `PLACES_PROVIDER`).

### 5. `mcp_server/` - integracoes tambem expostas via MCP
- `google_client.py` / `location_service.py`: a implementacao real de Geocoding/Places (usada por `providers/google.py`);
- `server.py`: expoe `geocode_address` e `reverse_geocode` como ferramentas MCP;
- `weather_server.py` (novo): expoe `get_marine_conditions` e `get_forecast_conditions` como ferramentas MCP, reaproveitando `providers/openmeteo.py` sem duplicar codigo.

### 6. Metadata de surf
`surf_metadata.py` continua na raiz (usado tanto por `providers/google.py`, via `mcp_server/location_service.py`, quanto potencialmente por `ranking/`), aplicando heuristicas de deduplicacao de nome e swell preferido para spots conhecidos.

### 7. Cache
`cache/ttl.py` fornece `LayeredCache` (memoria + `persistent_cache.PersistentTTLCache` em disco), usado tanto para leituras de mar/vento (`services/caching.py`) quanto para descoberta de praias e resultado de busca (`services/beach_discovery.py`, `services/search_orchestrator.py`).

## Fluxo de dados
### Busca manual
1. `surfweb/blueprints/pages.py` valida a entrada (raio, limite de resultados, skill level, texto).
2. `container.location_resolver.resolve_origin(...)` chama `providers.geocoding` (Google) para resolver o texto em coordenadas.
3. `container.search_orchestrator.build_rankings_with_radius_fallback(...)` chama `beach_discovery_service` (Google Places) e depois `beach_evaluator` (Open-Meteo + `ranking_strategy`) para cada praia candidata, em paralelo.
4. O resultado ordenado e renderizado por `templates/index.html`.

### Busca por localizacao atual
1. O navegador usa `navigator.geolocation`.
2. O frontend chama `POST /api/reverse-geocode`, que usa `providers.geocoding.reverse_geocode`.
3. O formulario e submetido automaticamente com as coordenadas resolvidas, seguindo o mesmo pipeline da busca manual.

## Seguranca
- `SECRET_KEY` e obrigatoria quando `FLASK_ENV=production` - o app falha ao subir sem ela, em vez de rodar silenciosamente sem protecao de sessao;
- headers de seguranca (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`, `Referrer-Policy`, `Strict-Transport-Security` fora de debug) aplicados em toda resposta (`surfweb/security.py`);
- rate limiting por IP via Flask-Limiter nas rotas que chamam APIs pagas do Google (`/`, `/api/location-autocomplete`, `/api/reverse-geocode`), configuravel via `.env`;
- toda entrada de requisicao e validada no servidor (`surfweb/validation.py`) - `result_limit`, `skill_level`, `max_distance_km`, `lat`/`lon` fora dos limites nunca mais geram um erro 500 bruto;
- erros inesperados sao logados via `logging` (nao mais `print`) e nunca retornam stack trace ao usuario (`surfweb/errors.py`).

## Configuracao e segredos
- `GOOGLE_MAPS_API_KEY`, `GOOGLE_GEOCODING_BASE_URL`, `GOOGLE_PLACES_NEARBY_BASE_URL`, `GOOGLE_PLACES_AUTOCOMPLETE_BASE_URL`: integracao Google;
- `SECRET_KEY`, `FLASK_ENV`, `FLASK_DEBUG`: config do Flask;
- `MARINE_PROVIDER`, `FORECAST_PROVIDER`, `GEOCODING_PROVIDER`, `PLACES_PROVIDER`: qual adaptador usar em cada capacidade (ver `providers/registry.py`);
- `RANKING_STRATEGY`: qual algoritmo de pontuacao usar (ver `ranking/factory.py`);
- `CACHE_PATH`, `CACHE_TTL_SECONDS`: cache persistente;
- `RATELIMIT_STORAGE_URI`, `RATELIMIT_DEFAULT`, `RATE_LIMIT_SEARCH`, `RATE_LIMIT_AUTOCOMPLETE`: rate limiting.
- Todas ficam fora do codigo, em `.env` local ou no ambiente de deploy. Ver [`.env.example`](/.env.example).

## Caching
Sem mudanca de comportamento para o usuario: continua em memoria + persistido em disco (`.cache/surfspot_cache.json` por padrao), agora encapsulado em `cache.ttl.LayeredCache` e reutilizado por quatro pontos diferentes (mar, vento, descoberta de praias, resultado de busca) em vez de logica duplicada em `app.py`.

## Otimizacoes de performance
- o ranking avalia primeiro as praias mais proximas e limita quantos candidatos recebem chamadas externas (`services/search_orchestrator.py`);
- spots dinamicos sem sinal util da Marine API nao consomem chamada adicional de forecast (`services/beach_evaluator.py`);
- a avaliacao de candidatos roda em paralelo via `ThreadPoolExecutor`;
- as chamadas para Open-Meteo usam retry curto e timeouts menores para falhar mais rapido quando o provedor esta lento (`providers/openmeteo.py`).
