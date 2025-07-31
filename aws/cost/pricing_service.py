"""
AWS Pricing API service for accurate resource cost calculation.
"""

from .base import CostService
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3
import json


class PricingService(CostService):
    """Service for interacting with AWS Pricing API for accurate cost calculation"""
    
    def __init__(self):
        super().__init__("Pricing")
        self.client = None
        self._price_cache = {}  # Cache pricing data to avoid repeated API calls
    
    def get_client(self, session: boto3.Session):
        """Get the Pricing client"""
        if not self.client:
            # Pricing API is only available in specific regions
            self.client = session.client('pricing', region_name='us-east-1')
        return self.client
    
    def get_ec2_instance_pricing(
        self,
        instance_type: str,
        region: str,
        operating_system: str = 'Linux'
    ) -> float:
        """Get hourly pricing for EC2 instance"""
        cache_key = f"ec2_{instance_type}_{region}_{operating_system}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            # Build filters for EC2 pricing
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
                {'Type': 'TERM_MATCH', 'Field': 'instanceType', 'Value': instance_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)},
                {'Type': 'TERM_MATCH', 'Field': 'operatingSystem', 'Value': operating_system},
                {'Type': 'TERM_MATCH', 'Field': 'tenancy', 'Value': 'Shared'},
                {'Type': 'TERM_MATCH', 'Field': 'preInstalledSw', 'Value': 'NA'},
                {'Type': 'TERM_MATCH', 'Field': 'capacitystatus', 'Value': 'Used'}
            ]
            
            response = self.client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=1
            )
            
            if response['PriceList']:
                price_data = json.loads(response['PriceList'][0])
                hourly_rate = self._extract_on_demand_hourly_rate(price_data)
                self._price_cache[cache_key] = hourly_rate
                return hourly_rate
            
        except Exception as e:
            print(f"Error getting EC2 pricing for {instance_type}: {e}")
        
        # Fallback to estimated pricing
        return self._get_fallback_ec2_price(instance_type)
    
    def get_ebs_volume_pricing(
        self,
        volume_type: str,
        region: str
    ) -> float:
        """Get monthly pricing per GB for EBS volume"""
        cache_key = f"ebs_{volume_type}_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            # Map volume types to AWS pricing volume types
            volume_type_mapping = {
                'gp2': 'General Purpose',
                'gp3': 'General Purpose',
                'io1': 'Provisioned IOPS',
                'io2': 'Provisioned IOPS',
                'sc1': 'Cold HDD',
                'st1': 'Throughput Optimized HDD'
            }
            
            aws_volume_type = volume_type_mapping.get(volume_type, 'General Purpose')
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'volumeType', 'Value': aws_volume_type},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
            ]
            
            response = self.client.get_products(
                ServiceCode='AmazonEC2',
                Filters=filters,
                MaxResults=1
            )
            
            if response['PriceList']:
                price_data = json.loads(response['PriceList'][0])
                monthly_rate = self._extract_on_demand_monthly_rate(price_data)
                self._price_cache[cache_key] = monthly_rate
                return monthly_rate
                
        except Exception as e:
            print(f"Error getting EBS pricing for {volume_type}: {e}")
        
        # Fallback to estimated pricing
        return self._get_fallback_ebs_price(volume_type)
    
    def get_elb_pricing(
        self,
        load_balancer_type: str,
        region: str
    ) -> float:
        """Get hourly pricing for Elastic Load Balancer"""
        cache_key = f"elb_{load_balancer_type}_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            # Map load balancer types
            if load_balancer_type.lower() in ['classic', 'clb']:
                service_code = 'AWSELB'
                product_family = 'Load Balancer'
            else:
                service_code = 'AWSELB'
                product_family = 'Load Balancer-Application'
            
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': service_code},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': product_family},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
            ]
            
            response = self.client.get_products(
                ServiceCode=service_code,
                Filters=filters,
                MaxResults=1
            )
            
            if response['PriceList']:
                price_data = json.loads(response['PriceList'][0])
                hourly_rate = self._extract_on_demand_hourly_rate(price_data)
                self._price_cache[cache_key] = hourly_rate
                return hourly_rate
                
        except Exception as e:
            print(f"Error getting ELB pricing for {load_balancer_type}: {e}")
        
        # Fallback to estimated pricing
        return 0.025  # ~$18/month for ALB/NLB, ~$22.5/month for CLB
    
    def calculate_resource_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate actual cost for a resource using AWS Pricing API"""
        if not hasattr(resource, 'additional_info') or not resource.additional_info:
            return self._get_default_cost_data(resource)
        
        resource_category = resource.additional_info.get('resource_category')
        
        if resource_category == 'ec2_instance':
            return self._calculate_ec2_instance_cost(resource, region, days)
        elif resource_category == 'ebs_volume':
            return self._calculate_ebs_volume_cost(resource, region, days)
        elif resource_category == 'security_group':
            return self._get_free_service_cost('Security-Group')
        elif resource_category == 'network_interface':
            return self._get_free_service_cost('Network-Interface')
        elif resource_category == 'classic_elb':
            return self._calculate_elb_cost(resource, region, days, 'classic')
        elif resource_category == 'alb_nlb':
            return self._calculate_elb_cost(resource, region, days, resource.type or 'application')
        else:
            return self._get_default_cost_data(resource)
    
    def _calculate_ec2_instance_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate EC2 instance cost"""
        instance_type = resource.type or 't3.micro'
        
        # Get hourly rate
        hourly_rate = self.get_ec2_instance_pricing(instance_type, region)
        
        # Calculate cost assuming instance is running (for cost estimation purposes)
        # This provides the total cost if all discovered resources were operational
        hours_in_period = days * 24
        total_cost = hourly_rate * hours_in_period
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {'EC2-Instance': total_cost},
            'service': 'EC2-Instance',
            'is_estimated': False,
            'hourly_rate': hourly_rate,
            'pricing_source': 'AWS Pricing API'
        }
    
    def _calculate_ebs_volume_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate EBS volume cost"""
        size_gb = resource.additional_info.get('size_gb', 20)
        volume_type = resource.additional_info.get('volume_type', 'gp2')
        
        # Get monthly rate per GB
        monthly_rate_per_gb = self.get_ebs_volume_pricing(volume_type, region)
        
        # Calculate cost for the period
        monthly_cost = monthly_rate_per_gb * size_gb
        period_cost = monthly_cost * (days / 30.0)
        
        return {
            'total_cost': period_cost,
            'service_breakdown': {'EBS-Volume': period_cost},
            'service': 'EBS-Volume',
            'is_estimated': False,
            'monthly_rate_per_gb': monthly_rate_per_gb,
            'size_gb': size_gb,
            'pricing_source': 'AWS Pricing API'
        }
    
    def _calculate_elb_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int,
        elb_type: str
    ) -> Dict[str, Any]:
        """Calculate ELB cost"""
        # Get hourly rate
        hourly_rate = self.get_elb_pricing(elb_type, region)
        
        # Calculate cost for the period
        hours_in_period = days * 24
        total_cost = hourly_rate * hours_in_period
        
        service_name = f"ELB-{elb_type.title()}"
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {service_name: total_cost},
            'service': service_name,
            'is_estimated': False,
            'hourly_rate': hourly_rate,
            'pricing_source': 'AWS Pricing API'
        }
    
    def _get_free_service_cost(self, service_name: str) -> Dict[str, Any]:
        """Return cost data for free services"""
        return {
            'total_cost': 0.0,
            'service_breakdown': {service_name: 0.0},
            'service': service_name,
            'is_estimated': False,
            'pricing_source': 'AWS Pricing (Free Service)'
        }
    
    def _get_default_cost_data(self, resource: 'ResourceInfo') -> Dict[str, Any]:
        """Return default cost data for unknown resources"""
        return {
            'total_cost': 0.0,
            'service_breakdown': {'Unknown': 0.0},
            'service': 'Unknown',
            'is_estimated': True,
            'pricing_source': 'Default (Unknown Resource Type)'
        }
    
    def _extract_on_demand_hourly_rate(self, price_data: Dict[str, Any]) -> float:
        """Extract on-demand hourly rate from pricing data"""
        try:
            terms = price_data.get('terms', {})
            on_demand = terms.get('OnDemand', {})
            
            for term_key, term_data in on_demand.items():
                price_dimensions = term_data.get('priceDimensions', {})
                for dim_key, dim_data in price_dimensions.items():
                    price_per_unit = dim_data.get('pricePerUnit', {})
                    usd_price = price_per_unit.get('USD', '0')
                    return float(usd_price)
        except (KeyError, ValueError, TypeError):
            pass
        
        return 0.0
    
    def _extract_on_demand_monthly_rate(self, price_data: Dict[str, Any]) -> float:
        """Extract on-demand monthly rate from pricing data"""
        try:
            terms = price_data.get('terms', {})
            on_demand = terms.get('OnDemand', {})
            
            for term_key, term_data in on_demand.items():
                price_dimensions = term_data.get('priceDimensions', {})
                for dim_key, dim_data in price_dimensions.items():
                    price_per_unit = dim_data.get('pricePerUnit', {})
                    usd_price = price_per_unit.get('USD', '0')
                    return float(usd_price)
        except (KeyError, ValueError, TypeError):
            pass
        
        return 0.0
    
    def _get_location_name(self, region: str) -> str:
        """Map AWS region to location name used in pricing API"""
        region_mapping = {
            'us-east-1': 'US East (N. Virginia)',
            'us-east-2': 'US East (Ohio)',
            'us-west-1': 'US West (N. California)',
            'us-west-2': 'US West (Oregon)',
            'eu-west-1': 'EU (Ireland)',
            'eu-central-1': 'EU (Frankfurt)',
            'ap-southeast-1': 'Asia Pacific (Singapore)',
            'ap-northeast-1': 'Asia Pacific (Tokyo)',
            # Add more regions as needed
        }
        
        return region_mapping.get(region, 'US East (N. Virginia)')
    
    def _get_fallback_ec2_price(self, instance_type: str) -> float:
        """Fallback EC2 pricing when API fails"""
        instance_type_lower = instance_type.lower()
        
        # Rough hourly pricing for common instance types
        fallback_prices = {
            't2.nano': 0.0058, 't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't2.large': 0.0928, 't3.nano': 0.0052, 't3.micro': 0.0104, 't3.small': 0.0208,
            't3.medium': 0.0416, 't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384, 'm5.4xlarge': 0.768,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34, 'c5.4xlarge': 0.68,
            'c5d.metal': 3.888,  # Very expensive bare metal instance
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504
        }
        
        # Find exact match first
        if instance_type_lower in fallback_prices:
            return fallback_prices[instance_type_lower]
        
        # Try partial matches
        for inst_type, price in fallback_prices.items():
            if inst_type in instance_type_lower:
                return price
        
        # Default price for unknown instance types
        return 0.096  # m5.large equivalent
    
    def _get_fallback_ebs_price(self, volume_type: str) -> float:
        """Fallback EBS pricing when API fails"""
        fallback_prices = {
            'gp2': 0.10, 'gp3': 0.08, 'io1': 0.125, 'io2': 0.125,
            'sc1': 0.025, 'st1': 0.045
        }
        
        return fallback_prices.get(volume_type, 0.10)