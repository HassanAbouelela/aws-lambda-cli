import logging

import botocore.exceptions
import click
from boto3.session import Session

from aws_lambda_cli import __NAME__, __VERSION__
from aws_lambda_cli.cli.utils import CLIContext, ClickLogger, FORCE_OPTION, Group, OPT_STR, get_effective_config

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
    ctx.obj.force = force

    # Set session
    if any((profile, region, aws_session_token, aws_access_key_id, aws_secret_access_key)):
        # Use explicit configuration settings
        logger.info("Using explicit authentication credentials.")
        ctx.obj.session = Session(
            profile_name=profile,
            region_name=region,
            aws_session_token=aws_session_token,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
    else:
        result = get_effective_config()
        if result:
            # Use a saved configuration
            logger.info(f"Using saved configuration from {result[0]}")
            try:
                ctx.obj.session = Session(**result[1].dump_instance())
            except botocore.exceptions.BotoCoreError as e:
                logger.debug(f"Failed to read the configuration for {result[0]}.", exc_info=e)
                if force:
                    logger.warning("Error reading saved configuration, using defaults.")
                else:
                    cont = click.confirm(
                        f"Failed to load configuration from: {result[0]}, continue?", default=False
                    )
                    if cont:
                        logger.warning("Using a default session. See debug logs for more detailed errors.")
                    else:
                        show = click.confirm("Do you want to see the full error message?", default=True)
                        if show:
                            raise e
                        raise click.Abort()
        else:
            # No configuration selected, just use defaults
            logger.debug("No saved configuration or explicit settings, using a default session.")

        if not hasattr(ctx.obj, "session"):
            ctx.obj.session = Session()


if __name__ == "__main__":
    cli.main()
