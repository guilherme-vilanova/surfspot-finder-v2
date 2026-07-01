# Technical Reference

## Arquivos centrais
- [`app.py`](/app.py) - entrypoint fino, so chama `surfweb.create_app()`
- [`surfweb/factory.py`](/surfweb/factory.py), [`surfweb/config.py`](/surfweb/config.py), [`surfweb/container.py`](/surfweb/container.py)
- [`surfweb/blueprints/pages.py`](/surfweb/blueprints/pages.py), [`surfweb/blueprints/api.py`](/surfweb/blueprints/api.py)
- [`services/location_resolver.py`](/services/location_resolver.py), [`services/beach_discovery.py`](/services/beach_discovery.py), [`services/beach_evaluator.py`](/services/beach_evaluator.py), [`services/search_orchestrator.py`](/services/search_orchestrator.py), [`services/caching.py`](/services/caching.py), [`services/map_links.py`](/services/map_links.py)
- [`ranking/classic.py`](/ranking/classic.py), [`ranking/presentation.py`](/ranking/presentation.py), [`ranking/factory.py`](/ranking/factory.py)
- [`providers/ports.py`](/providers/ports.py), [`providers/openmeteo.py`](/providers/openmeteo.py), [`providers/google.py`](/providers/google.py), [`providers/registry.py`](/providers/registry.py)
- [`cache/ttl.py`](/cache/ttl.py), [`persistent_cache.py`](/persistent_cache.py)
- [`surf_metadata.py`](/surf_metadata.py)
- [`templates/index.html`](/templates/index.html), [`templates/error.html`](/templates/error.html)
- [`mcp_server/google_client.py`](/mcp_server/google_client.py), [`mcp_server/location_service.py`](/mcp_server/location_service.py), [`mcp_server/server.py`](/mcp_server/server.py), [`mcp_server/weather_server.py`](/mcp_server/weather_server.py)

## Principais rotas
### `GET/POST /` (`surfweb/blueprints/pages.py: home`)
- valida `location_query`, `max_distance_km`, `result_limit`, `skill_level`, `origin_lat`, `origin_lon` no servidor (`surfweb/validation.py`);
- resolve a origem via `container.location_resolver`;
- monta o ranking via `container.search_orchestrator.build_rankings_with_radius_fallback`;
- renderiza `index.html`. Limitada por `RATE_LIMIT_SEARCH` no metodo POST.

### `POST /api/reverse-geocode` (`surfweb/blueprints/api.py: reverse_geocode`)
- recebe `lat`/`lon`, valida faixa (-90..90 / -180..180);
- resolve endereco amigavel via `container.providers.geocoding`;
- retorna JSON. Limitada por `RATE_LIMIT_AUTOCOMPLETE`.

### `GET /api/location-autocomplete` (`surfweb/blueprints/api.py: location_autocomplete`)
- recebe `q`, sanitiza e exige minimo de 2 caracteres;
- consulta `container.providers.places.autocomplete_places`;
- retorna sugestoes normalizadas. Limitada por `RATE_LIMIT_AUTOCOMPLETE`.

## `surfweb/` - camada web
### `Config` (`surfweb/config.py`)
Le toda configuracao do ambiente. `Config.resolved_secret_key()` levanta `RuntimeError` se `FLASK_ENV=production` e `SECRET_KEY` estiver vazio.

### `ServiceContainer` (`surfweb/container.py`)
Composition root: monta `PersistentTTLCache`, o `ProviderBundle` (via `providers.build_provider_bundle`), os providers cacheados (`CachedMarineProvider`/`CachedForecastProvider`), a `RankingStrategy` (via `ranking.build_ranking_strategy`) e os services (`LocationResolver`, `BeachDiscoveryService`, `BeachEvaluator`, `SearchOrchestrator`). Fica em `app.extensions["surfspot_container"]`.

### `surfweb/validation.py`
- `parse_optional_float`, `parse_latitude`, `parse_longitude` (com faixa valida);
- `clamp_radius_km`, `parse_result_limit`, `parse_skill_level` (fallback seguro em vez de lançar exceção para o usuário final);
- `sanitize_location_query` (remove caracteres nao imprimiveis, limita tamanho).

### `surfweb/security.py`
`register_security_headers(app)` adiciona CSP, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` e `Strict-Transport-Security` (fora de debug/testing) em toda resposta.

### `surfweb/errors.py`
Handlers para 404/429/500 - nunca devolvem stack trace; JSON para rotas `/api/*`, HTML (`error.html`) para as demais.

## `services/`
### `LocationResolver.resolve_origin(...)`
Resolve a origem: coordenadas do navegador ou geocoding de texto via `GeocodingProvider`. Retorna `(origin, error_message)`.

### `BeachDiscoveryService.find_candidate_beaches(origin, max_distance_km)`
Descobre praias via `PlacesProvider.find_nearby_beaches`, deduplica por nome canonico (`surf_metadata.canonical_beach_name`) e filtra por raio (`haversine_km`). Cacheado por `(lat, lon, raio)`.

### `BeachEvaluator.evaluate(beach, skill_level)`
Busca leituras de `MarineDataProvider`/`ForecastProvider`, pula o forecast quando o spot e dinamico e nao tem sinal de mar (`has_surf_marine_signal`), pontua via `RankingStrategy.score(...)` e monta o dict de apresentacao completo (usado direto no template).

### `SearchOrchestrator.build_beach_rankings` / `build_rankings_with_radius_fallback`
Pipeline completo: descoberta -> limite de avaliacao (`MIN_BEACHES_TO_EVALUATE`/`MAX_BEACHES_TO_EVALUATE`) -> avaliacao paralela (`ThreadPoolExecutor`) -> filtro de spots dinamicos sem sinal de mar -> ordenacao -> cache do resultado final. O fallback de raio usa `RADIUS_EXPANSION_STEPS` (hoje vazio, mesma configuracao do app original).

### `services/caching.py`
`CachedMarineProvider` / `CachedForecastProvider` implementam os mesmos Protocols de `providers/ports.py`, adicionando um `LayeredCache` por cima de qualquer provider concreto - a troca de provider nao muda como o cache funciona.

### `services/map_links.py`
`build_beach_map_embed_url(beach, google_maps_api_key)` e `build_beach_google_maps_url(beach)` - usam `place_id` quando disponivel, caem para coordenadas quando nao.

## `ranking/`
### `ClassicHeuristicRanking` (`ranking/classic.py`)
- `wind_quality_score`, `wave_quality_score`, `swell_quality_score`: mesma heuristica original, agora funcoes puras e testadas isoladamente;
- `score(marine, forecast, beach, skill_level) -> ScoreBreakdown`: combina os tres componentes.

### `ranking/presentation.py`
`classify_condition`, `classify_color`, `degrees_to_cardinal_arrow`, `weather_label` - traducao de score/leitura para texto/cor da UI.

### `ranking/factory.py`
`build_ranking_strategy(name)` - escolhe a estrategia pelo nome (`RANKING_STRATEGY`). Adicionar uma nova estrategia = nova classe implementando `RankingStrategy` + registro no dict `STRATEGIES`.

## `providers/`
### `providers/ports.py`
`MarineDataProvider`, `ForecastProvider`, `GeocodingProvider`, `PlacesProvider` (Protocols) + `ProviderError` (exececao comum).

### `OpenMeteoMarineProvider` / `OpenMeteoForecastProvider` (`providers/openmeteo.py`)
Mesma logica de `get_marine_conditions`/`get_forecast_conditions` do `app.py` original, incluindo `safe_get` (retry) e `has_surf_marine_signal`.

### `GoogleGeocodingProvider` / `GooglePlacesProvider` (`providers/google.py`)
Delegam para `mcp_server.location_service.GoogleLocationService` e traduzem `LocationServiceError` em `ProviderError` na fronteira do adaptador.

### `providers/registry.py`
`build_provider_bundle(marine_provider, forecast_provider, geocoding_provider, places_provider) -> ProviderBundle`. Adicionar uma nova API = nova classe implementando o Protocol certo + entrada no dict correspondente (`MARINE_PROVIDERS`, etc.).

## `mcp_server/`
### `GoogleGeocodingClient` / `GooglePlacesClient` (`google_client.py`)
Inalterados - chamam a Geocoding API e o endpoint `places:searchNearby`/`places:autocomplete`.

### `GoogleLocationService` (`location_service.py`)
Inalterado na logica; `LocationServiceError` agora e documentado como "a excecao propria deste modulo", traduzida por `providers/google.py` para quem consome via `providers/`.

### `server.py`
Ferramentas MCP: `geocode_address(query)`, `reverse_geocode(lat, lon)`.

### `weather_server.py` (novo)
Ferramentas MCP: `get_marine_conditions(lat, lon)`, `get_forecast_conditions(lat, lon)` - usam `providers/openmeteo.py` diretamente, sem cache (a camada web e que adiciona cache, via `services/caching.py`).

## Metadata auxiliar de surf
### `surf_metadata.py` (inalterado)
- `canonical_beach_name`: canonicaliza nomes de praia para deduplicacao;
- `SURF_SPOT_METADATA`: spots conhecidos com `preferred_swell_label`/`preferred_swell_degrees`;
- `apply_surf_metadata`: aplica esse metadata a um beach dict.

## Campos principais do formulario
- `location_query`, `origin_lat`, `origin_lon`, `origin_source`, `resolved_location_label`, `max_distance_km`, `result_limit`, `skill_level`

## Configuracao tecnica relevante
- `surfweb/config.py` carrega `.env` via `env_loader.load_local_env` (ou `python-dotenv`) usando caminho absoluto do projeto;
- `MIN_RADIUS_KM`/`MAX_RADIUS_KM`/`DEFAULT_RADIUS_KM`, `ALLOWED_RESULT_LIMITS`, `ALLOWED_SKILL_LEVELS` sao constantes de `Config`, nao mais espalhadas em `app.py`;
- `persistent_cache.PersistentTTLCache` continua gravando em `CACHE_PATH` (`.cache/surfspot_cache.json` por padrao).

## Testes
- `tests/test_app.py`: integracao via Flask test client (fluxo de busca, validacao de entrada, endpoints de API, headers de seguranca, rate limiting);
- `tests/test_services.py`: `BeachDiscoveryService`, `BeachEvaluator`, `SearchOrchestrator`, `LocationResolver` com providers fake;
- `tests/test_ranking.py`: `ClassicHeuristicRanking`, `ranking.factory`, `ranking.presentation`;
- `tests/test_providers_openmeteo.py`: `safe_get`, `has_surf_marine_signal`, parsing das respostas Open-Meteo;
- `tests/test_validation.py`: `surfweb/validation.py`;
- `tests/test_location_service.py`: inalterado - `GoogleGeocodingClient`, `GooglePlacesClient`, `GoogleLocationService`.

## Funcionalidades atuais
- busca por localizacao digitada e por localizacao atual;
- descoberta dinamica de praias por coordenadas e raio (Google Places);
- reverse geocoding interno;
- ranking de praias por score, com algoritmo isolado e trocavel;
- providers de mar/vento/geocoding/places trocaveis por config, sem mudar codigo de negocio;
- destaque da melhor praia, tabela de resultados;
- cache em memoria + disco;
- rate limiting, headers de seguranca, validacao de entrada no servidor;
- ferramentas MCP para Google (geocoding/places) e Open-Meteo (mar/clima);
- testes unitarios por camada (web, services, ranking, providers).
