import logging
import typing
from pathlib import Path

import click
from boto3.session import Session
from click import Command, Context

logger = logging.getLogger(__name__)

OPT_STR = typing.Optional[str]

CONFIG_FILE = Path.home() / ".aws" / "lambda-cli.json"
CONFIG_TYPE = dict[Path, "ConfigEntry"]


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

    def group(
        self,
        *args: typing.Any,
        aliases: typing.Optional[list[str]] = None,
        **kwargs: typing.Any
    ) -> typing.Union[typing.Callable[[typing.Callable[..., typing.Any]], "Group"], "Group"]:
        self.pending_aliases = aliases
        return super().group(*args, **kwargs)


class CLIContext(Context):
    class ContextObject:
        session: Session
        force: bool = False

    obj: ContextObject


def __force(ctx: CLIContext, _param, value: typing.Optional[bool]) -> bool:
    ctx.ensure_object(CLIContext.ContextObject)

    if value is not None:
        ctx.obj.force = value
        return value
    else:
        return ctx.obj.force


FORCE_OPTION = click.option(
    "-f", "--force",
    is_flag=True,
    default=None,
    callback=__force,
    help="Bypass confirmation and safety prompts.",
)
