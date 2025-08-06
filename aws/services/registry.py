"""
Service registry and configuration management.

This module provides centralized service registration and configuration.
Services are registered here and can be enabled/disabled via configuration.

The registry pattern allows for:
- Dynamic service discovery
- Configuration-driven service enabling
- Easy addition of new services
- Service-specific configuration

Usage:
    from services import SERVICE_REGISTRY, get_available_services
    
    # Get all available services
    services = get_available_services()
    
    # Check if a service is enabled
    from services import is_service_enabled
    if is_service_enabled('EC2'):
        # Use EC2 service
        pass
    
    # Get service configuration
    from services import get_service_config
    config = get_service_config('EC2')

Adding New Services:
1. Import your service class
2. Add to SERVICE_REGISTRY dictionary
3. Add configuration to SERVICE_CONFIG dictionary
4. The service will be automatically available through the services package
"""

from .ec2_service import EC2Service
from .elb_service import ELBService
from .resource_groups_service import ResourceGroupsService


# Service Registry - Add new services here
SERVICE_REGISTRY = {
    'ResourceGroups': ResourceGroupsService(),  # Unified resource discovery
    'EC2': EC2Service(),
    'ELB': ELBService(),
}

# Configuration for each service (optional)
SERVICE_CONFIG = {
    'ResourceGroups': {
        'enabled': False,  # Start disabled for testing/gradual migration
        'unified_discovery': True,
        'fallback_to_individual': True,
        'enrich_resources': False,  # Whether to fetch additional resource details
        'resource_types': [
            'instances', 'volumes', 'security_groups', 'network_interfaces',  # EC2
            'classic_elbs', 'albs_nlbs', 'target_groups',  # ELB
            'rds_instances', 'rds_clusters',  # RDS
            's3_buckets',  # S3
            'lambda_functions',  # Lambda
            'iam_roles', 'iam_policies',  # IAM
            'cloudformation_stacks',  # CloudFormation
            'other_resources'  # Catch-all
        ]
    },
    'EC2': {
        'enabled': True,
        'resource_types': ['instances', 'volumes', 'security_groups', 'network_interfaces']
    },
    'ELB': {
        'enabled': True,
        'resource_types': ['classic_elbs', 'albs_nlbs']
    }
}


def get_available_services():
    """Get list of available service names
    
    Returns:
        List[str]: List of service names that are registered
    """
    return list(SERVICE_REGISTRY.keys())


def get_service_config(service_name: str):
    """Get configuration for a specific service
    
    Args:
        service_name (str): Name of the service to get configuration for
        
    Returns:
        dict: Service configuration dictionary, empty dict if not found
    """
    return SERVICE_CONFIG.get(service_name, {})


def is_service_enabled(service_name: str) -> bool:
    """Check if a service is enabled
    
    Args:
        service_name (str): Name of the service to check
        
    Returns:
        bool: True if service is enabled, False otherwise
    """
    return SERVICE_CONFIG.get(service_name, {}).get('enabled', True)


def should_use_unified_discovery() -> bool:
    """Check if unified discovery via ResourceGroups should be used
    
    Returns:
        bool: True if ResourceGroups service is enabled and unified discovery is configured
    """
    rg_config = SERVICE_CONFIG.get('ResourceGroups', {})
    return rg_config.get('enabled', False) and rg_config.get('unified_discovery', False)


def should_fallback_to_individual() -> bool:
    """Check if fallback to individual services is enabled when ResourceGroups fails
    
    Returns:
        bool: True if fallback is enabled
    """
    rg_config = SERVICE_CONFIG.get('ResourceGroups', {})
    return rg_config.get('fallback_to_individual', True)