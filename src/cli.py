"""
Command-line interface for the Devin Repository Indexer.
"""
import click
import os
from pathlib import Path
from typing import Optional


@click.command()
@click.option(
    '--indexing-url',
    required=True,
    help='URL of the Devin indexing page (e.g., https://devin.ai/org/your-org/settings/indexing)'
)
@click.option(
    '--search-term',
    required=True,
    help='Search term to filter repositories'
)
@click.option(
    '--output',
    default='indexing_results.json',
    help='Path to output JSON file (default: indexing_results.json)'
)
@click.option(
    '--session-file',
    default='session.json',
    help='Path to session file for storing cookies (default: session.json)'
)
@click.option(
    '--headless/--no-headless',
    default=True,
    help='Run browser in headless mode after authentication (default: True)'
)
@click.option(
    '--max-retries',
    default=3,
    type=int,
    help='Maximum number of retry attempts for failed operations (default: 3)'
)
@click.option(
    '--rate-limit',
    default=1.0,
    type=float,
    help='Delay in seconds between operations (default: 1.0)'
)
@click.option(
    '--log-level',
    default='INFO',
    type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], case_sensitive=False),
    help='Logging level (default: INFO)'
)
@click.option(
    '--log-file',
    default='indexer.log',
    help='Path to log file (default: indexer.log)'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Enable verbose output (sets log level to DEBUG)'
)
def main(
    indexing_url: str,
    search_term: str,
    output: str,
    session_file: str,
    headless: bool,
    max_retries: int,
    rate_limit: float,
    log_level: str,
    log_file: str,
    verbose: bool
):
    """
    Devin Repository Indexer - Automate repository indexing on Devin platform.
    
    This tool searches for repositories matching a search term and indexes
    their main and develop branches automatically.
    """
    from src.utils.logger import setup_logger
    from src.main import run_indexer
    
    # Override log level if verbose
    if verbose:
        log_level = 'DEBUG'
    
    # Setup logger
    logger = setup_logger(
        name="devin_indexer",
        log_level=log_level,
        log_file=log_file,
        console_output=True
    )
    
    # Validate inputs
    if not indexing_url.startswith('http'):
        logger.error("Invalid indexing URL. Must start with http:// or https://")
        raise click.BadParameter("Invalid indexing URL")
    
    if not search_term.strip():
        logger.error("Search term cannot be empty")
        raise click.BadParameter("Search term cannot be empty")
    
    # Create config dictionary
    config = {
        'indexing_url': indexing_url,
        'search_term': search_term,
        'output_file': output,
        'session_file': session_file,
        'headless': headless,
        'max_retries': max_retries,
        'rate_limit': rate_limit,
        'log_level': log_level,
        'log_file': log_file
    }
    
    logger.info("=" * 60)
    logger.info("Devin Repository Indexer")
    logger.info("=" * 60)
    logger.info(f"Indexing URL: {indexing_url}")
    logger.info(f"Search term: {search_term}")
    logger.info(f"Output file: {output}")
    logger.info(f"Headless mode: {headless}")
    logger.info("=" * 60)
    
    try:
        # Run the indexer
        run_indexer(config)
        logger.info("Indexing completed successfully!")
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}", exc_info=True)
        raise click.ClickException(str(e))


if __name__ == '__main__':
    main()

# Made with Bob
