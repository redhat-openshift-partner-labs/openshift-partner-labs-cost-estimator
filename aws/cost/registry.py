"""
Cost service registry and configuration management.

This module provides centralized cost service registration and configuration.
Cost services are registered here and can be enabled/disabled via configuration.

The registry pattern allows for:
- Dynamic cost service discovery
- Configuration-driven cost service enabling
- Easy addition of new cost services
- Cost service-specific configuration

Usage:
    from cost import COST_SERVICE_REGISTRY, get_available_cost_services
    
    # Get all available cost services
    services = get_available_cost_services()
    
    # Check if a cost service is enabled
    from cost import is_cost_service_enabled
    if is_cost_service_enabled('explorer'):
        # Use cost explorer service
        pass
    
    # Get cost service configuration
    from cost import get_cost_service_config
    config = get_cost_service_config('explorer')

Adding New Cost Services:
1. Import your cost service class
2. Add to COST_SERVICE_REGISTRY dictionary
3. Add configuration to COST_SERVICE_CONFIG dictionary
4. The cost service will be automatically available through the cost package
"""

from .explorer_service import CostExplorerService
from .analyzer_service import CostAnalyzerService
from .reporter_service import CostReporterService
from .pricing_service import PricingService


# Cost Service Registry - Add new cost services here
COST_SERVICE_REGISTRY = {
    'explorer': CostExplorerService(),
    'analyzer': CostAnalyzerService(),
    'reporter': CostReporterService(),
    'pricing': PricingService(),
}

# Configuration for each cost service (optional)
COST_SERVICE_CONFIG = {
    'explorer': {
        'enabled': True,
        'max_retries': 3,
        'timeout': 30
    },
    'analyzer': {
        'enabled': True,
        'forecast_days': 90,
        'optimization_threshold': 100
    },
    'reporter': {
        'enabled': True,
        'export_formats': ['json', 'csv', 'html']
    },
    'pricing': {
        'enabled': True,
        'cache_pricing_data': True,
        'fallback_to_estimates': True
    }
}


def get_available_cost_services():
    """Get list of available cost service names
    
    Returns:
        List[str]: List of cost service names that are registered
    """
    return list(COST_SERVICE_REGISTRY.keys())


def get_cost_service_config(service_name: str):
    """Get configuration for a specific cost service
    
    Args:
        service_name (str): Name of the cost service to get configuration for
        
    Returns:
        dict: Cost service configuration dictionary, empty dict if not found
    """
    return COST_SERVICE_CONFIG.get(service_name, {})


def is_cost_service_enabled(service_name: str) -> bool:
    """Check if a cost service is enabled
    
    Args:
        service_name (str): Name of the cost service to check
        
    Returns:
        bool: True if cost service is enabled, False otherwise
    """
    return COST_SERVICE_CONFIG.get(service_name, {}).get('enabled', True)


def get_cost_service(service_name: str):
    """Get a cost service instance by name
    
    Args:
        service_name (str): Name of the cost service to get
        
    Returns:
        CostService: Cost service instance, None if not found
    """
    return COST_SERVICE_REGISTRY.get(service_name)


def register_cost_service(service_name: str, service_instance, config: dict = None):
    """Register a new cost service
    
    Args:
        service_name (str): Name of the cost service
        service_instance: Cost service instance
        config (dict): Optional configuration for the service
    """
    COST_SERVICE_REGISTRY[service_name] = service_instance
    if config:
        COST_SERVICE_CONFIG[service_name] = config
    else:
        COST_SERVICE_CONFIG[service_name] = {'enabled': True} 