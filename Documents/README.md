# SurfSpot Finder Documentation

Esta pasta concentra a documentacao principal da versao `Demo` do SurfSpot Finder.

## Estrutura recomendada
- [`INFRASTRUCTURE.md`](/Users/camilagoulartlima/Documents/surfspot-finder/Demo/Documents/INFRASTRUCTURE.md): arquitetura, componentes, integracoes e fluxo de dados.
- [`USABILITY.md`](/Users/camilagoulartlima/Documents/surfspot-finder/Demo/Documents/USABILITY.md): experiencia do usuario, fluxos da interface e comportamento esperado.
- [`IMPLEMENTATION_AND_INSTALLATION.md`](/Users/camilagoulartlima/Documents/surfspot-finder/Demo/Documents/IMPLEMENTATION_AND_INSTALLATION.md): setup local, instalacao, execucao, Google API e MCP server.
- [`TECHNICAL_REFERENCE.md`](/Users/camilagoulartlima/Documents/surfspot-finder/Demo/Documents/TECHNICAL_REFERENCE.md): principais metodos, funcoes, endpoints e contratos internos.
- [`DOCUMENTATION_POLICY.md`](/Users/camilagoulartlima/Documents/surfspot-finder/Demo/Documents/DOCUMENTATION_POLICY.md): regra de manutencao da documentacao e quando atualizar cada arquivo.

## Melhor forma de documentar este projeto
Para este repositorio, a melhor abordagem e separar a documentacao por objetivo:
- documentacao conceitual: visao de arquitetura e decisoes do sistema;
- documentacao operacional: como instalar, configurar e rodar;
- documentacao de produto/UX: como a ferramenta funciona para o usuario;
- documentacao tecnica de referencia: funcoes, contratos, endpoints e responsabilidades.

Esse formato reduz duplicacao, facilita onboarding e deixa claro qual arquivo atualizar quando alguma parte do sistema mudar.

## Escopo atual da ferramenta
- Busca de praias de surf com base em uma origem informada pelo usuario.
- Origem por texto livre ou por geolocalizacao atual do navegador.
- Resolucao de endereco via Google Geocoding.
- Ranking de praias usando Google Places e dados de mar/clima da Open-Meteo.
- Arquitetura em camadas (`surfweb/`, `services/`, `ranking/`, `providers/`) para que trocar uma API externa ou o algoritmo de ranking nao exija reescrever o app.
- MCP servers para Google (`mcp_server/server.py`) e Open-Meteo (`mcp_server/weather_server.py`), reaproveitando o mesmo codigo usado pelo app web.
- Seguranca de base: `SECRET_KEY` obrigatoria em producao, headers de seguranca, rate limiting, validacao de entrada no servidor.
