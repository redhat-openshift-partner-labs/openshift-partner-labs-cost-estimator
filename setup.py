#!/usr/bin/env python3
"""
Setup configuration for OpenShift Partner Labs Cost Estimator
"""

from setuptools import setup, find_packages
import os
import sys

# Read version from git tags or use fallback
def get_version():
    """Get version from git tags or use fallback version"""
    try:
        import subprocess
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'], 
                              capture_output=True, text=True, check=True)
        return result.stdout.strip().lstrip('v')
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "1.0.0"  # Fallback version

# Read README for long description
def get_long_description():
    """Read README.md for long description"""
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Multi-cloud cost estimation tool for OpenShift partner labs"

# Read requirements from requirements.txt
def get_requirements():
    """Parse requirements.txt and return list of dependencies"""
    requirements_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    requirements = []
    
    if os.path.exists(requirements_path):
        with open(requirements_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    requirements.append(line)
    
    return requirements

setup(
    name="openshift-cost-estimator",
    version=get_version(),
    
    # Package information
    description="Multi-cloud cost estimation tool for OpenShift partner labs",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    
    # Author information
    author="OpenShift Partner Labs Team",
    author_email="partner-labs@redhat.com",
    
    # URLs
    url="https://github.com/your-org/openshift-partner-labs-cost-estimator",
    project_urls={
        "Bug Reports": "https://github.com/your-org/openshift-partner-labs-cost-estimator/issues",
        "Source": "https://github.com/your-org/openshift-partner-labs-cost-estimator",
        "Documentation": "https://github.com/your-org/openshift-partner-labs-cost-estimator/blob/main/README.md",
    },
    
    # Package discovery
    packages=find_packages(include=['aws', 'aws.*', 'gcp', 'gcp.*', 'ibm', 'ibm.*']),
    package_data={
        'aws': ['services/*.py', 'cost/*.py', 'utils/*.py'],
        'aws.services': ['*.py'],
        'aws.cost': ['*.py'],
        'aws.utils': ['*.py'],
    },
    include_package_data=True,
    
    # Dependencies
    install_requires=get_requirements(),
    
    # Python version requirement
    python_requires=">=3.8",
    
    # Entry points for CLI
    entry_points={
        'console_scripts': [
            'openshift-cost-estimator=aws.main:main',
            'oce-aws=aws.main:main',
        ],
    },
    
    # Classification
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    
    # Keywords for discovery
    keywords="openshift kubernetes aws gcp ibm cloud cost estimation partner labs",
    
    # Extra dependencies for development
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'flake8>=5.0.0',
            'mypy>=1.0.0',
        ],
        'build': [
            'pyinstaller>=5.10.0',
            'wheel>=0.37.0',
            'build>=0.8.0',
        ],
    },
    
    # License
    license="Apache License 2.0",
    
    # Zip safety
    zip_safe=False,
)