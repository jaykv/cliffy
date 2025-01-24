## Generated aiprompt on 2025-01-24 13:22:43.676184
import subprocess
from typing import Optional, Any
import typer
import openai
import keyring
import json
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from typing import Optional, List
from pathlib import Path
from datetime import datetime



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS, help="""Generated with Claude. Command-line interface for interacting with OpenAI's APIs.""")
__version__ = '1.0.0'
__cli_name__ = 'aiprompt'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

@cli.callback()
def main(
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

config_app = typer.Typer()
chat_app = typer.Typer()
def load_api_key():
    key = keyring.get_password("aiprompt", "openai_api_key")
    if not key:
        raise typer.BadParameter("API key not found. Please set it using 'aiprompt config set-key'")
    return key

def format_chat_response(response):
    console = Console()
    content = response.choices[0].message.content
    console.print(Markdown(content))
    
def format_completion_response(response):
    console = Console()
    content = response.choices[0].text
    console.print(content)



def chat(verbose: bool = typer.Option(False, help="Enable verbose output"), prompt: str = typer.Argument(..., help="The prompt to send to the model"), model: str = typer.Option("gpt-3.5-turbo", help="GPT model to use"), temperature: float = typer.Option(0.7, help="Sampling temperature (0-2)"), max_tokens: int = typer.Option(1000, help="Maximum tokens in response")):
    client = openai.OpenAI(api_key=load_api_key())
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens
    )
    format_chat_response(response)


cli.command("chat", help="Start a chat completion with GPT models",)(chat)

def complete(verbose: bool = typer.Option(False, help="Enable verbose output"), prompt: str = typer.Argument(..., help="The prompt to complete"), model: str = typer.Option("gpt-3.5-turbo-instruct", help="Model to use"), temperature: float = typer.Option(0.7, help="Sampling temperature (0-2)"), max_tokens: int = typer.Option(500, help="Maximum tokens in response")):
    client = openai.OpenAI(api_key=load_api_key())
    response = client.completions.create(
        model=model,
        prompt=prompt,
        temperature=temperature,
        max_tokens=max_tokens
    )
    format_completion_response(response)


cli.command("complete", help="Generate text completions",)(complete)

def models(verbose: bool = typer.Option(False, help="Enable verbose output"), type: str = typer.Option("", help="Filter models by type (chat, completion, embedding, etc.)")):
    console = Console()
    client = openai.OpenAI(api_key=load_api_key())
    models = client.models.list()
    
    table = Table(title="Available OpenAI Models")
    table.add_column("ID", style="cyan")
    table.add_column("Created", style="green")
    table.add_column("Owner", style="blue")
    
    for model in sorted(models.data, key=lambda x: x.created):
        if type and type.lower() not in model.id.lower():
            continue
        created_date = datetime.fromtimestamp(model.created).strftime('%Y-%m-%d')
        table.add_row(model.id, created_date, model.owned_by)
    
    console.print(table)


cli.command("models", help="List available OpenAI models",)(models)
cli.add_typer(config_app, name="config", help="")

def config_set_key(verbose: bool = typer.Option(False, help="Enable verbose output"), api_key: str = typer.Argument(..., help="Your OpenAI API key")):
    keyring.set_password("aiprompt", "openai_api_key", api_key)
    typer.echo("API key saved successfully!")


config_app.command("set-key", help="Set OpenAI API key",)(config_set_key)
cli.add_typer(chat_app, name="chat", help="")

def chat_stream(verbose: bool = typer.Option(False, help="Enable verbose output"), prompt: str = typer.Argument(..., help="The prompt to send to the model"), model: str = typer.Option("gpt-3.5-turbo", help="GPT model to use"), temperature: float = typer.Option(0.7, help="Sampling temperature (0-2)")):
    console = Console()
    client = openai.OpenAI(api_key=load_api_key())
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        stream=True
    )
    for chunk in stream:
        if chunk.choices[0].delta.content:
            console.print(chunk.choices[0].delta.content, end="")
    console.print()


chat_app.command("stream", help="Start a streaming chat completion",)(chat_stream)

def chat_file(verbose: bool = typer.Option(False, help="Enable verbose output"), file: Path = typer.Argument(..., help="Path to the input file"), model: str = typer.Option("gpt-3.5-turbo", help="GPT model to use"), system_prompt: str = typer.Option("", help="Optional system prompt")):
    client = openai.OpenAI(api_key=load_api_key())
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
        
    with open(file, 'r') as f:
        content = f.read()
        messages.append({"role": "user", "content": content})
    
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    format_chat_response(response)


chat_app.command("file", help="Send a file's content as a chat prompt",)(chat_file)

if __name__ == "__main__":
    cli()
