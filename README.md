# Devin Index Repo Script

Ferramenta automatizada para descobrir, extrair e indexar repositórios de software na Plataforma Devin. Faz a ponte entre interfaces web de repositórios e APIs RESTful via automação de navegador.

## Pré-requisitos

- Python 3.8+
- Google Chrome / Chromium
- ChromeDriver compatível com a versão do Chrome

## Instalação

```bash
git clone https://github.com/rafaelakio/devin-index-repo-script.git
cd devin-index-repo-script
pip install -r requirements.txt
```

## Como Usar

```bash
python src/main.py [opções]
```

O script irá:
1. Abrir o navegador para login manual (MFA/SSO)
2. Alternar para modo headless após autenticação
3. Descobrir e extrair metadados dos repositórios
4. Indexar via API da Plataforma Devin

## Arquitetura

O sistema utiliza uma arquitetura modular:

- **`src/main.py`**: Orquestrador principal e ponto de entrada
- **`src/cli.py`**: Parsing de argumentos de linha de comando
- **`browser/`**: Gerenciamento do WebDriver Selenium e persistência de sessão
- **`scraper/`**: Navegação, parsing DOM e extração de metadados
- **`indexer/`**: Cliente API para a Plataforma Devin com retry e rate-limit
- **`utils/`**: Logging, serialização de output e métricas

Para mais detalhes, consulte [ARCHITECTURE.md](ARCHITECTURE.md).

## Como Contribuir

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para diretrizes de contribuição.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.
