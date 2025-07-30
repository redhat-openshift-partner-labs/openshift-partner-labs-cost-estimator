# Services Package

This package contains modular AWS service implementations for resource discovery.

## Overview

The services package provides a modular architecture for AWS resource discovery. Each AWS service is implemented as a separate module that inherits from the `AWSService` base class, ensuring consistency and maintainability.

## Structure

```
services/
├── __init__.py                  # Package exports using __all__
├── base.py                      # Base classes and shared types
├── ec2_service.py              # EC2 service implementation
├── elb_service.py              # ELB service implementation
└── registry.py                 # Service registry and configuration
```

## Components

### Base Classes (`base.py`)

- **`AWSService`**: Abstract base class for all AWS services
- **`ResourceInfo`**: Standardized data structure for resource information

### Service Implementations

- **`EC2Service`**: Discovers EC2 instances, volumes, security groups, and network interfaces
- **`ELBService`**: Discovers Classic load balancers, ALBs, and NLBs

### Registry (`registry.py`)

- **`SERVICE_REGISTRY`**: Central registry of all available services
- **`SERVICE_CONFIG`**: Configuration for each service
- **`get_available_services()`**: Get list of available service names
- **`get_service_config()`**: Get configuration for a specific service
- **`is_service_enabled()`**: Check if a service is enabled

## Usage

### Basic Import

```python
from services import EC2Service, ELBService, SERVICE_REGISTRY
from services import get_available_services
```

### Get Available Services

```python
from services import get_available_services

services = get_available_services()
print(services)  # ['EC2', 'ELB']
```

### Use a Specific Service

```python
from services import SERVICE_REGISTRY

ec2_service = SERVICE_REGISTRY['EC2']
session = boto3.Session()
client = ec2_service.get_client(session)
resources = ec2_service.search_resources(client, 'tag-key', 'tag-value')
```

### Check Service Status

```python
from services import is_service_enabled, get_service_config

# Check if EC2 service is enabled
if is_service_enabled('EC2'):
    print("EC2 service is enabled")

# Get EC2 service configuration
config = get_service_config('EC2')
print(config)  # {'enabled': True, 'resource_types': [...]}
```

## Adding a New Service

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
        super().__init__("RDS", ["instances", "snapshots"])
    
    def get_client(self, session: boto3.Session):
        return session.client('rds')
    
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        # Implementation here
        pass
```

### Step 2: Register Service

Add your service to `services/registry.py`:

```python
from .rds_service import RDSService

SERVICE_REGISTRY = {
    'EC2': EC2Service(),
    'ELB': ELBService(),
    'RDS': RDSService(),  # Add your service here
}

SERVICE_CONFIG = {
    'EC2': {'enabled': True, 'resource_types': [...]},
    'ELB': {'enabled': True, 'resource_types': [...]},
    'RDS': {'enabled': True, 'resource_types': [...]},  # Add config here
}
```

### Step 3: Import in Package

Add your service to `services/__init__.py`:

```python
from .rds_service import RDSService

__all__ = [
    # ... existing exports ...
    'RDSService',
]
```

### Step 4: Use Your Service

```python
from services import RDSService, SERVICE_REGISTRY

# Your service is now available
rds_service = SERVICE_REGISTRY['RDS']
```

## Service Implementation Guidelines

### Required Methods

Every service must implement:

1. **`__init__(self)`**: Initialize with service name and resource types
2. **`get_client(self, session)`**: Return the appropriate AWS client
3. **`search_resources(self, client, tag_key, tag_value)`**: Implement resource discovery

### Best Practices

1. **Inherit from AWSService**: Use the base class for consistency
2. **Use pagination**: Always use boto3 paginators for large result sets
3. **Handle errors gracefully**: Use try-catch blocks and call `self.handle_error()`
4. **Return ResourceInfo objects**: Use standardized data structure
5. **Include relevant metadata**: Store additional info in `additional_info` dict
6. **Follow naming conventions**: Use lowercase with underscores for resource types

### Error Handling

```python
try:
    # Your AWS API calls here
    pass
except ClientError as e:
    self.handle_error(e, 'resource_type')
```

### Resource Creation

```python
resources['instances'].append(ResourceInfo(
    id=instance['InstanceId'],
    name=instance.get('Name', instance['InstanceId']),
    state=instance['State']['Name'],
    type=instance['InstanceType'],
    additional_info={
        'launch_time': instance.get('LaunchTime'),
        'vpc_id': instance.get('VpcId')
    }
))
```

## Testing Your Service

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from services import RDSService

class TestRDSService(unittest.TestCase):
    def setUp(self):
        self.service = RDSService()
        self.mock_session = Mock()
        self.mock_client = Mock()
    
    def test_service_initialization(self):
        self.assertEqual(self.service.service_name, "RDS")
        self.assertEqual(self.service.resource_types, ["instances", "snapshots"])
    
    def test_get_client(self):
        client = self.service.get_client(self.mock_session)
        self.mock_session.client.assert_called_once_with('rds')
    
    def test_search_resources(self):
        # Mock AWS responses and test your implementation
        pass
```

### Integration Testing

```python
from services import SERVICE_REGISTRY
from utils.discoverer import AWSResourceDiscoverer

# Test with real AWS session
session = boto3.Session(profile_name='test')
discoverer = AWSResourceDiscoverer(session, 'tag-key', 'tag-value')
all_resources = discoverer.discover_all_resources()

# Verify your service is included
assert 'RDS' in all_resources
```

## Configuration

### Service Configuration

Each service can have configuration in `SERVICE_CONFIG`:

```python
SERVICE_CONFIG = {
    'RDS': {
        'enabled': True,
        'resource_types': ['instances', 'snapshots'],
        'max_results': 1000,
        'timeout': 30
    }
}
```

### Environment Variables

You can control service behavior with environment variables:

```bash
export AWS_RESOURCE_DISCOVERY_ENABLE_RDS=true
export AWS_RESOURCE_DISCOVERY_RDS_MAX_RESULTS=500
```

## Performance Considerations

1. **Use pagination**: Always use boto3 paginators for large result sets
2. **Limit API calls**: Minimize the number of AWS API calls
3. **Handle rate limiting**: Implement exponential backoff for API limits
4. **Cache results**: Consider caching for frequently accessed data
5. **Parallel processing**: Use async/await for better performance (future enhancement)

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure service is properly registered in `registry.py`
2. **Permission errors**: Check AWS credentials and IAM permissions
3. **Rate limiting**: Implement delays between API calls
4. **Service not found**: Verify service is added to `SERVICE_REGISTRY`

### Debug Mode

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In your service method
logger.debug(f"Searching {self.service_name} resources with tag {tag_key}:{tag_value}")
```

## Future Enhancements

1. **Async support**: Implement async/await for better performance
2. **Service discovery**: Automatic discovery of available AWS services
3. **Plugin system**: Dynamic loading of service implementations
4. **Configuration management**: External configuration files
5. **Caching**: Result caching to avoid repeated API calls
6. **Metrics**: Performance metrics and monitoring 