# Holy CLI

Holy is a CLI tool that makes it effortless to create, manage and connect to servers in your AWS account.

It is designed to help you quickly spin up servers for development and test purposes.

[demo video](https://github.com/holy-cli/cli/assets/501743/0ef07eb5-f816-47d1-bce1-ac8c41c689dd)

## Installation

Please make sure you have Python 3.9 or newer (`python --version`):

```
pip install holy-cli
holy --help
```

## Upgrade

```
pip install --upgrade holy-cli
```

## Configuration

To run Holy commands, you will need to have credentials to your AWS account set. Holy will look for credentials the same way as the AWS CLI or SDK does (e.g. inside [~/.aws/credentials file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) or as [environment variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)).

Ensure the IAM user for those credentials has the `AdministratorAccess` permission policy attached.

Follow our simple guide for complete setup here.

## Usage

Create a server:

```bash
# No options, create with a random name using amazon-linux OS on a micro instance (within the free tier):

holy server create

# Create with a specific name, using ubuntu on a large compute optimized instance with 30GB disk space:

holy server create my_server --os=ubuntu:22 --type=c4.large --disk-size=30

# Create with a specific Amazon machine image:

holy server create my_server --image-id="ami-00d5053dee71cee04"

# Create and open ports 22 and 3000 to the world:

holy server create my_server --ports="22,3000"

# Create and allow the server to list all S3 buckets:

holy server create my_server --actions="s3:ListAllMyBuckets"

# Create and run a script once launched:

holy server create my_server --script=/path/to/install_software.sh
```

SSH into a server:

```bash
# SSH straight in:

holy server ssh my_server

# Save SSH config for use later (VS Code, ssh command etc):

holy server ssh my_server --save

# SSH in with a particular username:

holy server ssh my_server --username=root
```

Manage inbound server ports:

```bash
# Open port 80 to the world:

holy server port my_server --action=open --port=80

# Close port 80 to the world:

holy server port my_server --action=close --port=80

# Open port 80 to a specific IP address:

holy server port my_server --action=open --port=80 --ip=1.2.3.4
```

List all servers:

```bash
holy server list

# Filter to just servers running
holy server list --running
```

Specific server actions:

```bash
# View info about a server
holy server info my_server

# Start a server
holy server start my_server

# Stop a server
holy server stop my_server

# Delete a server
holy server delete my_server
```

Remove all infrastructure created by holy:

```bash
holy teardown
```

## Development

Clone this repo and pip install:

```
pip install -e .
```