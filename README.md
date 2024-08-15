# AWS Lambda CLI
A simple CLI (Command Line Interface) tool to interact with [AWS Lambda functions](https://aws.amazon.com/lambda/) and Lambda layers.

### Installation
To get started, install the package:
```shell
pip install aws-lambda-cli
```

and run the help command:
```shell
lambda --help
```

See [examples](#examples) below for more details.

### License note:
This project is licensed under [GPL-3](https://www.gnu.org/licenses/gpl-3.0.en.html), whose license restrictions apply
to the distribution (propagation) and modification of this project.
Usage for personal/development purposes does not carry the same requirements (disclosure, same license, etc.),
however, warranty and liability limitations are still in effect.
See section 9 of the license for details.

### TODO
- Add layer support
- Add mypy and flake/ruff
- Unittests?
- Build actions

### Examples
<a id="examples"></a>
- Show CLI version
```shell
lambda -V
```

- Use a cli profile called `work`, and act on the `eu-central-1` region:
```shell
lambda --profile work --region eu-central-1 <subcommand>
```
Type `lambda --help` for more authentication options.

- Configure default parameters (such as authentication) to be used with all the following commands:
  This saves the configuration to file in the user's home directory. 
  See `lambda config --help` for more details.
```shell
lambda config set --profile work --region eu-central-1
lambda function Test main.py # Using profile work and region eu-central-1 
```

- Build, upload, and publish `main.py` to the function `Test`:
```shell
lambda function Test main.py --publish
```

- Use an S3 bucket called `resources`:
```shell
lambda function Test main.py --aws-s3-bucket resources
```

- Upload a project folder:
```shell
lambda function Test src
```

- Build locally, and keep the output file without uploading:
```shell
lambda function Test main.py --out out.zip --no-upload
```
