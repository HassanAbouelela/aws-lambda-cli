import importlib.metadata
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

__NAME__ = "aws-lambda-cli"

try:
    __VERSION__ = importlib.metadata.version(__NAME__)
except importlib.metadata.PackageNotFoundError:
    __VERSION__ = "dev"
