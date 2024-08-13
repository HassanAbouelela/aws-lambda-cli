import time
import typing

if typing.TYPE_CHECKING:
    from mypy_boto3_lambda.client import LambdaClient
    from mypy_boto3_lambda.type_defs import FunctionConfigurationResponseTypeDef


class ResourceNotFoundException(Exception):
    pass


def validate_function(function: str, client: "LambdaClient") -> str:
    """Validate that the given function exists in the current scope, and return the ARN."""
    try:
        return client.get_function(FunctionName=function)["Configuration"]["FunctionArn"]
    except Exception as e:
        if type(e).__name__ == "ResourceNotFoundException":
            raise ResourceNotFoundException(*e.args)
        raise e


def upload_function(
    function: str,
    code: bytes,
    client: "LambdaClient",
    *,
    publish: bool,
    s3_bucket: typing.Optional[str],
    s3_key: typing.Optional[str],
) -> "FunctionConfigurationResponseTypeDef":
    bucket = {}
    if s3_bucket:
        bucket["S3Bucket"] = s3_bucket
    if s3_key:
        bucket["S3Key"] = s3_key

    return client.update_function_code(
        FunctionName=function,
        ZipFile=code,
        Publish=publish,
        **bucket,
    )


def wait_release(function: str, client: "LambdaClient") -> typing.Literal["Successful", "Failed"]:
    while (status := client.get_function(FunctionName=function)["Configuration"]["LastUpdateStatus"]) == "InProgress":
        time.sleep(1)

    # noinspection PyTypeChecker
    return status
