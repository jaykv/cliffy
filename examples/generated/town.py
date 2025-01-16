## Generated town on 2025-01-16 04:52:17.516271
import typer
import subprocess
from typing import Optional, Any
import re
import time



CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
cli = typer.Typer(context_settings=CONTEXT_SETTINGS)
__version__ = '0.1.1'
__cli_name__ = 'town'


def version_callback(value: bool):
    if value:
        print(f"{__cli_name__}, {__version__}")
        raise typer.Exit()

def aliases_callback(value: bool):
    if value:
        print("""
Command          Aliases
--------         --------
home.build       bu
""")
        raise typer.Exit()

@cli.callback()
def main(
    aliases: Optional[bool] = typer.Option(None, '--aliases', callback=aliases_callback, is_eager=True),
    version: Optional[bool] = typer.Option(None, '--version', callback=version_callback, is_eager=True)
):
    pass

def format_money(money: float):
    return "${:.2f}".format(money)


land_app = typer.Typer()
cli.add_typer(land_app, name="land", help="Manage land")

def land_build(name: str = typer.Argument(..., help="Name"), address: str = typer.Argument(...), value: int = typer.Option(100, "--value", "-v")):
    """Build land"""
    print(f"building land {name}")


land_app.command("build", help="",)(land_build)

def land_sell(name: str = typer.Argument(..., help="Name"), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Sell land"""
    print(f"selling land {name}")


land_app.command("sell", help="",)(land_sell)

def land_buy(name: str = typer.Argument(..., help="Name"), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Buy land"""
    print(f"buying land {name} for {format_money(money)}")


land_app.command("buy", help="",)(land_buy)
people_app = typer.Typer()
cli.add_typer(people_app, name="people", help="Manage people")

def people_add(fullname: str = typer.Argument(...), age: int = typer.Argument(...), home: str = typer.Option(None, "--home", "-h")):
    """Add a person to town"""
    print(f"adding person {fullname}, {age}, {home}")


people_app.command("add", help="",)(people_add)

def people_remove(fullname: str = typer.Argument(...)):
    """Remove person from town"""
    print(f"removing person {fullname}")


people_app.command("remove", help="",)(people_remove)
shops_app = typer.Typer()
cli.add_typer(shops_app, name="shops", help="Manage shops")

def shops_build(name: str = typer.Argument(..., help="Name"), land: str = typer.Argument(...), type: str = typer.Option(None, "--type", "-t")):
    """Build a shop"""
    print(f"building shop {name} ({type}) on land {land}")


shops_app.command("build", help="",)(shops_build)

def shops_sell(name: str = typer.Argument(..., help="Name"), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Sell a shop"""
    print(f"selling shop {name} for ${money}")


shops_app.command("sell", help="",)(shops_sell)

def shops_buy(name: str = typer.Argument(..., help="Name"), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Buy a shop"""
    print(f"buying shop {name} for ${money}")


shops_app.command("buy", help="",)(shops_buy)
home_app = typer.Typer()
cli.add_typer(home_app, name="home", help="Manage homes")

def home_build(address: str = typer.Argument(...), land: str = typer.Argument(None), owner: str = typer.Argument(None)):
    """Build a home"""
    print(f"building home at {address} for {owner} on land {land}")


home_app.command("build", help="",)(home_build)

home_app.command("bu", hidden=True, epilog="Alias for build")(home_build)

def home_sell(address: str = typer.Argument(...), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Sell a home"""
    print(f"selling home {address} for {format_money(money)}")


home_app.command("sell", help="",)(home_sell)

home_app.command("s", hidden=True, epilog="Alias for sell")(home_sell)

def home_buy(address: str = typer.Argument(...), money: float = typer.Option(..., help="Amount of money", min=0)):
    """Buy a home"""
    print(f"buying home {address} for {money}")


home_app.command("buy", help="",)(home_buy)

home_app.command("b", hidden=True, epilog="Alias for buy")(home_buy)

def land_list(limit: int = typer.Option(None, "--limit", "-l")):
    """Get a list of land"""
    print(f"listing land")


land_app.command("list", help="",)(land_list)

def people_list(limit: int = typer.Option(None, "--limit", "-l")):
    """Get a list of people"""
    print(f"listing people")


people_app.command("list", help="",)(people_list)

def shops_list(limit: int = typer.Option(None, "--limit", "-l")):
    """Get a list of shops"""
    print(f"listing shops")


shops_app.command("list", help="",)(shops_list)

def home_list(limit: int = typer.Option(None, "--limit", "-l")):
    """Get a list of home"""
    print(f"listing home")


home_app.command("list", help="",)(home_list)

if __name__ == "__main__":
    cli()
