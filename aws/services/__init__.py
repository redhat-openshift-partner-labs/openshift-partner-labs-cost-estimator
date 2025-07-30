"""
AWS Services package.

This package provides modular AWS service implementations for resource discovery.
Each service is implemented as a separate module that inherits from AWSService.

Available Services:
- EC2Service: EC2 instances, volumes, security groups, network interfaces
- ELBService: Classic load balancers, ALBs, NLBs

Usage:
    from services import EC2Service, SERVICE_REGISTRY
    from services import get_available_services

    # Get all available services
    services = get_available_services()
    
    # Use a specific service
    ec2_service = SERVICE_REGISTRY['EC2']
    
    # Check if a service is enabled
    from services import is_service_enabled
    if is_service_enabled('EC2'):
        # Use EC2 service
        pass

Adding New Services:
1. Create service file in services/ directory
2. Inherit from AWSService base class
3. Implement required methods (get_client, search_resources)
4. Register in services/registry.py
5. Import in this __init__.py file
"""

# Export base classes and types
from .base import AWSService, ResourceInfo

# Export service implementations
from .ec2_service import EC2Service
from .elb_service import ELBService

# Export registry and configuration
from .registry import (
    SERVICE_REGISTRY,
    SERVICE_CONFIG,
    get_available_services,
    get_service_config,
    is_service_enabled
)

# Define public API
__all__ = [
    # Base classes
    'AWSService',
    'ResourceInfo',
    
    # Service implementations
    'EC2Service',
    'ELBService',
    
    # Registry and configuration
    'SERVICE_REGISTRY',
    'SERVICE_CONFIG',
    'get_available_services',
    'get_service_config',
    'is_service_enabled',
]
