# Devin Repository Indexer

Automated tool for indexing repositories on the Devin platform using web scraping with Selenium.

## Features

- 🔐 **Session Management**: Login once, reuse session for future runs
- 🔍 **Smart Search**: Filter repositories by search term
- 🌿 **Branch Filtering**: Automatically indexes `main` and `develop` branches
- 🔄 **Retry Logic**: Exponential backoff for failed operations
- 📊 **Detailed Reports**: JSON and CSV output with comprehensive statistics
- 🎯 **Headless Mode**: Run in background after initial authentication
- 📝 **Comprehensive Logging**: Detailed logs for debugging and monitoring

## Prerequisites

- Python 3.8 or higher
- Google Chrome browser
- ChromeDriver (automatically managed by webdriver-manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd devin-index-repo-script
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the example environment file:
```bash
cp .env.example .env
```

5. Edit `.env` with your configuration (optional).

## Usage

### Basic Usage

```bash
python -m src.cli --indexing-url "https://devin.ai/org/your-org/settings/indexing" --search-term "your-search-term"
```

### First Run (Manual Login Required)

On the first run, the browser will open for you to log in manually:

```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/your-org/settings/indexing" \
  --search-term "poc"
```

1. Browser window will open
2. Log in to Devin manually
3. Wait for the script to detect successful login
4. Session will be saved automatically
5. Browser switches to headless mode
6. Indexing begins

### Subsequent Runs (Using Saved Session)

After the first run, the session is saved and reused:

```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/your-org/settings/indexing" \
  --search-term "data-pipeline" \
  --headless
```

### Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--indexing-url` | Yes | - | URL of the Devin indexing page |
| `--search-term` | Yes | - | Search term to filter repositories |
| `--output` | No | `indexing_results.json` | Path to output JSON file |
| `--session-file` | No | `session.json` | Path to session file |
| `--headless/--no-headless` | No | `True` | Run in headless mode after auth |
| `--max-retries` | No | `3` | Maximum retry attempts |
| `--rate-limit` | No | `1.0` | Delay between operations (seconds) |
| `--log-level` | No | `INFO` | Logging level |
| `--log-file` | No | `indexer.log` | Path to log file |
| `--verbose` | No | `False` | Enable verbose output (DEBUG level) |

### Examples

**Index all repositories matching "machine-learning":**
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "machine-learning" \
  --output ml-repos.json
```

**Run with custom retry and rate limit settings:**
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "api" \
  --max-retries 5 \
  --rate-limit 2.0 \
  --verbose
```

**Run in non-headless mode (keep browser visible):**
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "frontend" \
  --no-headless
```

## Output Format

### JSON Output

The script generates a JSON file with the following structure:

```json
{
  "metadata": {
    "timestamp": "2026-04-30T01:30:00Z",
    "indexing_url": "https://devin.ai/org/myorg/settings/indexing",
    "search_term": "poc",
    "total_repositories_found": 15,
    "total_repositories_processed": 15,
    "total_branches_indexed": 28,
    "successful_indexations": 26,
    "failed_indexations": 2,
    "already_indexed": 5,
    "execution_time_seconds": 245.3
  },
  "results": {
    "successful": [
      {
        "repository": "org/repo-name",
        "branch": "main",
        "status": "success",
        "message": "Branch indexed successfully",
        "timestamp": "2026-04-30T01:31:15Z"
      }
    ],
    "failed": [
      {
        "repository": "org/failed-repo",
        "branch": "main",
        "status": "error",
        "error": "Timeout waiting for indexing confirmation",
        "timestamp": "2026-04-30T01:35:00Z"
      }
    ],
    "already_indexed": [
      {
        "repository": "org/existing-repo",
        "branch": "develop",
        "status": "already_indexed",
        "message": "Branch is already indexed",
        "timestamp": "2026-04-30T01:32:00Z"
      }
    ],
    "skipped": [
      {
        "repository": "org/no-branches-repo",
        "reason": "No valid branches found"
      }
    ]
  }
}
```

### CSV Output

A CSV file is also generated with the following columns:
- `repository`: Repository name
- `branch`: Branch name
- `status`: Status (success, error, already_indexed)
- `message`: Success message or error description
- `timestamp`: Operation timestamp

## Project Structure

```
devin-index-repo-script/
├── src/
│   ├── __init__.py
│   ├── main.py                 # Main entry point
│   ├── cli.py                  # CLI argument parser
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── selenium_manager.py # Selenium WebDriver management
│   │   └── session_handler.py  # Cookie/session persistence
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── search.py           # Repository search logic
│   │   └── extractor.py        # Data extraction from pages
│   ├── indexer/
│   │   ├── __init__.py
│   │   ├── api_client.py       # Indexing operations
│   │   └── retry_handler.py    # Retry logic and rate limiting
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Logging configuration
│       └── output.py           # JSON/CSV output writer
├── tests/
│   └── __init__.py
├── config/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```env
# Devin Indexing Configuration
DEVIN_INDEXING_URL=https://devin.ai/org/your-org/settings/indexing
DEFAULT_SEARCH_TERM=
SESSION_FILE_PATH=./session.json
OUTPUT_FILE_PATH=./indexing_results.json

# Retry and Rate Limiting
MAX_RETRIES=3
RETRY_DELAY=2
RATE_LIMIT_DELAY=1

# Browser Configuration
HEADLESS_MODE=true
BROWSER_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FILE=indexer.log
```

## Troubleshooting

### Session Expired

If you see "Session appears to be invalid", delete the session file and run again:

```bash
rm session.json
python -m src.cli --indexing-url "..." --search-term "..."
```

### ChromeDriver Issues

The script uses `webdriver-manager` to automatically download and manage ChromeDriver. If you encounter issues:

1. Ensure Chrome browser is installed
2. Update Chrome to the latest version
3. Clear the webdriver cache: `rm -rf ~/.wdm`

### No Repositories Found

If no repositories are found:

1. Verify the search term is correct
2. Check that you have access to repositories in the organization
3. Try running without `--headless` to see the browser
4. Check the log file for detailed error messages

### Rate Limiting

If you encounter rate limiting:

1. Increase the `--rate-limit` value (e.g., `--rate-limit 2.0`)
2. Reduce the number of repositories being processed
3. Wait a few minutes before retrying

## Logging

Logs are written to both console and file:

- **Console**: INFO level and above (colored output)
- **File**: DEBUG level and above (detailed logs)

View logs in real-time:
```bash
tail -f indexer.log
```

## Security Considerations

1. **Session Files**: Contains authentication cookies - keep secure
2. **Credentials**: Never commit `.env` or `session.json` to version control
3. **Logs**: May contain sensitive information - review before sharing
4. **HTTPS**: Always use HTTPS URLs for the indexing page

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Check the troubleshooting section
- Review log files for detailed error messages
- Open an issue on GitHub

## Changelog

### Version 1.0.0 (2026-04-30)
- Initial release
- Session management with cookie persistence
- Repository search and filtering
- Automatic branch indexing (main/develop)
- Retry logic with exponential backoff
- JSON and CSV output formats
- Comprehensive logging