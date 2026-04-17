"""
Main entry point for local LLM SEO agent.
Supports demo_mode (homework scenarios) and catalog_mode (Excel processing).
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

# Setup paths
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.agent.prompts import get_demo_scenario_task
from app.agent.runner import AgentRunner
from app.agent.schemas import AgentRunResult
from app.llm.ollama_client import OllamaClient
from app.services.catalog_processor import CatalogProcessor
from app.tools.base import ToolRegistry
from app.tools.calculator import CalculatorTool
from app.tools.excel_tools import GetExcelInfoTool, ReadExcelRowTool
from app.tools.file_tools import ReadTextFileTool
from app.tools.http_fetch import HttpGetTool

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
console = Console()

SCENARIO_CHOICES = ("calculator", "file_read", "http_get")
CHAT_EXIT_COMMANDS = {"exit", "quit", "q"}


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(verbose: bool) -> None:
    """Local AI agent using qwen3.5:4b via Ollama for homework tasks and souvenir catalog SEO."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        console.print("[dim]Debug logging enabled[/dim]")


@cli.command()
def health() -> None:
    """Check if Ollama service is accessible."""
    console.print("[bold]Checking Ollama health...[/bold]")

    client = OllamaClient()
    ready, message = client.health_status()
    if ready:
        console.print("[green]✓ Ollama is running[/green]")
        console.print(f"[dim]Endpoint: {client.endpoint}[/dim]")
        console.print(f"[dim]Model: {client.model}[/dim]")
        return

    console.print("[red]✗ Ollama is not ready[/red]")
    console.print(f"[dim]{message}[/dim]")
    raise click.exceptions.Exit(code=1)


@cli.command()
@click.option(
    "--scenario",
    "-s",
    type=click.Choice(SCENARIO_CHOICES, case_sensitive=True),
    default=None,
    help="Demo scenario to run",
)
@click.option(
    "--task",
    "-t",
    default=None,
    help="Custom task to solve (overrides scenario)",
)
def demo(scenario: Optional[str], task: Optional[str]) -> None:
    """Run demo mode with homework scenarios."""
    if task:
        scenarios_to_run = [("custom", task)]
    elif scenario:
        scenarios_to_run = [(scenario, None)]
    else:
        scenarios_to_run = [(name, None) for name in SCENARIO_CHOICES]

    client = OllamaClient()
    ready, message = client.health_status()
    if not ready:
        console.print("[red]✗ Ollama not ready[/red]")
        console.print(f"[dim]{message}[/dim]")
        raise click.exceptions.Exit(code=1)

    console.print("[bold blue]Local LLM SEO Agent - Demo Mode[/bold blue]\n")

    all_passed = True
    for scenario_name, custom_task in scenarios_to_run:
        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")
        console.print(
            f"[bold]Running: {scenario_name.replace('_', ' ').title()}[/bold]"
        )
        console.print(f"[bold cyan]{'=' * 60}[/bold cyan]\n")

        task_desc = custom_task or get_demo_scenario_task(scenario_name)
        if not task_desc:
            console.print(f"[red]Unknown scenario: {scenario_name}[/red]\n")
            all_passed = False
            continue

        console.print(f"[dim]Task: {task_desc}[/dim]\n")

        success = _run_demo_scenario(client, task_desc, scenario_name)
        if success:
            console.print("[green]✓ Success[/green]\n")
        else:
            all_passed = False
            console.print("[red]Failed[/red]\n")

    console.print(f"[bold cyan]{'=' * 60}[/bold cyan]")
    if all_passed:
        console.print("[green]✓ All scenarios completed[/green]")
        return

    console.print("[red]✗ Some scenarios failed[/red]")
    raise click.exceptions.Exit(code=1)


@cli.command()
def chat() -> None:
    """Run interactive demo chat mode."""
    client = OllamaClient()
    ready, message = client.health_status()
    if not ready:
        console.print("[red]✗ Ollama not ready[/red]")
        console.print(f"[dim]{message}[/dim]")
        raise click.exceptions.Exit(code=1)

    console.print("[bold blue]Local LLM SEO Agent - Chat Mode[/bold blue]")
    console.print("[dim]Type a task and press Enter. Use exit, quit, or q to leave.[/dim]\n")

    while True:
        task = click.prompt("You", prompt_suffix=" > ", type=str).strip()
        if task.lower() in CHAT_EXIT_COMMANDS:
            console.print("[dim]Chat closed.[/dim]")
            break

        if not task:
            console.print("[yellow]Enter a task or type exit.[/yellow]\n")
            continue

        console.print()
        _run_demo_scenario(client, task, "chat")


def _run_demo_scenario(client: OllamaClient, task: str, scenario_name: str) -> bool:
    """
    Run a single demo scenario with the agent.

    Args:
        client: OllamaClient instance
        task: Task description
        scenario_name: Scenario identifier

    Returns:
        True if successful, False otherwise
    """
    logger.debug("Preparing demo scenario: %s", scenario_name)

    registry = ToolRegistry()
    registry.register(CalculatorTool())
    registry.register(ReadTextFileTool(base_path=str(BASE_DIR)))
    registry.register(HttpGetTool(max_text_length=300))
    registry.register(GetExcelInfoTool())
    registry.register(ReadExcelRowTool())

    runner = AgentRunner(
        llm_client=client,
        tool_registry=registry,
        task=task,
        mode="demo_mode",
        max_steps=5,
    )

    result = runner.run()
    _display_result(result)
    return result.success


def _display_result(result: AgentRunResult) -> None:
    """
    Display agent result in formatted table.

    Args:
        result: AgentRunResult from runner
    """
    if result.steps:
        console.print("[bold]Step History:[/bold]")
        for step in result.steps:
            console.print(
                f"  [cyan]Step {step.step_number}:[/cyan] {step.thought[:70]}"
            )
            console.print(f"    → {step.action} {str(step.args)[:60]}")
            obs = step.observation_summary or step.observation
            console.print(f"    ← {obs[:70]}\n")

    console.print("[bold]Result:[/bold]")
    if result.success:
        console.print(f"[green]✓ Task completed in {result.total_steps} steps[/green]")
        if result.final_answer:
            console.print("\n[bold]Answer:[/bold]")
            console.print(f"  {result.final_answer}")
    else:
        console.print(f"[red]✗ Failed: {result.error}[/red]")
        if result.total_steps > 0:
            console.print(
                f"[dim]Completed {result.total_steps} steps before failure[/dim]"
            )

    console.print()


@cli.command("process-catalog")
@click.option(
    "--input",
    "-i",
    "input_path",
    default="samples/products.xlsx",
    help="Path to input Excel file",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    help="Path to output Excel file (default: input_base + _result.xlsx)",
)
@click.option(
    "--sheet",
    "-s",
    "sheet_name",
    default="products",
    help="Sheet name in Excel file",
    show_default=True,
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=None,
    help="Process only first N rows (for testing)",
)
def process_catalog(
    input_path: str,
    output_path: Optional[str],
    sheet_name: str,
    limit: Optional[int],
) -> None:
    """
    Process souvenir catalog from Excel file.
    Generate SEO fields and save to new Excel file.
    """
    input_file = Path(input_path)

    if not input_file.exists():
        console.print(f"[red]✗ Input file not found: {input_path}[/red]")
        raise click.exceptions.Exit(code=1)

    if output_path is None:
        output_path = str(input_file.parent / f"{input_file.stem}_result.xlsx")

    console.print("[bold]Processing catalog[/bold]")
    console.print(f"[dim]Input: {input_path}[/dim]")
    console.print(f"[dim]Output: {output_path}[/dim]")
    console.print(f"[dim]Sheet: {sheet_name}[/dim]")
    if limit:
        console.print(f"[dim]Limit: {limit} rows[/dim]")
    console.print()

    client = OllamaClient()
    ready, message = client.health_status()
    if not ready:
        console.print("[red]✗ Ollama not ready[/red]")
        console.print(f"[dim]{message}[/dim]")
        raise click.exceptions.Exit(code=1)

    processor = CatalogProcessor(
        llm_client=client,
        input_path=input_path,
        output_path=output_path,
        sheet_name=sheet_name,
        limit=limit,
    )

    try:
        result = processor.process()
    except ValueError as e:
        console.print(f"[red]✗ Catalog processing failed: {e}[/red]")
        raise click.exceptions.Exit(code=1)

    console.print("[green]✓ Catalog processing completed[/green]")
    console.print(f"[dim]Rows processed: {result['processed_rows']}[/dim]")
    stats = result["stats"]
    console.print(
        "[dim]Stats: "
        f"success={stats.get('success', 0)}, "
        f"needs_review={stats.get('needs_review', 0)}, "
        f"skipped={stats.get('skipped', 0)}, "
        f"error={stats.get('error', 0)}[/dim]"
    )


def main() -> None:
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
