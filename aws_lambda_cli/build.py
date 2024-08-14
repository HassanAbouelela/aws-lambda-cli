import logging
import shutil
import uuid
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)


def build_function(src: Path, dest: Path) -> Path:
    """
    Create a zip-file containing a lambda function's source code.

    Args:
        src: The location of the source code.
        dest: The destination to build the zip file to.
              If this exists, and is a directory, we place a randomly named zip inside.

    Returns:
        The path to the result zip file.
    """
    logger.debug(f"Building {src.absolute().as_posix()} to {dest.absolute().as_posix()}")

    if dest.is_dir():
        name = uuid.uuid4().hex
        logger.debug(f"Generated random name for build: {name}")
    else:
        name = src.name
        dest = src.parent

    logger.debug(f"Writing to {name} at {dest}")

    if src.is_dir():
        result = shutil.make_archive((dest / name).absolute().as_posix(), "zip", src)
    else:
        if not name.endswith(".zip"):
            name += ".zip"

        with zipfile.ZipFile(dest / name, "w") as file:
            file.write(src, src.relative_to(src.parent))
            result = file.filename

    result = Path(result)
    logger.debug(f"Build output written to: {result.absolute().as_posix()}")
    return result
