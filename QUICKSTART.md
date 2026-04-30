# Quick Start Guide - Devin Repository Indexer

## Installation (5 minutes)

```bash
# 1. Navigate to project directory
cd devin-index-repo-script

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

## First Run (Manual Login)

```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/YOUR-ORG/settings/indexing" \
  --search-term "YOUR-SEARCH-TERM"
```

**What happens:**
1. Browser opens automatically
2. You log in manually to Devin
3. Script detects login and saves session
4. Browser switches to headless mode
5. Indexing starts automatically

## Subsequent Runs (Automatic)

```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/YOUR-ORG/settings/indexing" \
  --search-term "YOUR-SEARCH-TERM" \
  --headless
```

**What happens:**
1. Script loads saved session
2. Runs in headless mode (no browser window)
3. Indexes repositories automatically

## Common Commands

### Index repositories matching "api"
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "api"
```

### Save results to custom file
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "data" \
  --output data-repos.json
```

### Run with verbose logging
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "ml" \
  --verbose
```

### Keep browser visible (debugging)
```bash
python -m src.cli \
  --indexing-url "https://devin.ai/org/myorg/settings/indexing" \
  --search-term "test" \
  --no-headless
```

## Output Files

After running, you'll find:

- `indexing_results.json` - Detailed results in JSON format
- `indexing_results.csv` - Results in CSV format
- `indexer.log` - Detailed execution logs
- `session.json` - Saved authentication session

## Troubleshooting

### Session expired?
```bash
rm session.json
# Run the command again - you'll need to login manually
```

### No repositories found?
- Check your search term
- Verify you have access to the organization
- Try running with `--no-headless` to see what's happening

### ChromeDriver issues?
```bash
# Update Chrome browser to latest version
# Clear webdriver cache (Windows):
rmdir /s %USERPROFILE%\.wdm
# Clear webdriver cache (Linux/Mac):
rm -rf ~/.wdm
```

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [TECHNICAL_SPEC.md](TECHNICAL_SPEC.md) for implementation details
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for system architecture

## Support

- Check `indexer.log` for detailed error messages
- Run with `--verbose` flag for more information
- Review the troubleshooting section in README.md