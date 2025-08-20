# PyInstaller hook for aws module
# This hook ensures that all project AWS modules are properly included

from PyInstaller.utils.hooks import collect_submodules, collect_data_files, get_package_paths
import os

# Collect all aws submodules
hiddenimports = collect_submodules('aws')

# Collect data files from aws package
datas = collect_data_files('aws')

# Get package paths
pkg_base, pkg_dir = get_package_paths('aws')

# Add specific imports for AWS services
aws_service_modules = [
    'aws.services.base',
    'aws.services.ec2_service', 
    'aws.services.elb_service',
    'aws.services.resource_groups_service',
    'aws.services.registry',
    'aws.cost.base',
    'aws.cost.analyzer_service',
    'aws.cost.calculator_registry',
    'aws.cost.cost_aggregator',
    'aws.cost.cost_categories',
    'aws.cost.enhanced_reporter',
    'aws.cost.explorer_service',
    'aws.cost.pricing_service',
    'aws.cost.registry',
    'aws.cost.reporter_service',
    'aws.utils.discoverer',
    'aws.utils.formatter',
]

hiddenimports.extend(aws_service_modules)

# Include any JSON or configuration files
if pkg_dir and os.path.exists(pkg_dir):
    for root, dirs, files in os.walk(pkg_dir):
        for file in files:
            if file.endswith(('.json', '.yaml', '.yml', '.toml', '.ini')):
                rel_path = os.path.relpath(os.path.join(root, file), pkg_base)
                datas.append((os.path.join(root, file), os.path.dirname(rel_path)))