"""
Cost calculator registry and factory pattern for AWS resources.

This module provides a centralized registry for cost calculators and
implements the factory pattern for selecting appropriate calculators
based on resource characteristics.
"""

from typing import Dict, List, Optional, Callable, Any
import boto3
from datetime import datetime, timedelta
import asyncio
import time
import random
from .cost_categories import CostCategory, CostClassifier, CostPriority
from .pricing_service import PricingService


class CostCalculatorRegistry:
    """Registry for cost calculation methods"""
    
    def __init__(self):
        self._calculators: Dict[str, Callable] = {}
        self._pricing_service: Optional[PricingService] = None
        self._batch_size = 10  # Process resources in batches
        self._max_retries = 3
        self._base_delay = 1.0  # Base delay for exponential backoff
    
    def register_calculator(self, resource_category: str, calculator_func: Callable):
        """Register a cost calculator for a specific resource category"""
        self._calculators[resource_category] = calculator_func
    
    def get_calculator(self, resource_category: str) -> Optional[Callable]:
        """Get the appropriate cost calculator for a resource category"""
        return self._calculators.get(resource_category)
    
    def set_pricing_service(self, pricing_service: PricingService):
        """Set the pricing service instance"""
        self._pricing_service = pricing_service
    
    def calculate_cost_with_retry(
        self, 
        resource: 'ResourceInfo', 
        region: str, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate cost with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self._max_retries + 1):
            try:
                if self._pricing_service:
                    return self._pricing_service.calculate_resource_cost(resource, region, days)
                else:
                    raise ValueError("Pricing service not initialized")
                    
            except Exception as e:
                last_exception = e
                
                if attempt < self._max_retries:
                    # Exponential backoff with jitter
                    delay = self._base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Cost calculation attempt {attempt + 1} failed for {resource.id}, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    # Final attempt failed, return fallback cost data
                    print(f"All cost calculation attempts failed for {resource.id}: {e}")
                    return self._get_fallback_cost_data(resource, last_exception)
        
        # This should never be reached, but included for completeness
        return self._get_fallback_cost_data(resource, last_exception)
    
    def calculate_batch_costs(
        self, 
        resources: List['ResourceInfo'], 
        region: str, 
        days: int = 30,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate costs for multiple resources in batches for better performance"""
        results = {}
        total_resources = len(resources)
        processed = 0
        
        # Sort resources by priority (high-cost resources first)
        prioritized_resources = self._prioritize_resources_for_batch(resources)
        
        # Process in batches
        for i in range(0, len(prioritized_resources), self._batch_size):
            batch = prioritized_resources[i:i + self._batch_size]
            
            # Process batch
            for resource in batch:
                try:
                    cost_data = self.calculate_cost_with_retry(resource, region, days)
                    results[resource.id] = cost_data
                except Exception as e:
                    print(f"Failed to calculate cost for {resource.id}: {e}")
                    results[resource.id] = self._get_fallback_cost_data(resource, e)
                
                processed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(processed, total_resources)
            
            # Small delay between batches to avoid overwhelming APIs
            if i + self._batch_size < len(prioritized_resources):
                time.sleep(0.1)
        
        return results
    
    def _prioritize_resources_for_batch(self, resources: List['ResourceInfo']) -> List['ResourceInfo']:
        """Sort resources by cost priority for batch processing"""
        def get_priority_score(resource):
            resource_type = getattr(resource, 'type', 'unknown')
            category = resource.additional_info.get('resource_category', 'unknown') if resource.additional_info else 'unknown'
            
            # Try to determine resource category from various sources
            if not category or category == 'unknown':
                if hasattr(resource, 'additional_info') and resource.additional_info:
                    service = resource.additional_info.get('service', '')
                    resource_type_from_arn = resource.additional_info.get('resource_type', '')
                    if service and resource_type_from_arn:
                        # Use the same mapping logic as PricingService
                        category = self._map_arn_to_category(service, resource_type_from_arn)
            
            priority = CostClassifier.get_cost_priority(category)
            
            # Assign numeric scores for sorting (higher score = higher priority)
            priority_scores = {
                CostPriority.HIGH: 4,
                CostPriority.MEDIUM: 3,
                CostPriority.LOW: 2,
                CostPriority.FREE: 1,
                CostPriority.UNKNOWN: 0
            }
            
            return priority_scores.get(priority, 0)
        
        return sorted(resources, key=get_priority_score, reverse=True)
    
    def _map_arn_to_category(self, arn_service: str, arn_resource_type: str) -> str:
        """Map ARN service and resource type to cost calculation category"""
        # This mirrors the logic in PricingService._map_arn_to_category
        service_type_mapping = {
            'ec2': {
                'instance': 'instances',
                'volume': 'volumes',
                'natgateway': 'nat_gateways',
                'nat-gateway': 'nat_gateways',
                'elastic-ip': 'elastic_ips',
                'vpc-endpoint': 'vpc_endpoints',
                'security-group': 'security_groups',
                'network-interface': 'network_interfaces',
                'vpc': 'vpcs',
                'subnet': 'subnets',
                'route-table': 'route_tables',
                'internet-gateway': 'internet_gateways'
            },
            'elasticloadbalancing': {
                'loadbalancer': 'albs_nlbs',
                'targetgroup': 'target_groups'
            },
            's3': {
                '': 's3_buckets'
            },
            'route53': {
                'hostedzone': 'route53_zones',
                'rrset': 'route53_records'
            },
            'iam': {
                'role': 'iam_roles',
                'policy': 'iam_policies'
            },
            'cloudformation': {
                'stack': 'cloudformation_stacks'
            }
        }
        
        if arn_service in service_type_mapping:
            service_map = service_type_mapping[arn_service]
            
            if arn_resource_type in service_map:
                return service_map[arn_resource_type]
            
            for key, category in service_map.items():
                if key and key in arn_resource_type:
                    return category
            
            if '' in service_map:
                return service_map['']
        
        return 'unknown'
    
    def _get_fallback_cost_data(self, resource: 'ResourceInfo', exception: Exception) -> Dict[str, Any]:
        """Generate fallback cost data when calculation fails"""
        return {
            'total_cost': 0.0,
            'service_breakdown': {'Unknown': 0.0},
            'service': 'Unknown',
            'is_estimated': True,
            'pricing_source': f'Fallback (Error: {str(exception)[:100]})',
            'calculation_failed': True,
            'error': str(exception)
        }
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the calculator registry"""
        return {
            'registered_calculators': len(self._calculators),
            'calculator_categories': list(self._calculators.keys()),
            'batch_size': self._batch_size,
            'max_retries': self._max_retries,
            'base_delay': self._base_delay
        }


class CostCalculatorFactory:
    """Factory for creating and configuring cost calculators"""
    
    @staticmethod
    def create_registry() -> CostCalculatorRegistry:
        """Create a fully configured calculator registry"""
        registry = CostCalculatorRegistry()
        
        # Register default calculators
        # (These would be actual calculator functions in a full implementation)
        registry.register_calculator('instances', CostCalculatorFactory._ec2_instance_calculator)
        registry.register_calculator('volumes', CostCalculatorFactory._ebs_volume_calculator)
        registry.register_calculator('nat_gateways', CostCalculatorFactory._nat_gateway_calculator)
        registry.register_calculator('elastic_ips', CostCalculatorFactory._elastic_ip_calculator)
        registry.register_calculator('vpc_endpoints', CostCalculatorFactory._vpc_endpoint_calculator)
        registry.register_calculator('s3_buckets', CostCalculatorFactory._s3_bucket_calculator)
        registry.register_calculator('route53_zones', CostCalculatorFactory._route53_calculator)
        registry.register_calculator('albs_nlbs', CostCalculatorFactory._elb_calculator)
        
        return registry
    
    @staticmethod
    def create_pricing_service(session: boto3.Session) -> PricingService:
        """Create and configure a pricing service"""
        pricing_service = PricingService()
        pricing_service.get_client(session)
        return pricing_service
    
    # Placeholder calculator methods (these would delegate to PricingService methods)
    @staticmethod
    def _ec2_instance_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_ec2_instance_cost(resource, region, days)
    
    @staticmethod
    def _ebs_volume_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_ebs_volume_cost(resource, region, days)
    
    @staticmethod
    def _nat_gateway_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_nat_gateway_cost(resource, region, days)
    
    @staticmethod
    def _elastic_ip_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_elastic_ip_cost(resource, region, days)
    
    @staticmethod
    def _vpc_endpoint_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_vpc_endpoint_cost(resource, region, days)
    
    @staticmethod
    def _s3_bucket_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_s3_bucket_cost(resource, region, days)
    
    @staticmethod
    def _route53_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_route53_cost(resource, region, days, 'hosted_zone')
    
    @staticmethod
    def _elb_calculator(resource, region, days, pricing_service):
        return pricing_service._calculate_elb_cost(resource, region, days, 'application')


def create_cost_calculation_system(session: boto3.Session) -> tuple[CostCalculatorRegistry, PricingService]:
    """Convenience function to create a complete cost calculation system"""
    registry = CostCalculatorFactory.create_registry()
    pricing_service = CostCalculatorFactory.create_pricing_service(session)
    registry.set_pricing_service(pricing_service)
    
    return registry, pricing_service