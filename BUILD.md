# Building Executable Distribution

This document provides comprehensive instructions for building a standalone executable distribution of the OpenShift Partner Labs Cost Estimator using PyInstaller.

## Quick Start

### Option 1: Python Build Script (Recommended)
```bash
# Install dependencies
pip install -r requirements.txt

# Build executable with full automation
python build_executable.py
```

### Option 2: Shell Script
```bash
# Make script executable (if needed)
chmod +x build.sh

# Build executable
./build.sh
```

### Option 3: Manual PyInstaller
```bash
# Install PyInstaller
pip install pyinstaller>=5.10.0

# Build from spec file
pyinstaller openshift-cost-estimator.spec --clean --noconfirm
```

## Build Process Overview

The build process creates a single standalone executable that includes:
- Python interpreter
- All required dependencies (boto3, botocore, termcolor)
- Project modules and packages
- AWS service configurations
- Documentation files

## Build Artifacts

After a successful build, you'll find:

```
dist/
├── openshift-cost-estimator              # Single executable file
└── openshift-cost-estimator-package/     # Distribution package
    ├── openshift-cost-estimator           # Executable
    ├── README.md                          # Project documentation
    ├── CHANGELOG.md                       # Version history
    ├── IAM_POLICY.md                      # AWS permissions guide
    └── USAGE.txt                          # Usage instructions
```

## Build Configuration

### PyInstaller Spec File
The `openshift-cost-estimator.spec` file contains the complete build configuration:

- **Entry Point**: `aws/main.py`
- **Hidden Imports**: All AWS SDK modules and project modules
- **Data Files**: Service configurations and documentation
- **Hooks**: Custom PyInstaller hooks for AWS dependencies
- **Exclusions**: Test files and development dependencies

### Build Script Options

The `build_executable.py` script supports several options:

```bash
python build_executable.py --help
```

Available options:
- `--no-clean`: Skip cleaning previous build artifacts
- `--no-test`: Skip running pre-build and post-build tests
- `--debug`: Enable PyInstaller debug mode for troubleshooting
- `--no-package`: Skip creating the distribution package
- `--project-root`: Specify custom project root directory

## Dependencies and Requirements

### Build Dependencies
- Python 3.8 or higher
- PyInstaller 5.10.0 or higher
- All runtime dependencies (boto3, botocore, termcolor)

### System Requirements
- **Linux**: glibc 2.17 or higher (CentOS 7+, Ubuntu 16.04+)
- **macOS**: macOS 10.14 or higher
- **Windows**: Windows 10 or higher

### AWS SDK Dependencies
The build process automatically handles:
- Boto3 and botocore modules
- AWS service client libraries
- AWS data files and configurations
- Dynamic imports for AWS services

## Build Size Optimization

The executable is optimized for size using:
- **UPX Compression**: Reduces file size by ~30-50%
- **Exclude Test Files**: Removes unittest and test modules
- **Hidden Imports**: Only includes required AWS service modules
- **Single File**: Everything bundled into one executable

Typical executable size: **25-40 MB** (compressed)

## Troubleshooting Build Issues

### Common Issues and Solutions

#### 1. Import Errors During Build
```
ModuleNotFoundError: No module named 'botocore.client'
```

**Solution**: The spec file includes comprehensive hidden imports. If you encounter missing modules:
1. Add the module to `hiddenimports` in the spec file
2. Create a custom hook in the `hooks/` directory
3. Use `--debug` mode to identify missing imports

#### 2. AWS Service Not Found
```
UnknownServiceError: Unknown service
```

**Solution**: Add the service to the hidden imports:
```python
# In openshift-cost-estimator.spec
hiddenimports=[
    # ... existing imports ...
    'botocore.client.ServiceName',
]
```

#### 3. Build Fails with Permission Errors
**Solution**: 
- Ensure write permissions to project directory
- Run with appropriate user permissions
- Check antivirus software interference

#### 4. Executable Crashes on Startup
**Solution**:
1. Build with debug mode: `python build_executable.py --debug`
2. Check for missing data files in the spec file
3. Verify all project modules are included

#### 5. Large Executable Size
**Solution**:
- Ensure UPX is installed and enabled in spec file
- Review and remove unnecessary hidden imports
- Exclude additional test/development modules

### Debug Mode
Enable debug mode for detailed troubleshooting:

```bash
# Python script with debug
python build_executable.py --debug

# Direct PyInstaller with debug
pyinstaller openshift-cost-estimator.spec --debug=all
```

### Log Analysis
Build logs are captured during the process. Check for:
- Missing modules in the analysis phase
- File permissions issues
- Import warnings and errors

## Cross-Platform Building

### Building for Different Platforms
PyInstaller creates executables for the platform it runs on:

- **Linux executable**: Build on Linux
- **macOS executable**: Build on macOS  
- **Windows executable**: Build on Windows

### Docker Build (Linux)
For consistent Linux builds:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN python build_executable.py

# Extract executable
RUN cp dist/openshift-cost-estimator /output/
```

## Distribution and Deployment

### Single Executable Distribution
The simplest distribution method:
1. Copy `dist/openshift-cost-estimator` to target system
2. Ensure execute permissions: `chmod +x openshift-cost-estimator`
3. Run: `./openshift-cost-estimator --help`

### Package Distribution
Use the complete package for end users:
1. Copy entire `dist/openshift-cost-estimator-package/` directory
2. Include documentation and usage instructions
3. Provide AWS IAM policy requirements

### AWS Permissions
The executable requires the same AWS permissions as the source code. See `aws/IAM_POLICY.md` for details.

## Testing the Executable

### Automated Testing
The build script includes automatic testing:
1. **Import Test**: Verifies main module can be imported
2. **Help Test**: Runs `--help` command to verify basic functionality
3. **Syntax Check**: Validates Python syntax in test files

### Manual Testing
Test the executable manually:

```bash
# Basic functionality test
./dist/openshift-cost-estimator --help

# Version information
./dist/openshift-cost-estimator --version

# Test with actual cluster UID (requires AWS credentials)
./dist/openshift-cost-estimator --cluster-uid test-cluster --unified-discovery
```

### Performance Testing
Compare performance between source and executable:
- Startup time should be similar
- Memory usage may be slightly higher
- AWS API response times should be identical

## Maintenance and Updates

### Updating the Build Configuration
When adding new dependencies or modules:

1. **Update spec file**: Add new hidden imports and data files
2. **Update hooks**: Create new hooks for complex dependencies  
3. **Test build**: Verify the new functionality works in executable
4. **Update documentation**: Document any new requirements

### Version Management
The build system integrates with the project's versioning:
- Version is read from git tags via `setup.py`
- Executable includes version information
- CHANGELOG.md is included in distribution package

## Security Considerations

### Executable Security
- The executable contains all source code and dependencies
- Sensitive information should not be embedded in the build
- Use environment variables for AWS credentials and configuration
- Consider code signing for production distributions

### Build Environment Security
- Use clean build environments
- Verify dependency integrity
- Scan for vulnerabilities before building
- Use reproducible build processes

## Advanced Configuration

### Custom Hooks
Create custom PyInstaller hooks for complex dependencies:

```python
# hooks/hook-mymodule.py
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules('mymodule')
datas = collect_data_files('mymodule')
```

### Runtime Hooks
For runtime behavior modification:

```python
# runtime-hooks/runtime-hook-aws.py
import os
import sys

# Modify AWS behavior at runtime
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
```

### Build Customization
Modify the spec file for specific requirements:
- Change executable name
- Add/remove data files
- Modify compression settings
- Include custom icons or metadata

## Support and Resources

- **PyInstaller Documentation**: https://pyinstaller.readthedocs.io/
- **Project Issues**: Use GitHub issues for build-related problems
- **AWS SDK Issues**: Check boto3/botocore documentation
- **Build Logs**: Always check build logs for detailed error information