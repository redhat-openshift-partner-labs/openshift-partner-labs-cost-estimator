# Utils Package

This package contains utility classes for the AWS resource discovery framework.

## Overview

The utils package provides essential utilities for resource discovery, formatting, and orchestration. These utilities work with the services package to provide a complete resource discovery solution.

## Structure

```
utils/
├── __init__.py
├── formatter.py                # Resource formatting utilities
└── discoverer.py               # Resource discovery orchestrator
```

## Components

### Resource Formatter (`formatter.py`)

The `ResourceFormatter` class handles the formatting and display of discovered resources.

**Key Features:**
- Standardized resource formatting
- Human-readable output
- Detailed resource information display
- Summary statistics

**Usage:**
```python
from utils.formatter import ResourceFormatter

# Format a single resource
formatted = ResourceFormatter.format_resource_info(resource)

# Print all results
ResourceFormatter.print_results(all_resources, cluster_uid)
```

**Methods:**
- `format_resource_info(resource)`: Format a single resource for display
- `print_results(all_resources, cluster_uid)`: Print all discovered resources

### Resource Discoverer (`discoverer.py`)

The `AWSResourceDiscoverer` class orchestrates the resource discovery process across all registered services.

**Key Features:**
- Multi-service resource discovery
- Error handling and recovery
- Service filtering and selection
- Result aggregation

**Usage:**
```python
from utils.discoverer import AWSResourceDiscoverer

# Create discoverer
discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)

# Discover all resources
all_resources = discoverer.discover_all_resources()
```

**Methods:**
- `__init__(session, tag_key, tag_value)`: Initialize the discoverer
- `discover_all_resources()`: Discover resources across all services

## Usage Examples

### Basic Resource Discovery

```python
import boto3
from utils.discoverer import AWSResourceDiscoverer
from utils.formatter import ResourceFormatter

# Create AWS session
session = boto3.Session(profile_name='production')

# Create discoverer
discoverer = AWSResourceDiscoverer(
    session, 
    'kubernetes.io/cluster/my-cluster', 
    'owned'
)

# Discover resources
all_resources = discoverer.discover_all_resources()

# Format and display results
ResourceFormatter.print_results(all_resources, 'my-cluster')
```

### Custom Resource Formatting

```python
from utils.formatter import ResourceFormatter
from services import ResourceInfo

# Create a custom resource
resource = ResourceInfo(
    id='i-1234567890abcdef0',
    name='my-instance',
    state='running',
    type='t3.micro',
    additional_info={'launch_time': '2023-01-01T00:00:00Z'}
)

# Format the resource
formatted = ResourceFormatter.format_resource_info(resource)
print(formatted)
# Output: "    - my-instance (state: running, type: t3.micro, launch_time: 2023-01-01T00:00:00Z)"
```

### Service-Specific Discovery

```python
from utils.discoverer import AWSResourceDiscoverer
from services import SERVICE_REGISTRY

# Filter to specific services
session = boto3.Session()
discoverer = AWSResourceDiscoverer(session, 'tag-key', 'tag-value')

# Temporarily modify registry for specific services
original_registry = SERVICE_REGISTRY.copy()
SERVICE_REGISTRY.clear()
SERVICE_REGISTRY['EC2'] = original_registry['EC2']

# Discover only EC2 resources
ec2_resources = discoverer.discover_all_resources()

# Restore original registry
SERVICE_REGISTRY.clear()
SERVICE_REGISTRY.update(original_registry)
```

## Integration with Services Package

The utils package is designed to work seamlessly with the services package:

```python
from services import SERVICE_REGISTRY, get_available_services
from utils.discoverer import AWSResourceDiscoverer
from utils.formatter import ResourceFormatter

# Get available services
services = get_available_services()

# Create discoverer
discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)

# Discover resources from all services
all_resources = discoverer.discover_all_resources()

# Format results
ResourceFormatter.print_results(all_resources, cluster_uid)
```

## Error Handling

### Discoverer Error Handling

The `AWSResourceDiscoverer` includes comprehensive error handling:

```python
try:
    all_resources = discoverer.discover_all_resources()
except Exception as e:
    print(f"Discovery failed: {e}")
    # Handle error appropriately
```

### Formatter Error Handling

The `ResourceFormatter` handles malformed resources gracefully:

```python
# Safe formatting even with incomplete resources
resource = ResourceInfo(id='test-id')  # Minimal resource
formatted = ResourceFormatter.format_resource_info(resource)
# Output: "    - test-id"
```

## Performance Considerations

### Discovery Performance

1. **Parallel Processing**: Future enhancement for concurrent service discovery
2. **Caching**: Consider caching results for repeated queries
3. **Service Filtering**: Only discover from needed services
4. **Pagination**: Services handle pagination internally

### Formatting Performance

1. **Lazy Evaluation**: Only format when needed
2. **Streaming Output**: For large result sets
3. **Memory Efficiency**: Process resources one at a time

## Customization

### Custom Formatter

You can extend the `ResourceFormatter` for custom output:

```python
class CustomFormatter(ResourceFormatter):
    @staticmethod
    def format_resource_info(resource: ResourceInfo) -> str:
        # Custom formatting logic
        return f"Custom: {resource.id} ({resource.state})"
    
    @staticmethod
    def print_results(all_resources, cluster_uid):
        # Custom output format
        print(f"Custom output for cluster: {cluster_uid}")
        # ... custom implementation
```

### Custom Discoverer

You can extend the `AWSResourceDiscoverer` for custom discovery logic:

```python
class CustomDiscoverer(AWSResourceDiscoverer):
    def discover_all_resources(self):
        # Custom discovery logic
        results = super().discover_all_resources()
        
        # Add custom processing
        for service_name, service_resources in results.items():
            # Custom processing per service
            pass
        
        return results
```

## Testing

### Unit Testing

```python
import unittest
from unittest.mock import Mock
from utils.formatter import ResourceFormatter
from utils.discoverer import AWSResourceDiscoverer
from services import ResourceInfo

class TestFormatter(unittest.TestCase):
    def test_format_resource_info(self):
        resource = ResourceInfo(id='test-id', state='running')
        formatted = ResourceFormatter.format_resource_info(resource)
        self.assertIn('test-id', formatted)
        self.assertIn('running', formatted)

class TestDiscoverer(unittest.TestCase):
    def setUp(self):
        self.mock_session = Mock()
        self.discoverer = AWSResourceDiscoverer(
            self.mock_session, 'tag-key', 'tag-value'
        )
    
    def test_discoverer_initialization(self):
        self.assertEqual(self.discoverer.tag_key, 'tag-key')
        self.assertEqual(self.discoverer.tag_value, 'tag-value')
```

### Integration Testing

```python
from utils.discoverer import AWSResourceDiscoverer
from utils.formatter import ResourceFormatter

# Test with real AWS session
session = boto3.Session(profile_name='test')
discoverer = AWSResourceDiscoverer(session, 'tag-key', 'tag-value')

# Test discovery
all_resources = discoverer.discover_all_resources()

# Test formatting
ResourceFormatter.print_results(all_resources, 'test-cluster')
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure services package is available
2. **Session errors**: Verify AWS credentials and session creation
3. **Service errors**: Check that services are properly registered
4. **Formatting errors**: Verify ResourceInfo objects are properly structured

### Debug Mode

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In discoverer
logger.debug(f"Discovering resources with tag {tag_key}:{tag_value}")

# In formatter
logger.debug(f"Formatting resource: {resource.id}")
```

## Future Enhancements

1. **Async support**: Async/await for better performance
2. **Export formats**: JSON, CSV, YAML output support
3. **Custom formatters**: Plugin system for custom output formats
4. **Progress tracking**: Real-time progress updates for long-running discoveries
5. **Caching**: Result caching for repeated queries
6. **Metrics**: Performance metrics and monitoring
7. **Streaming**: Streaming output for large result sets 