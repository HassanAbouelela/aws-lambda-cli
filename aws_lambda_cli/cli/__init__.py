from aws_lambda_cli.cli.configure import configure_cli
from aws_lambda_cli.cli.function import function_cli
from aws_lambda_cli.cli.root import cli

__all__ = ["cli", "function_cli", "configure_cli"]
