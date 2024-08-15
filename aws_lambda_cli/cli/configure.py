import logging
import typing
from pathlib import Path

import click

from aws_lambda_cli.cli.root import cli
from aws_lambda_cli.cli.utils import (
    CONFIG_FILE, CONFIG_TYPE, ConfigEntry, FORCE_OPTION, OPT_STR, get_effective_config, safe_read_config,
)

logger = logging.getLogger(__name__)


def get_create_file() -> CONFIG_TYPE:
    # Ensure the .aws folder exists
    try:
        CONFIG_FILE.parent.mkdir(exist_ok=True)
    except Exception:
        raise click.ClickException(
            f"Failed to create the aws folder in the user directory.\n{CONFIG_FILE.parent.absolute()}"
        )

    # Ensure the config file exists
    if not CONFIG_FILE.exists():
        logger.debug("No configuration file, creating one.")
        try:
            CONFIG_FILE.touch(700)
        except Exception as e:
            msg = f"Failed to creat the configuration file.\n{CONFIG_FILE.absolute()}"
            logger.error(msg, exc_info=e)
            raise click.ClickException(msg)
        return {}

    # Try and read the file
    try:
        content = CONFIG_FILE.read_text("utf-8")
    except Exception as e:
        msg = f"Failed to read the configuration file, possibly due to a permission error"
        logger.error(msg, exc_info=e)
        raise click.ClickException(msg)

    # Parse it
    return ConfigEntry.load_json(content)


@cli.group("config", aliases=["configure"])
def configure_cli():
    """
    Set or read the current configuration.

    Alias: 'configure'

    The configuration is saved in your user home directory at: '~/.aws/lambda-cli.json'

    When you use the CLI with a saved configuration, it will use the configuration for the current folder,
    or any parent folders, similar to git.

    I.E: if you're in a folder (that does not have a saved configuration) called '/home/project/abc',
    but you have a configuration for '/home/project', that will be used instead. If a configuration is loaded,
    a message is shown at the beginning of the command.
    """
    pass


@configure_cli.command("set")
@click.option("-p", "--profile", default=None, help="The AWS CLI profile to use if available.")
@click.option("-r", "--region", default=None, help="The AWS region to use.")
@click.option("--aws-access-key-id", default=None, help="Use an explicit API key.")
@click.option("--aws-secret-access-key", default=None, help="Use an explicit API key.")
@click.option("--aws-session-token", default=None, help="Use a session token.")
@FORCE_OPTION
def set_config_cli(*, force: bool, profile: OPT_STR, region: OPT_STR, **kwargs: typing.Any):
    """Configure application defaults."""
    logger.debug(f"Modifying config for: {Path.cwd().absolute()}")
    new = ConfigEntry(profile_name=profile, region_name=region, **kwargs)
    config = get_create_file()

    new_path = Path.cwd()
    if new_path in config and not force:
        click.confirm(f"An entry already exists for {new_path}, overwrite?", default=False, abort=True)
    logger.debug(f"Updating config for: {new_path}")

    config[new_path] = new
    CONFIG_FILE.write_text(ConfigEntry.dump_json(config), "utf-8")
    logger.info(f"Successfully updated configuration for {new_path.absolute()}")


@configure_cli.command("get")
@click.option(
    "-p", "--path",
    default=Path.cwd(),
    type=click.Path(path_type=Path),
    help="Get the effective configuration for a specific working directory."
)
def get_config_cli(path: Path):
    """Get the effective configuration for the current context."""
    config = safe_read_config("Configuration file does not exist, no config will be applied.")
    if config is None:
        return

    result = get_effective_config(config, path)
    if result:
        actual_path, entry = result
        logger.info(f"Found entry from {actual_path.absolute()}:")
        for item, value in entry.dump_instance().items():
            logger.info(f"\t{item} = {value}")
    else:
        logger.info("No default configuration found.")


@configure_cli.command("delete")
@click.option(
    "-p", "--path",
    default=Path.cwd(),
    type=click.Path(path_type=Path),
    help="Delete the configuration for the specified path."
)
@FORCE_OPTION
def delete_config_cli(*, path: Path, force: bool):
    """Delete the saved configuration for the current directory."""
    config = safe_read_config()
    if config is None:
        return

    result = get_effective_config(config, path, parents=False)
    if result:
        if not force:
            click.confirm(f"Found config from {result[0]}, delete?", default=False, abort=True)
        config.pop(result[0])
        CONFIG_FILE.write_text(ConfigEntry.dump_json(config), "utf-8")
        logger.info("Configuration deleted")
    else:
        logger.info("No configuration found for the specified path.")


@configure_cli.command("list")
def list_config_cli():
    """Print out all available configurations."""
    config = safe_read_config()
    if config is None:
        return

    for path, entry in config.items():
        logger.info(f"[{path.absolute()}]:")
        for item, value in entry.dump_instance().items():
            logger.info(f"\t{item} = {value}")
