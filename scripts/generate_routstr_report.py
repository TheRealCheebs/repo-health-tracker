# scripts/generate_routestr_report.py

import os
import click
from dotenv import load_dotenv
from rich.console import Console
from jinja2 import Environment, FileSystemLoader
import json

# Use the standard OpenAI library
from openai import OpenAI

load_dotenv()
console = Console()


@click.command()
@click.option(
    "--data-file",
    default="summary_report.json",
    help="Path to the JSON report file.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--template-file",
    default="report_prompt.md",
    help="Path to the Jinja2 template file.",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--output",
    default="final_report.md",
    help="Path for the generated Markdown file.",
    type=click.Path(dir_okay=False),
)
@click.option(
    "--model",
    default="gpt-4o",
    help="The LLM model to use (e.g., 'gpt-4o', 'gemini-pro').",
)
def main(data_file: str, template_file: str, output: str, model: str):
    """Generates a Markdown report using the OpenAI SDK pointed at the Routstr proxy."""
    try:
        # 1. Load the template and the data
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 2. Render the template with the data using Jinja2
        env = Environment(loader=FileSystemLoader("."))
        template = env.from_string(template_content)
        rendered_prompt = template.render(data=data)

        # 3. Configure the OpenAI client to use the Routstr proxy
        api_key = os.getenv("ROUTSTR_API_KEY")
        if not api_key:
            console.print(
                "[red]ROUTSTR_API_KEY not found in environment variables.[/red]"
            )
            return

        # This is the key part: point the standard OpenAI client at Routstr's endpoint
        client = OpenAI(api_key=api_key, base_url="https://api.routstr.com/v1")

        console.print(f"[blue]Generating report with routstr/{model}...[/blue]")

        # 4. Make the API call using the standard OpenAI SDK method
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert software engineering analyst.",
                },
                {"role": "user", "content": rendered_prompt},
            ],
        )

        markdown_report = response.choices[0].message.content

        # 5. Save the final Markdown report
        with open(output, "w", encoding="utf-8") as f:
            f.write(markdown_report)

        console.print(f"[green]Successfully generated report at {output}[/green]")

    except Exception as e:
        console.print(f"[red]An error occurred: {e}[/red]")


if __name__ == "__main__":
    main()
