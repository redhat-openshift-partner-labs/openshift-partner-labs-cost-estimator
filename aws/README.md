# AWS Resource Discovery Framework

This framework provides a modular approach to discovering AWS resources tagged for Kubernetes clusters with optional cost estimation capabilities. It uses a service registry pattern to make adding new AWS services straightforward and maintainable.

## Overview

The framework consists of several key components organized in a modular structure:

1. **AWSService** - Abstract base class for all AWS services
2. **ResourceInfo** - Standardized data structure for resource information
3. **Service Registry** - Central registry of all available services
4. **ResourceFormatter** - Handles output formatting
5. **AWSResourceDiscoverer** - Main orchestrator
6. **Cost Services** - Optional cost estimation and analysis (NEW)

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Script   │───▶│  Service        │───▶│  AWS API        │
│   (main.py)     │    │  Registry       │    │  Clients        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Utils Package   │    │ Services        │    │ Resource        │
│ (formatter,     │    │ Package         │    │ Discovery       │
│  discoverer)    │    │ (EC2, ELB, etc.)│    │ Engine          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Cost Package    │    │ Cost Services   │    │ AWS Cost        │
│ (analyzer,      │    │ (Explorer,      │    │ Explorer API    │
│  reporter)      │    │  Analyzer,      │    │                 │
│                 │    │  Reporter)      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## File Structure

```
aws/
├── main.py                           # Main script (orchestration only)
├── services/                         # Resource discovery services
│   ├── __init__.py                  # Package exports using __all__
│   ├── base.py                      # Base classes and shared types
│   ├── ec2_service.py              # EC2 service implementation
│   ├── elb_service.py              # ELB service implementation
│   └── registry.py                 # Service registry and configuration
├── cost/                            # NEW: Cost estimation services
│   ├── __init__.py                  # Package exports
│   ├── base.py                      # Cost service base classes
│   ├── explorer_service.py          # AWS Cost Explorer integration
│   ├── analyzer_service.py          # Cost analysis and insights
│   ├── reporter_service.py          # Cost reporting and export
│   └── registry.py                  # Cost service registry
├── utils/
│   ├── __init__.py
│   ├── formatter.py                # Resource formatting utilities
│   └── discoverer.py               # Resource discovery orchestrator
├── examples/
│   └── rds_service_example.py      # Example service implementation
└── [test files and documentation]
```

## Cost Estimation Features

The framework now includes optional cost estimation capabilities that integrate with AWS Cost Explorer API. This allows you to analyze costs for discovered resources and identify optimization opportunities.

### Cost Services

The cost estimation functionality is organized into three main services:

1. **CostExplorerService** - Handles AWS Cost Explorer API interactions
2. **CostAnalyzerService** - Analyzes cost data and provides insights
3. **CostReporterService** - Generates cost reports and exports

### Cost Data Structures

```python
@dataclass
class CostRecord:
    """Represents a cost record for a specific time period"""
    start_date: datetime
    end_date: datetime
    amount: float
    service: str
    currency: str = "USD"
    unit: str = "Hrs"

@dataclass
class CostSummary:
    """Summary of costs for a resource or group of resources"""
    total_cost: float
    period_start: datetime
    period_end: datetime
    cost_breakdown: Dict[str, float]  # Service -> Cost
    resource_count: int
    average_cost_per_resource: float
    cost_trend: str  # "increasing", "decreasing", "stable"
    forecast_30_days: float
    forecast_90_days: float

@dataclass
class OptimizationSuggestion:
    """Cost optimization suggestion"""
    resource_id: str
    resource_type: str
    current_cost: float
    potential_savings: float
    suggestion_type: str  # "resize", "reserved_instance", "delete", "schedule"
    description: str
    implementation_steps: List[str]
    risk_level: str  # "low", "medium", "high"
```

### Enhanced ResourceInfo

The `ResourceInfo` class has been enhanced with optional cost fields while maintaining backward compatibility:

```python
@dataclass
class ResourceInfo:
    """Enhanced resource information with optional cost data"""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    # Optional cost-related fields (None by default for backward compatibility)
    cost_data: Optional[Dict[str, Any]] = None
    cost_history: Optional[List[CostRecord]] = None
    cost_forecast: Optional[List[CostRecord]] = None
    optimization_suggestions: Optional[List[OptimizationSuggestion]] = None
```

### Cost Analysis Capabilities

- **Cost Discovery**: Retrieve actual costs for discovered resources
- **Cost Forecasting**: Provide cost projections for future periods
- **Cost Breakdown**: Show costs by service, resource type, and time period
- **Cost Optimization**: Identify potential cost savings opportunities
- **Cost Reporting**: Generate detailed cost reports and summaries

### Export Formats

The framework supports multiple export formats for cost reports:

- **JSON**: Structured data export for programmatic analysis
- **CSV**: Spreadsheet-friendly format for data analysis
- **HTML**: Web-ready reports with formatting and styling

## Adding a New AWS Service

### Step 1: Create Service File

Create a new file in the `services/` directory (e.g., `services/rds_service.py`):

```python
"""
RDS service implementation for AWS resource discovery.
"""

from .base import AWSService, ResourceInfo
from botocore.exceptions import ClientError
from typing import Dict, List
import boto3


class RDSService(AWSService):
    """RDS service implementation"""
    
    def __init__(self):
        super().__init__("RDS", ["instances", "snapshots", "subnet_groups"])
    
    def get_client(self, session: boto3.Session):
        return session.client('rds')
    
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        resources = {rt: [] for rt in self.resource_types}
        
        # RDS Instances
        try:
            paginator = client.get_paginator('describe_db_instances')
            for page in paginator.paginate():
                for instance in page['DBInstances']:
                    # Check tags for this instance
                    tags = client.list_tags_for_resource(
                        ResourceName=instance['DBInstanceArn']
                    )['TagList']
                    
                    for tag in tags:
                        if tag['Key'] == tag_key and tag['Value'] == tag_value:
                            resources['instances'].append(ResourceInfo(
                                id=instance['DBInstanceIdentifier'],
                                name=instance['DBInstanceIdentifier'],
                                state=instance['DBInstanceStatus'],
                                type=instance['DBInstanceClass'],
                                additional_info={
                                    'engine': instance['Engine'],
                                    'storage': f"{instance['AllocatedStorage']} GB"
                                }
                            ))
                            break
        except ClientError as e:
            self.handle_error(e, 'instances')
        
        return resources
```

### Step 2: Register the Service

Add your service to `services/registry.py`:

```python
from .rds_service import RDSService

# Service Registry - Add new services here
SERVICE_REGISTRY = {
    'EC2': EC2Service(),
    'ELB': ELBService(),
    'RDS': RDSService(),  # Add your new service here
}

# Configuration for each service (optional)
SERVICE_CONFIG = {
    'EC2': {
        'enabled': True,
        'resource_types': ['instances', 'volumes', 'security_groups', 'network_interfaces']
    },
    'ELB': {
        'enabled': True,
        'resource_types': ['classic_elbs', 'albs_nlbs']
    },
    'RDS': {  # Add configuration for your service
        'enabled': True,
        'resource_types': ['instances', 'snapshots', 'subnet_groups']
    }
}
```

### Step 3: Import and Use

Your service is now automatically available through the services package:

```python
from services import RDSService, SERVICE_REGISTRY
from services import get_available_services

# Check available services
services = get_available_services()  # ['EC2', 'ELB', 'RDS']

# Use your service
rds_service = SERVICE_REGISTRY['RDS']
```

## Service Implementation Guidelines

### Required Methods

1. **`__init__(self)`** - Initialize with service name and resource types
2. **`get_client(self, session)`** - Return the appropriate AWS client
3. **`search_resources(self, client, tag_key, tag_value)`** - Implement resource discovery

### Best Practices

1. **Use pagination** - Always use boto3 paginators for large result sets
2. **Handle errors gracefully** - Use try-catch blocks and call `self.handle_error()`
3. **Return standardized data** - Use `ResourceInfo` objects for consistency
4. **Include relevant metadata** - Store additional info in `additional_info` dict
5. **Follow naming conventions** - Use lowercase with underscores for resource types
6. **Create separate files** - Each service should be in its own file in `services/`

### ResourceInfo Structure

```python
@dataclass
class ResourceInfo:
    id: str                    # Required: Unique identifier
    name: Optional[str] = None # Optional: Human-readable name
    type: Optional[str] = None # Optional: Resource type/class
    state: Optional[str] = None # Optional: Current state
    region: Optional[str] = None # Optional: AWS region
    additional_info: Optional[Dict[str, Any]] = None # Optional: Extra metadata
    # Optional cost-related fields (None by default for backward compatibility)
    cost_data: Optional[Dict[str, Any]] = None # Optional: Cost information
    cost_history: Optional[List[CostRecord]] = None # Optional: Historical costs
    cost_forecast: Optional[List[CostRecord]] = None # Optional: Cost forecasts
    optimization_suggestions: Optional[List[OptimizationSuggestion]] = None # Optional: Optimization suggestions
```

## Common AWS Service Patterns

### Pattern 1: Services with Tag Filtering Support

```python
# EC2, EBS, Security Groups, etc.
tag_filter = [{'Name': f'tag:{tag_key}', 'Values': [tag_value]}]
paginator = client.get_paginator('describe_instances')
for page in paginator.paginate(Filters=tag_filter):
    # Process resources
```

### Pattern 2: Services Requiring Individual Tag Lookup

```python
# RDS, ELB, etc.
paginator = client.get_paginator('describe_db_instances')
for page in paginator.paginate():
    for resource in page['DBInstances']:
        tags = client.list_tags_for_resource(
            ResourceName=resource['DBInstanceArn']
        )['TagList']
        
        for tag in tags:
            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                # Process matching resource
                break
```

### Pattern 3: Services with Multiple Clients

```python
# ELB service example
def search_resources(self, session: boto3.Session, tag_key: str, tag_value: str):
    # Use session directly instead of single client
    elb_client = session.client('elb')
    elbv2_client = session.client('elbv2')
    # Process each client type
```

## Development Workflow

### Creating a New Service

1. **Create Service File**: Create `services/your_service.py`
2. **Inherit from Base**: Extend `AWSService` class
3. **Implement Methods**: Add `get_client()` and `search_resources()`
4. **Add to Registry**: Register in `services/registry.py`
5. **Write Tests**: Create unit tests for your service
6. **Update Documentation**: Add examples and usage notes

### Testing Your Service

```python
from services import YourService
from utils.discoverer import AWSResourceDiscoverer

# Test your service in isolation
service = YourService()
session = boto3.Session(profile_name='test')
client = service.get_client(session)

# Test with mock data
resources = service.search_resources(client, 'test-key', 'test-value')
assert 'your_resource_type' in resources
```

### Integration Testing

```python
from services import SERVICE_REGISTRY
from utils.discoverer import AWSResourceDiscoverer

# Test full discovery workflow
discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
all_resources = discoverer.discover_all_resources()

# Verify your service is included
assert 'YOUR_SERVICE' in all_resources
```

### Cost Estimation Testing

```python
from cost import CostExplorerService, CostAnalyzerService
from utils.discoverer import AWSResourceDiscoverer

# Test cost estimation workflow
discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
all_resources = discoverer.discover_all_resources(include_costs=True)

# Test cost services
explorer_service = CostExplorerService()
analyzer_service = CostAnalyzerService()

# Verify cost services are working
assert explorer_service.service_name == "CostExplorer"
assert analyzer_service.service_name == "CostAnalyzer"
```

## Command Line Usage

### Basic Resource Discovery
```bash
# Search all services
python main.py --cluster-uid my-cluster-123

# Search specific services
python main.py --cluster-uid my-cluster-123 --services EC2 RDS

# Use different AWS profile/region
python main.py --cluster-uid my-cluster-123 --profile production --region us-west-2
```

### Cost Estimation Features

```bash
# Resource discovery with cost estimation
python main.py --cluster-uid my-cluster-123 --include-costs

# Detailed cost analysis with optimization suggestions
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --cost-period 60 \
    --forecast-days 180 \
    --optimization

# Export cost report to JSON
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --export-format json \
    --export-file cost_report.json

# Export cost report to CSV
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --export-format csv \
    --export-file cost_report.csv

# Export cost report to HTML
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --export-format html \
    --export-file cost_report.html
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--cluster-uid` | Kubernetes cluster UID (required) | - |
| `--region` | AWS region | Use AWS config/environment |
| `--profile` | AWS profile to use | - |
| `--services` | Specific AWS services to search | All enabled services |
| `--include-costs` | Include cost estimation in output | False |
| `--cost-period` | Cost analysis period in days | 30 |
| `--forecast-days` | Cost forecast period in days | 90 |
| `--optimization` | Include cost optimization suggestions | False |
| `--export-format` | Export format (json, csv, html) | - |
| `--export-file` | Output file for cost report export | - |

## API Reference

### Services Package
```python
from services import (
    AWSService,           # Base class for all services
    ResourceInfo,         # Standardized resource data structure
    EC2Service,           # EC2 service implementation
    ELBService,           # ELB service implementation
    SERVICE_REGISTRY,     # Central service registry
    get_available_services,  # Get list of available services
    get_service_config,   # Get configuration for a service
    is_service_enabled    # Check if a service is enabled
)
```

### Cost Package
```python
from cost import (
    CostExplorerService,    # AWS Cost Explorer integration
    CostAnalyzerService,    # Cost analysis and optimization
    CostReporterService,    # Cost reporting and export
    CostRecord,             # Cost record data structure
    CostSummary,            # Cost summary data structure
    OptimizationSuggestion  # Optimization suggestion data structure
)
```

### Utils Package
```python
from utils.formatter import ResourceFormatter      # Output formatting utilities
from utils.discoverer import AWSResourceDiscoverer # Resource discovery orchestrator
```

## AWS Permissions

### Resource Discovery Permissions

For basic resource discovery, your AWS credentials need permissions for the services you're searching:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeVolumes",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeNetworkInterfaces",
                "elasticloadbalancing:DescribeLoadBalancers",
                "elasticloadbalancing:DescribeTargetGroups"
            ],
            "Resource": "*"
        }
    ]
}
```

### Cost Estimation Permissions

For cost estimation features, additional permissions are required:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetReservationCoverage",
                "ce:GetReservationUtilization",
                "ce:GetDimensionValues",
                "ce:GetTags"
            ],
            "Resource": "*"
        }
    ]
}
```

## Troubleshooting

### Common Issues

1. **Permission Errors** - Ensure AWS credentials have appropriate permissions
2. **Rate Limiting** - Add delays between API calls if needed
3. **Tag Format Issues** - Verify tag key/value format matches expected pattern
4. **Client Errors** - Check AWS service availability in target region
5. **Import Errors** - Ensure service is properly registered in `services/registry.py`
6. **Cost Explorer Errors** - Verify Cost Explorer API is enabled in your AWS account

### Debug Mode

Add debug logging to your service:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In your service method
logger.debug(f"Searching {self.service_name} resources with tag {tag_key}:{tag_value}")
```

## Future Enhancements

1. **Async Support** - Implement async/await for better performance
2. **Caching** - Add result caching to avoid repeated API calls
3. **Export Formats** - Support additional output formats (YAML, XML)
4. **Resource Dependencies** - Map relationships between resources
5. **Plugin System** - Dynamic loading of service implementations
6. **Advanced Cost Forecasting** - Machine learning-based cost predictions
7. **Multi-Region Cost Analysis** - Cross-region cost comparison
8. **Cost Optimization Automation** - Automated resource optimization
9. **Resource Dependencies Mapping** - Visualize resource relationships
10. **Real-time Cost Monitoring** - Live cost tracking and alerts

## Contributing

When adding new services:

1. **Follow the Modular Pattern**: Create separate service files in `services/`
2. **Extend Base Class**: Inherit from `AWSService` for consistency
3. **Add to Registry**: Register in `services/registry.py`
4. **Write Tests**: Add comprehensive unit and integration tests
5. **Update Documentation**: Add examples and usage notes
6. **Consider Performance**: Optimize for large resource sets
7. **Handle Errors Gracefully**: Implement proper error handling 