import logging
import tempfile
import typing
from pathlib import Path

import click
from boto3.session import Session

from src import build, utils

logger = logging.getLogger(__name__)
OPT_STR = typing.Optional[str]


class ClickLogger(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        prefix = f"[{record.levelname}]: "
        level = record.levelno
        bg = None
        if level == logging.DEBUG:
            color = "bright_black"
        elif level == logging.INFO:
            prefix = ""
            color = "bright_green"
        elif level == logging.WARNING:
            color = "yellow"
        elif level == logging.ERROR:
            color = "red"
        else:
            color = "white"
            bg = "red"

        click.secho(prefix + self.format(record), fg=color, bg=bg)


@click.command("lambda")
@click.option(
    "-u/-b", "--upload/--no-upload",
    default=True,
    help="Upload the build result to AWS. Defaults to true.",
)
@click.option("--publish", is_flag=True, default=False, help="Publish a new function version.")
@click.option("--aws_s3_bucket", default=None)
@click.option("--aws_s3_key", default=None)
@click.option(
    "-o", "--out",
    default=None,
    type=click.Path(resolve_path=True, path_type=Path),
    help="Optionally specify the name of the output zip. If this is not specified, a temporary file is used instead.",
)
@click.option("-w/-s", "--wait/--skip", default=True, help="Wait for the new code to be valid.")
@click.option("-p", "--profile", default="default", help="The AWS CLI profile to use if available.")
@click.option("-r", "--region", default=None, help="The AWS region to use.")
@click.option("--aws_access_key_id", default=None)
@click.option("--aws_secret_access_key", default=None)
@click.option("--aws_session_token", default=None)
@click.option("-f", "--force", is_flag=True, default=False, help="Bypass confirmation and safety prompts.")
@click.option("-q", "--quiet", count=True, default=0, help="Only print warnings and errors.")
@click.option("-v", "--verbose", is_flag=True, default=False, help="Increase output information.")
@click.help_option("-h", "--help")
@click.argument("function")
@click.argument("source", type=click.Path(exists=True, resolve_path=True, path_type=Path))
def cli(
    function: str,
    source: Path,
    *,
    upload: bool,
    publish: bool,
    aws_s3_bucket: OPT_STR,
    aws_s3_key: OPT_STR,
    out: typing.Optional[Path],
    wait: bool,
    profile: str,
    region: OPT_STR,
    aws_access_key_id: OPT_STR,
    aws_secret_access_key: OPT_STR,
    aws_session_token: OPT_STR,
    force: bool,
    quiet: int,
    verbose: bool,
) -> None:
    """
    Build and optionally upload AWS Lambda function code.

    Function: The AWS function name or ARN.

    Source: The source code to be uploaded. If this is a file, it is added at the root of the zip.
    If it is a directory, the content of the directory is added at the root of the zip.
    """
    logger.parent.addHandler(ClickLogger())
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet > 0:
        level = logging.WARNING if quiet == 1 else logging.ERROR

    logger.parent.setLevel(level)
    logger.debug(f"Set log level to {logging.getLevelName(logger.getEffectiveLevel())}")

    # Input sanity checks
    if not upload and out is None:
        raise click.UsageError("When uploading is not enabled, you must specify an output file (--out).")

    if out is not None and out.is_file():
        if not force:
            click.confirm("The output file already exists, overwrite?", default=False, abort=True)
        logger.warning(f"Overwriting file: {out.absolute().as_posix()}")

    # Generate a temporary directory if necessary
    if out is None:
        tmp_dir = tempfile.TemporaryDirectory()
        out = Path(tmp_dir.name)

    # Build the user's code
    result = build.build_function(source, out)
    if not upload:
        logger.info(f"Done! You can find your zip-file at: {result.absolute().as_posix()}")
        return

    # Proceed with upload
    logger.info(f"Built zip: {result.absolute().as_posix()}")

    # Validate the connection
    client = Session(
        profile_name=profile,
        region_name=region,
        aws_session_token=aws_session_token,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
    ).client("lambda")

    # Validate the function
    try:
        arn = utils.validate_function(function, client)
    except utils.ResourceNotFoundException as e:
        raise click.ClickException(*e.args)

    logger.debug(f"Found function: {arn}")

    # Upload the new function
    utils.upload_function(arn, result.read_bytes(), client, publish=publish, s3_bucket=aws_s3_bucket, s3_key=aws_s3_key)
    if not wait:
        logger.info("Code upload done. Make sure to wait till the code is valid before using it.")
        return

    # Wait for it to be valid
    logger.info("Code uploaded, waiting till it's valid.")
    status = utils.wait_release(function, client)
    if status != "Successful":
        raise click.ClickException(f"Function update did not succeed with status: {status}")

    logger.info("All done!")


if __name__ == "__main__":
    cli.main()
