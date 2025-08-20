# PyInstaller hook for boto3
# This hook ensures that all AWS service modules are properly included

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all boto3 submodules
hiddenimports = collect_submodules('boto3')

# Also collect botocore submodules
hiddenimports.extend(collect_submodules('botocore'))

# Collect data files for boto3 and botocore
datas = collect_data_files('boto3')
datas.extend(collect_data_files('botocore'))

# Add specific AWS service clients that might be dynamically imported
aws_services = [
    'ec2',
    'elbv2', 
    'elb',
    'resourcegroupstaggingapi',
    'ce',  # Cost Explorer
    'pricing',
    'sts',
    'iam',
]

for service in aws_services:
    hiddenimports.extend([
        f'botocore.client.{service}',
        f'botocore.data.{service}',
    ])

# Add common boto3 resources
hiddenimports.extend([
    'boto3.resources',
    'boto3.session',
    'boto3.dynamodb',
    'boto3.s3',
])