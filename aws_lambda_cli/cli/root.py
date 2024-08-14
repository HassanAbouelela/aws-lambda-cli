import logging
import typing

import click
from boto3.session import Session
from click import Command, Context

from aws_lambda_cli import __NAME__, __VERSION__

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


class Group(click.Group):
    pending_aliases: typing.Optional[list[str]] = None
    aliases: dict[str, Command]

    def __init__(
        self,
        name: typing.Optional[str] = None,
        commands: typing.Optional[
            typing.Union[typing.MutableMapping[str, Command], typing.Sequence[Command]]
        ] = None,
        **attrs: typing.Any
    ) -> None:
        super().__init__(name, commands, **attrs)
        self.aliases = {}

    def add_command(self, cmd: Command, name: typing.Optional[str] = None) -> None:
        super().add_command(cmd, name)

        # Handle aliases
        aliases = self.pending_aliases or []
        self.pending_aliases = None
        for alias in aliases:
            if alias in self.aliases:
                raise TypeError(
                    f"Trying to register duplicate alias `{alias}` to {cmd.name}."
                    f" Already registered to {self.aliases[alias]}"
                )
            self.aliases[alias] = cmd

    def command(
        self,
        *args: typing.Any,
        aliases: typing.Optional[list[str]] = None,
        **kwargs: typing.Any
    ) -> typing.Union[typing.Callable[[typing.Callable[..., typing.Any]], Command], Command]:
        # Add an alias kwarg
        self.pending_aliases = aliases
        return super().command(*args, **kwargs)

    def get_command(self, ctx: Context, cmd_name: str) -> typing.Optional[Command]:
        if cmd_name in self.aliases:
            cmd_name = self.aliases[cmd_name].name

        return super().get_command(ctx, cmd_name)


class CLIContext(Context):
    class ContextObject:
        session: Session

    obj: ContextObject


settings = {
    "help_option_names": ["-h", "--help"]
}


@click.group(name="lambda", cls=Group, context_settings=settings)
@click.option("-p", "--profile", default=None, help="The AWS CLI profile to use if available.")
@click.option("-r", "--region", default=None, help="The AWS region to use.")
@click.option("--aws_access_key_id", default=None, help="Use an explicit API key.")
@click.option("--aws_secret_access_key", default=None, help="Use an explicit API key.")
@click.option("--aws_session_token", default=None, help="Use a session token.")
@click.option(
    "-q", "--quiet",
    count=True,
    default=0,
    help="Only print warnings and errors. Pass twice to silence warnings."
)
@click.option("-v", "--verbose", is_flag=True, default=False, help="Increase output information.")
@click.version_option(__VERSION__, "-V", "--version", package_name=__NAME__)
@click.pass_context
def cli(
    ctx: CLIContext,
    *,
    profile: str,
    region: OPT_STR,
    aws_access_key_id: OPT_STR,
    aws_secret_access_key: OPT_STR,
    aws_session_token: OPT_STR,
    quiet: int,
    verbose: bool
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


if __name__ == "__main__":
    cli.main()
