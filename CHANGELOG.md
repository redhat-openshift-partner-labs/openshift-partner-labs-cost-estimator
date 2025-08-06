# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.0] - 2025-08-06 (Latest)

### 🚀 Major Features
- **Unified Resource Discovery**: Revolutionary new discovery method using AWS Resource Groups Tagging API
- **Resource Enrichment**: Automatic enhancement of discovered resources with service-specific details
- **Comprehensive Cost System**: Advanced cost aggregation, calculation registry, and enhanced reporting

### ⚡ Enhancements  
- **CLI Options**: Added `--unified-discovery` flag for new discovery method
- **Performance**: Single API call discovers resources across all AWS services
- **Coverage**: Support for all AWS services that support tagging (EC2, ELB, RDS, S3, Lambda, Route53, IAM, CloudFormation)
- **Testing**: Massive expansion of test suite with 10+ new comprehensive test files

### 📚 Documentation
- Added comprehensive migration and implementation guides
- Enhanced usage documentation with unified discovery examples
- Added debugging utilities and cost calculation guides

### 🔧 Technical Improvements
- New `ResourceGroupsService` for unified discovery
- Enhanced cost calculation with pricing service integration
- Improved error handling and resource categorization
- Advanced cost filtering and aggregation capabilities

### 📁 Files Added/Changed
- **26 files changed** with **7,846+ lines added**
- New unified discovery service and comprehensive cost system
- Multiple debug utilities and extensive testing infrastructure
- Comprehensive documentation and migration guides

**Git Reference**: `ad0a2df` - Update system to use AWS Resource Explorer

---

## [v0.2.0] - 2025-07-31

### 🚀 Major Features
- **Enhanced Cost Calculation**: Proper cost calculations for stopped EC2 instances
- **AWS Pricing Service**: Full integration with AWS Pricing API for accurate cost estimation

### ⚡ Enhancements
- Improved cost accuracy for non-running resources
- Enhanced EC2 and ELB service cost integration
- Better cost analysis for operational planning

### 🧪 Testing
- Added comprehensive EC2 cost estimation tests
- Enhanced cost estimation test coverage

### 📁 Files Changed
- **9 files changed** with **1,016+ lines added**
- Major enhancements to cost calculation accuracy and service integration

**Git Reference**: `364815f` - Get proper calculations for resources even those not running

---

## [v0.1.1] - 2025-07-31

### 🐛 Bug Fixes
- **Resource Count Doubling**: Fixed issue where resource totals were incorrectly doubled in output

### 📚 Documentation
- **README.md**: Added comprehensive 311-line README with installation, usage, and examples
- Clear documentation of CLI options, permissions, and cost calculation notes

### 🔧 Dependencies
- Updated requirements.txt with additional dependencies
- Enhanced project dependency management

### 📁 Files Changed
- **3 files changed** across documentation and dependencies
- Comprehensive README.md creation
- Bug fix for resource counting accuracy

**Git References**: 
- `195c1a8` - Resolve issue where resource count total is doubled
- `58ba713` - Create a comprehensive README.md
- `6c38a6d` - Update requirements.txt

---

## [v0.1.0] - 2025-07-30 (Initial Release)

### 🚀 Initial Implementation
- **Modular Architecture**: Complete modular framework for multi-cloud cost estimation
- **Service Registry Pattern**: Pluggable architecture for AWS services (EC2, ELB)
- **Cost Estimation System**: Integration with AWS Cost Explorer and cost analysis
- **Tag-based Discovery**: Resource discovery using Kubernetes cluster UIDs

### 📦 Core Components
- **AWS Services Package**: EC2 and ELB service implementations
- **Cost Package**: Cost estimation, analysis, and reporting services  
- **Utils Package**: Formatting and discovery utilities
- **Testing Framework**: Comprehensive test suite for framework and cost estimation

### 🔧 Technical Features
- CLI interface with multiple export formats (JSON, CSV, HTML)
- AWS permissions documentation and IAM policy guidance
- Boto3 integration with proper error handling and pagination
- Resource tagging following OpenShift cluster conventions

### 📁 Initial Project Structure
- **30 files created** with **6,557+ lines**
- Complete project foundation with services, cost estimation, testing, and documentation
- Modular architecture ready for multi-cloud expansion

**Git Reference**: `525b60c` - WIP: Resource by service retrieval working

---

## Migration Guide

### Upgrading to v1.0.0 (Unified Discovery)

**Recommended**: Use the new unified discovery method for better performance and coverage:

```bash
# Old method (still supported)
python aws/main.py --cluster-uid your-cluster-uid

# New method (recommended)
python aws/main.py --cluster-uid your-cluster-uid --unified-discovery
```

**Benefits of Unified Discovery**:
- Single API call vs multiple service calls
- Automatic discovery of all AWS services
- Enhanced resource enrichment
- Better error handling and performance

**Required Permissions**: Add `resourcegroupstaggingapi:GetResources` to your IAM policy.

### Upgrading from v0.1.x to v0.2.0

**Enhanced Cost Calculations**: No breaking changes, but cost calculations are now more accurate for stopped instances and include proper operational cost estimates.

---

## Development

This project is built using [Claude Code](https://claude.ai/code) and follows the development workflow documented in `CLAUDE.md`.

---

## Contributing

Please see our [Contributing Guidelines](README.md#contributing) for information on how to contribute to this project.