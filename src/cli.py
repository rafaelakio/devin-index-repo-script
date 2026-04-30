import click
from dotenv import load_dotenv
import os

load_dotenv()


@click.command()
@click.option(
    "--indexing-url",
    envvar="DEVIN_INDEXING_URL",
    required=True,
    help="URL da página de indexing do Devin (ex: https://devin.ai/org/MY_ORG/settings/indexing)",
)
@click.option(
    "--search-term",
    envvar="DEFAULT_SEARCH_TERM",
    default="",
    show_default=True,
    help="Termo para filtrar repositórios na busca",
)
@click.option(
    "--output",
    "output_file",
    envvar="OUTPUT_FILE_PATH",
    default="./indexing_results.json",
    show_default=True,
    help="Caminho do arquivo JSON de saída",
)
@click.option(
    "--session-file",
    envvar="SESSION_FILE_PATH",
    default="./session.json",
    show_default=True,
    help="Arquivo para persistir cookies de sessão",
)
@click.option(
    "--headless/--no-headless",
    envvar="HEADLESS_MODE",
    default=False,
    show_default=True,
    help="Usar modo headless após autenticação",
)
@click.option(
    "--max-retries",
    envvar="MAX_RETRIES",
    default=3,
    show_default=True,
    type=int,
    help="Máximo de tentativas por operação",
)
@click.option(
    "--rate-limit",
    envvar="RATE_LIMIT_DELAY",
    default=1.0,
    show_default=True,
    type=float,
    help="Delay entre operações (segundos)",
)
@click.option(
    "--login-timeout",
    default=300,
    show_default=True,
    type=int,
    help="Tempo máximo para login manual (segundos)",
)
@click.option("--verbose", is_flag=True, default=False, help="Logs detalhados")
def cli(**kwargs):
    """Indexa repositórios do Devin usando Microsoft Edge."""
    from src.main import run
    run(**kwargs)


if __name__ == "__main__":
    cli()
