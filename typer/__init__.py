class Exit(SystemExit):
    def __init__(self, code=0):
        super().__init__(code)

class Option:
    def __init__(self, *args, **kwargs):
        pass

class Typer:
    def __init__(self, *args, **kwargs):
        pass
    def command(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def __call__(self, *args, **kwargs):
        pass

# For testing CLI definitions
from .testing import CliRunner 
