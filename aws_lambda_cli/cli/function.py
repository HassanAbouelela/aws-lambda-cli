import logging
import tempfile
import typing
from pathlib import Path

import click

from aws_lambda_cli import build, utils
from aws_lambda_cli.cli.root import cli
from aws_lambda_cli.cli.utils import CLIContext, FORCE_OPTION, OPT_STR

logger = logging.getLogger(__name__)


@cli.command("function", aliases=["func"])
@click.option(
    "-u/-b", "--upload/--no-upload",
    default=True,
    help="Upload the build result to AWS. Defaults to true.",
)
@click.option("--publish", is_flag=True, default=False, help="Publish a new function version.")
@click.option("--aws-s3-bucket", default=None)
@click.option("--aws-s3-key", default=None)
@click.option(
    "-o", "--out",
    default=None,
    type=click.Path(resolve_path=True, path_type=Path),
    help="Optionally specify the name of the output zip. If this is not specified, a temporary file is used instead.",
)
@click.option("-w/-s", "--wait/--skip", default=True, help="Wait for the new code to be valid.")
@FORCE_OPTION
@click.argument("function")
@click.argument("source", type=click.Path(exists=True, resolve_path=True, path_type=Path))
@click.pass_context
def function_cli(
    ctx: CLIContext,
    function: str,
    source: Path,
    *,
    upload: bool,
    publish: bool,
    aws_s3_bucket: OPT_STR,
    aws_s3_key: OPT_STR,
    out: typing.Optional[Path],
    wait: bool,
    force: bool,
) -> None:
    """
    Build and optionally upload AWS Lambda function code.
    Alias: "func"

    Function: The AWS function name or ARN.

    Source: The source code to be uploaded. If this is a file, it is added at the root of the zip.
    If it is a directory, the content of the directory is added at the root of the zip.
    """
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
    client = ctx.obj.session.client("lambda")

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
