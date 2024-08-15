import dataclasses
import json
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


@dataclasses.dataclass
class ConfigEntry:
    profile_name: OPT_STR = None
    region_name: OPT_STR = None
    aws_access_key_id: OPT_STR = None
    aws_secret_access_key: OPT_STR = None
    aws_session_token: OPT_STR = None

    def dump_instance(self) -> dict:
        # Convert to dict
        data = dataclasses.asdict(self)

        # Remove unnecessary data
        for key in list(data.keys()):
            if data[key] is None:
                data.pop(key)

        return data

    @staticmethod
    def dump_json(config: CONFIG_TYPE, indent=4) -> str:
        result = {}
        for path, entry in config.items():
            result[path.absolute().as_posix()] = entry.dump_instance()
        return json.dumps(result, indent=indent)

    @staticmethod
    def load_json(config: str) -> CONFIG_TYPE:
        try:
            data = json.loads(config)
        except json.JSONDecodeError as e:
            msg = (
                f"Failed to read the configuration file as valid JSON. Please check the file.\n{CONFIG_FILE.absolute()}"
            )
            logger.error(msg, exc_info=e)
            raise click.ClickException(msg)

        result = {}
        for item, value in data.items():
            try:
                result[Path(item).expanduser().absolute()] = ConfigEntry(**value)
            except Exception as e:
                msg = f"Failed to read configuration entry for '{item}'."
                logger.error(msg, exc_info=e)
                raise click.ClickException(msg)

        return result


def safe_read_config(
    msg: OPT_STR = "Configuration file does not exist, nothing to do.",
) -> typing.Optional[CONFIG_TYPE]:
    if not CONFIG_FILE.exists():
        if msg is not None:
            logger.info(msg)
        return None

    try:
        raw = CONFIG_FILE.read_text("utf-8")
    except Exception as e:
        logger.error("Failed to read config file.", exc_info=e)
        raise click.ClickException("Failed to read the configuration file.")

    return ConfigEntry.load_json(raw)


def get_effective_config(
    config: CONFIG_TYPE = None, path: Path = Path.cwd(), *, parents=True
) -> typing.Optional[tuple[Path, ConfigEntry]]:
    if config is None:
        config = safe_read_config(None)
        if config is None:
            return None

    path = path.expanduser().absolute()
    if path in config:
        return path, config[path]

    if not parents:
        return None

    for parent in path.parents:
        parent = parent.absolute()
        if parent in config:
            return parent, config[parent]


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
