# Arquitetura da Aplicação - Devin Repository Indexer

## Diagrama de Componentes

```mermaid
graph TB
    subgraph "CLI Layer"
        CLI[CLI Parser<br/>cli.py]
    end
    
    subgraph "Browser Management"
        SM[Selenium Manager<br/>selenium_manager.py]
        SH[Session Handler<br/>session_handler.py]
    end
    
    subgraph "Web Scraping"
        SEARCH[Search Module<br/>search.py]
        EXTRACT[Data Extractor<br/>extractor.py]
    end
    
    subgraph "Indexing Layer"
        API[API Client<br/>api_client.py]
        RETRY[Retry Handler<br/>retry_handler.py]
    end
    
    subgraph "Utilities"
        LOG[Logger<br/>logger.py]
        OUT[Output Writer<br/>output.py]
    end
    
    subgraph "External Systems"
        DEVIN[Devin Platform]
        CHROME[Chrome Browser]
    end
    
    CLI --> SM
    CLI --> LOG
    SM --> SH
    SM --> CHROME
    SH --> CHROME
    SM --> SEARCH
    SEARCH --> EXTRACT
    EXTRACT --> API
    API --> RETRY
    RETRY --> DEVIN
    API --> OUT
    OUT --> LOG
    
    style CLI fill:#e1f5ff
    style SM fill:#fff3e0
    style SEARCH fill:#f3e5f5
    style API fill:#e8f5e9
    style LOG fill:#fce4ec
    style DEVIN fill:#ffebee
    style CHROME fill:#ffebee
```

## Fluxo de Dados

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Selenium
    participant Browser
    participant Scraper
    participant Indexer
    participant DevinAPI
    participant Output

    User->>CLI: Execute with args
    CLI->>Selenium: Initialize Chrome
    Selenium->>Browser: Open browser
    
    alt No saved session
        Browser->>User: Show login page
        User->>Browser: Manual login
        Browser->>Selenium: Login complete
        Selenium->>Selenium: Save cookies
    else Session exists
        Selenium->>Browser: Load cookies
    end
    
    Selenium->>Browser: Switch to headless
    CLI->>Scraper: Search repositories
    Scraper->>Browser: Navigate and extract
    Browser-->>Scraper: Repository list
    
    loop For each repository
        Scraper->>Scraper: Filter branches
        loop For each branch (main/develop)
            Scraper->>Indexer: Index request
            Indexer->>DevinAPI: POST indexing data
            
            alt Success
                DevinAPI-->>Indexer: 200 OK
                Indexer->>Output: Log success
            else Failure
                DevinAPI-->>Indexer: Error
                Indexer->>Indexer: Retry with backoff
            end
        end
    end
    
    Output->>Output: Generate JSON
    Output->>User: Save results file
    Selenium->>Browser: Close
```

## Estrutura de Classes

```mermaid
classDiagram
    class CLIParser {
        +parse_arguments()
        +validate_args()
        -url: str
        -search_term: str
        -headless: bool
        -output_path: str
    }
    
    class SeleniumManager {
        +initialize_driver()
        +close_driver()
        +switch_to_headless()
        +wait_for_login()
        -driver: WebDriver
        -options: ChromeOptions
    }
    
    class SessionHandler {
        +save_cookies()
        +load_cookies()
        +is_session_valid()
        -session_file: str
        -cookies: dict
    }
    
    class RepositorySearch {
        +search_repositories()
        +handle_pagination()
        +extract_repo_list()
        -search_term: str
        -current_page: int
    }
    
    class DataExtractor {
        +extract_repo_info()
        +get_branches()
        +filter_branches()
        -repo_data: dict
    }
    
    class IndexingAPIClient {
        +index_repository()
        +prepare_payload()
        -api_url: str
        -session: requests.Session
    }
    
    class RetryHandler {
        +retry_with_backoff()
        +apply_rate_limit()
        -max_retries: int
        -delay: float
    }
    
    class OutputWriter {
        +write_json()
        +format_results()
        +add_metadata()
        -output_path: str
        -results: list
    }
    
    CLIParser --> SeleniumManager
    SeleniumManager --> SessionHandler
    SeleniumManager --> RepositorySearch
    RepositorySearch --> DataExtractor
    DataExtractor --> IndexingAPIClient
    IndexingAPIClient --> RetryHandler
    IndexingAPIClient --> OutputWriter
```

## Padrões de Design Utilizados

### 1. Singleton Pattern
- **SeleniumManager**: Garante uma única instância do WebDriver
- **Logger**: Instância única de logging para toda aplicação

### 2. Strategy Pattern
- **RetryHandler**: Diferentes estratégias de retry (exponential, linear, fixed)
- **DataExtractor**: Diferentes estratégias de extração baseadas na estrutura da página

### 3. Factory Pattern
- **WebDriver Factory**: Criação de diferentes tipos de drivers (Chrome, Firefox)
- **Output Factory**: Criação de diferentes formatos de saída (JSON, CSV)

### 4. Observer Pattern
- **Progress Tracker**: Notifica sobre progresso da indexação
- **Logger**: Observa eventos e registra logs

### 5. Command Pattern
- **CLI Commands**: Encapsula operações como comandos executáveis
- **API Operations**: Cada operação de API como comando independente

## Gerenciamento de Estado

```mermaid
stateDiagram-v2
    [*] --> Initializing
    Initializing --> CheckingSession
    
    CheckingSession --> LoadingSession: Session exists
    CheckingSession --> WaitingLogin: No session
    
    WaitingLogin --> Authenticated: Login successful
    LoadingSession --> Authenticated: Session valid
    LoadingSession --> WaitingLogin: Session invalid
    
    Authenticated --> Searching: Start search
    Searching --> Extracting: Results found
    Extracting --> Indexing: Data extracted
    
    Indexing --> RateLimiting: API call made
    RateLimiting --> Indexing: Delay complete
    Indexing --> Retrying: API error
    Retrying --> Indexing: Retry attempt
    Retrying --> Failed: Max retries
    
    Indexing --> WritingOutput: All indexed
    Failed --> WritingOutput: Partial results
    
    WritingOutput --> Cleanup
    Cleanup --> [*]
```

## Tratamento de Concorrência

### Estratégia de Threading
- **Main Thread**: Gerenciamento do Selenium e navegação
- **Worker Threads**: Chamadas paralelas à API (com rate limiting)
- **Logger Thread**: Processamento assíncrono de logs

### Sincronização
- **Locks**: Proteção de recursos compartilhados (cookies, session)
- **Queues**: Fila de repositórios para indexação
- **Semaphores**: Controle de rate limiting

## Segurança e Privacidade

### Dados Sensíveis
1. **Cookies de Sessão**
   - Armazenados em arquivo criptografado
   - Permissões restritas (600)
   - Não versionados no Git

2. **Logs**
   - Sanitização de dados sensíveis
   - Rotação automática
   - Retenção limitada

3. **API Keys**
   - Variáveis de ambiente
   - Nunca em código-fonte
   - Validação antes do uso

### Comunicação
- HTTPS obrigatório
- Validação de certificados SSL
- Timeout em requisições

## Performance e Otimização

### Caching
- Cache de resultados de busca
- Cache de estrutura de páginas
- TTL configurável

### Batch Processing
- Agrupamento de requisições
- Processamento em lote
- Redução de overhead

### Resource Management
- Pool de conexões HTTP
- Reuso de sessões
- Cleanup automático de recursos

## Monitoramento e Observabilidade

### Métricas Coletadas
- Tempo de execução total
- Tempo médio por indexação
- Taxa de sucesso/falha
- Número de retries
- Rate limit hits

### Logs Estruturados
```json
{
  "timestamp": "2026-04-30T01:30:00Z",
  "level": "INFO",
  "component": "IndexingAPIClient",
  "action": "index_repository",
  "repository": "org/repo",
  "branch": "main",
  "duration_ms": 1250,
  "status": "success"
}
```

### Health Checks
- Validação de sessão ativa
- Conectividade com API
- Disponibilidade do WebDriver
- Espaço em disco para logs

## Escalabilidade

### Horizontal Scaling
- Múltiplas instâncias com diferentes termos de busca
- Distribuição de carga via queue system
- Coordenação via Redis/database

### Vertical Scaling
- Otimização de memória do Selenium
- Processamento paralelo de repositórios
- Tuning de thread pools

## Deployment

### Containerização (Docker)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y chromium chromium-driver
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/
WORKDIR /app
CMD ["python", "src/main.py"]
```

### CI/CD Pipeline
1. Lint (flake8, black)
2. Unit tests
3. Integration tests
4. Build Docker image
5. Push to registry
6. Deploy to environment

## Manutenção

### Atualizações
- Selenium WebDriver: Automático via webdriver-manager
- Dependências Python: Renovate/Dependabot
- Chrome: Atualização manual do container

### Backup
- Sessões salvas
- Logs históricos
- Resultados de indexação

### Troubleshooting
- Logs detalhados por componente
- Debug mode com screenshots
- Replay de falhas