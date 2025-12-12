# pyright: reportUnusedCallResult=false
from cyclopts import App

from ._serve import serve_cmd

app = App(name="docs", help="Manage internal docs", help_on_error=True)
app.command(serve_cmd)

if __name__ == "__main__":
    app()
