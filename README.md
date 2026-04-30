# Devin Index Repo Script

Ferramenta automatizada para descobrir, extrair e indexar repositórios de software na Plataforma Devin. Faz a ponte entre interfaces web de repositórios e APIs RESTful via automação de navegador.

## Pré-requisitos

- Python 3.8+
- Microsoft Edge (já disponível no Windows — não requer instalação adicional)

> O script usa o **Microsoft Edge** via `webdriver-manager`, que baixa automaticamente
> o `msedgedriver` compatível com a versão instalada na máquina.

## Instalação

```bash
git clone https://github.com/rafaelakio/devin-index-repo-script.git
cd devin-index-repo-script
pip install -r requirements.txt
```

Copie o arquivo de variáveis de ambiente:

```bash
cp .env.example .env
# edite .env com a URL da sua organização
```

## Como Usar

```bash
# Primeira execução — abre o Edge para login manual
python src/main.py --indexing-url "https://devin.ai/org/MEU_ORG/settings/indexing" --search-term "poc"

# Execuções seguintes — reutiliza a sessão salva
python src/main.py --indexing-url "https://devin.ai/org/MEU_ORG/settings/indexing" --search-term "data" --output results.json

# Ver todas as opções
python src/main.py --help
```

O script irá:
1. Abrir o Edge para login manual (suporte a MFA/SSO)
2. Salvar os cookies de sessão para reutilização
3. Alternar para modo headless após autenticação
4. Buscar e extrair repositórios correspondentes ao termo de busca
5. Indexar as branches `main` e `develop` de cada repositório encontrado
6. Gerar um relatório JSON com os resultados

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
