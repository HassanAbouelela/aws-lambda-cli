import logging

import botocore.exceptions
import click
from boto3.session import Session

from aws_lambda_cli import __NAME__, __VERSION__
from aws_lambda_cli.cli.utils import CLIContext, ClickLogger, FORCE_OPTION, Group, OPT_STR

logger = logging.getLogger(__name__)

settings = {
    "help_option_names": ["-h", "--help"]
}


@click.group(name="lambda", cls=Group, context_settings=settings)
@click.option("-p", "--profile", default=None, help="The AWS CLI profile to use if available.")
@click.option("-r", "--region", default=None, help="The AWS region to use.")
@click.option("--aws-access-key-id", default=None, help="Use an explicit API key.")
@click.option("--aws-secret-access-key", default=None, help="Use an explicit API key.")
@click.option("--aws-session-token", default=None, help="Use a session token.")
@click.option(
    "-q", "--quiet",
    count=True,
    default=0,
    help="Only print warnings and errors. Pass twice to silence warnings."
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Increase output information.")
@FORCE_OPTION
@click.version_option(__VERSION__, "-V", "--version", package_name=__NAME__)
@click.pass_context
def cli(
    ctx: CLIContext,
    *,
    profile: OPT_STR,
    region: OPT_STR,
    aws_access_key_id: OPT_STR,
    aws_secret_access_key: OPT_STR,
    aws_session_token: OPT_STR,
    quiet: int,
    verbose: bool,
    force: bool,
):
    """A simple CLI for building and publishing AWS Lambda functions."""
    # Configure logging
    logger.parent.addHandler(ClickLogger())
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet > 0:
        level = logging.WARNING if quiet == 1 else logging.ERROR

    logger.parent.setLevel(level)
    logger.debug(f"Set log level to {logging.getLevelName(logger.getEffectiveLevel())}")

    ctx.ensure_object(CLIContext.ContextObject)
    ctx.obj.session = Session(
        profile_name=profile,
        region_name=region,
        aws_session_token=aws_session_token,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    )
    ctx.obj.force = force


if __name__ == "__main__":
    cli.main()
