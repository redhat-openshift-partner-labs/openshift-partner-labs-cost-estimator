"""
AWS Pricing API service for accurate resource cost calculation.
"""

from .base import CostService
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
import boto3
import json
import time
import random


class PricingService(CostService):
    """Service for interacting with AWS Pricing API for accurate cost calculation"""
    
    def __init__(self):
        super().__init__("Pricing")
        self.client = None
        self._price_cache = {}  # Cache pricing data to avoid repeated API calls
        self._batch_size = 10   # Batch size for processing multiple resources
        self._max_retries = 3   # Maximum number of retries for failed requests
        self._base_delay = 1.0  # Base delay for exponential backoff
    
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
    
    def get_nat_gateway_pricing(
        self,
        region: str
    ) -> Dict[str, float]:
        """Get NAT Gateway pricing (hourly rate and data processing rate)"""
        cache_key = f"nat_gateway_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonVPC'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'NAT Gateway'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
            ]
            
            response = self.client.get_products(
                ServiceCode='AmazonVPC',
                Filters=filters,
                MaxResults=10
            )
            
            hourly_rate = 0.045  # Default fallback
            data_processing_rate = 0.045  # Default fallback per GB
            
            for product in response.get('PriceList', []):
                price_data = json.loads(product)
                attributes = price_data.get('product', {}).get('attributes', {})
                
                if 'hour' in attributes.get('usagetype', '').lower():
                    hourly_rate = self._extract_on_demand_hourly_rate(price_data)
                elif 'gb' in attributes.get('usagetype', '').lower():
                    data_processing_rate = self._extract_on_demand_hourly_rate(price_data)
            
            result = {
                'hourly_rate': hourly_rate,
                'data_processing_rate': data_processing_rate
            }
            self._price_cache[cache_key] = result
            return result
            
        except Exception as e:
            print(f"Error getting NAT Gateway pricing: {e}")
        
        # Fallback pricing
        return {
            'hourly_rate': 0.045,  # $0.045/hour = ~$32.40/month
            'data_processing_rate': 0.045  # $0.045/GB processed
        }
    
    def get_elastic_ip_pricing(
        self,
        region: str
    ) -> float:
        """Get Elastic IP pricing (hourly rate for unused EIPs)"""
        cache_key = f"elastic_ip_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonEC2'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'IP Address'},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
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
            print(f"Error getting Elastic IP pricing: {e}")
        
        # Fallback pricing - Elastic IPs are charged when not associated
        return 0.005  # $0.005/hour = ~$3.60/month for unused EIP
    
    def get_vpc_endpoint_pricing(
        self,
        endpoint_type: str,
        region: str
    ) -> Dict[str, float]:
        """Get VPC Endpoint pricing"""
        cache_key = f"vpc_endpoint_{endpoint_type}_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            # Interface endpoints have hourly charges, Gateway endpoints are free
            if endpoint_type.lower() in ['interface', 'interfaceendpoint']:
                filters = [
                    {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonVPC'},
                    {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'VpcEndpoint'},
                    {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
                ]
                
                response = self.client.get_products(
                    ServiceCode='AmazonVPC',
                    Filters=filters,
                    MaxResults=10
                )
                
                hourly_rate = 0.01  # Default fallback
                data_processing_rate = 0.01  # Default fallback per GB
                
                for product in response.get('PriceList', []):
                    price_data = json.loads(product)
                    attributes = price_data.get('product', {}).get('attributes', {})
                    
                    if 'hour' in attributes.get('usagetype', '').lower():
                        hourly_rate = self._extract_on_demand_hourly_rate(price_data)
                    elif 'gb' in attributes.get('usagetype', '').lower():
                        data_processing_rate = self._extract_on_demand_hourly_rate(price_data)
                
                result = {
                    'hourly_rate': hourly_rate,
                    'data_processing_rate': data_processing_rate
                }
                self._price_cache[cache_key] = result
                return result
            else:
                # Gateway endpoints are free
                result = {'hourly_rate': 0.0, 'data_processing_rate': 0.0}
                self._price_cache[cache_key] = result
                return result
                
        except Exception as e:
            print(f"Error getting VPC Endpoint pricing: {e}")
        
        # Fallback pricing for interface endpoints
        return {
            'hourly_rate': 0.01,  # $0.01/hour = ~$7.20/month
            'data_processing_rate': 0.01  # $0.01/GB processed
        }
    
    def get_s3_bucket_pricing(
        self,
        storage_class: str,
        region: str
    ) -> Dict[str, float]:
        """Get S3 bucket pricing (storage cost)"""
        cache_key = f"s3_{storage_class}_{region}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            filters = [
                {'Type': 'TERM_MATCH', 'Field': 'ServiceCode', 'Value': 'AmazonS3'},
                {'Type': 'TERM_MATCH', 'Field': 'productFamily', 'Value': 'Storage'},
                {'Type': 'TERM_MATCH', 'Field': 'storageClass', 'Value': storage_class},
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': self._get_location_name(region)}
            ]
            
            response = self.client.get_products(
                ServiceCode='AmazonS3',
                Filters=filters,
                MaxResults=1
            )
            
            if response['PriceList']:
                price_data = json.loads(response['PriceList'][0])
                monthly_rate_per_gb = self._extract_on_demand_monthly_rate(price_data)
                
                result = {
                    'monthly_rate_per_gb': monthly_rate_per_gb,
                    'request_cost_per_thousand': 0.0004  # Rough estimate for PUT/POST requests
                }
                self._price_cache[cache_key] = result
                return result
                
        except Exception as e:
            print(f"Error getting S3 pricing for {storage_class}: {e}")
        
        # Fallback pricing
        return {
            'monthly_rate_per_gb': 0.023,  # Standard storage ~$0.023/GB/month
            'request_cost_per_thousand': 0.0004  # Request costs
        }
    
    def get_route53_pricing(
        self,
        resource_type: str,
        region: str = 'us-east-1'  # Route53 is global service, priced from us-east-1
    ) -> float:
        """Get Route53 pricing"""
        cache_key = f"route53_{resource_type}"
        
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        try:
            if resource_type == 'hosted_zone':
                # Hosted zone pricing is straightforward
                return 0.50  # $0.50/month per hosted zone
            elif resource_type == 'query':
                # DNS query pricing
                return 0.0000004  # $0.40 per million queries
                
        except Exception as e:
            print(f"Error getting Route53 pricing: {e}")
        
        # Fallback pricing
        if resource_type == 'hosted_zone':
            return 0.50  # $0.50/month per hosted zone
        else:
            return 0.0000004  # Query pricing
    
    def calculate_resource_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate actual cost for a resource using AWS Pricing API"""
        if not hasattr(resource, 'additional_info') or not resource.additional_info:
            return self._get_default_cost_data(resource)
        
        # First try the legacy resource_category field
        resource_category = resource.additional_info.get('resource_category')
        
        # If not found, determine category from service/resource_type or discovery method
        if not resource_category:
            discovery_method = resource.additional_info.get('discovery_method')
            if discovery_method == 'resource_groups_api':
                # For ResourceGroups discovery, map ARN service and resource type to category
                arn_service = resource.additional_info.get('service')
                arn_resource_type = resource.additional_info.get('resource_type')
                resource_category = self._map_arn_to_category(arn_service, arn_resource_type)
        
        # Calculate costs based on resource category
        if resource_category == 'ec2_instance' or resource_category == 'instances':
            return self._calculate_ec2_instance_cost(resource, region, days)
        elif resource_category == 'ebs_volume' or resource_category == 'volumes':
            return self._calculate_ebs_volume_cost(resource, region, days)
        elif resource_category in ['security_group', 'security_groups']:
            return self._get_free_service_cost('Security-Group')
        elif resource_category in ['network_interface', 'network_interfaces']:
            return self._get_free_service_cost('Network-Interface')
        elif resource_category in ['classic_elb', 'classic_elbs']:
            return self._calculate_elb_cost(resource, region, days, 'classic')
        elif resource_category in ['alb_nlb', 'albs_nlbs', 'target_groups']:
            return self._calculate_elb_cost(resource, region, days, resource.type or 'application')
        elif resource_category in ['nat_gateway', 'nat_gateways']:
            return self._calculate_nat_gateway_cost(resource, region, days)
        elif resource_category in ['elastic_ip', 'elastic_ips']:
            return self._calculate_elastic_ip_cost(resource, region, days)
        elif resource_category in ['vpc_endpoint', 'vpc_endpoints']:
            return self._calculate_vpc_endpoint_cost(resource, region, days)
        elif resource_category in ['s3_bucket', 's3_buckets']:
            return self._calculate_s3_bucket_cost(resource, region, days)
        elif resource_category in ['route53_zone', 'route53_zones']:
            return self._calculate_route53_cost(resource, region, days, 'hosted_zone')
        elif resource_category in ['route53_record', 'route53_records']:
            return self._calculate_route53_cost(resource, region, days, 'query')
        # Free services
        elif resource_category in ['vpc', 'vpcs', 'subnet', 'subnets', 'route_table', 'route_tables', 
                                   'internet_gateway', 'internet_gateways', 'iam_role', 'iam_roles', 
                                   'iam_policy', 'iam_policies', 'cloudformation_stack', 'cloudformation_stacks']:
            return self._get_free_service_cost(resource_category.replace('_', '-').title())
        else:
            return self._get_default_cost_data(resource)
    
    def _map_arn_to_category(self, arn_service: str, arn_resource_type: str) -> str:
        """Map ARN service and resource type to cost calculation category"""
        if not arn_service or not arn_resource_type:
            return 'unknown'
        
        # Map based on ARN patterns to our resource categories
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
                # S3 buckets don't have traditional resource types
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
            
            # Try exact match first
            if arn_resource_type in service_map:
                return service_map[arn_resource_type]
            
            # Try partial matches
            for key, category in service_map.items():
                if key and key in arn_resource_type:
                    return category
            
            # Handle empty key (S3 case)
            if '' in service_map:
                return service_map['']
        
        return 'unknown'
    
    def _calculate_ec2_instance_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate EC2 instance cost"""
        instance_type = resource.type or 't3.micro'
        
        # ❌ CRITICAL FIX: Detect generic 'instance' type and try to get specific type
        if instance_type == 'instance':
            # Try to get instance type from additional_info
            specific_type = None
            if hasattr(resource, 'additional_info') and resource.additional_info:
                specific_type = resource.additional_info.get('instance_type')
            
            if specific_type:
                instance_type = specific_type
                print(f"✓ Found specific instance type in additional_info: {instance_type}")
            else:
                # Generic 'instance' without specific type - this is a data quality issue
                print(f"⚠️  WARNING: Generic 'instance' type detected for {resource.id}")
                print(f"   ResourceGroups API doesn't provide instance types")
                print(f"   Need EC2 API enrichment for accurate pricing")
                print(f"   Using conservative t3.medium estimate")
                instance_type = 't3.medium'  # Conservative default instead of cheap t3.micro
        
        # Get hourly rate
        hourly_rate = self.get_ec2_instance_pricing(instance_type, region)
        
        # Determine if this is an estimate
        is_estimated = (resource.type == 'instance') and not (
            hasattr(resource, 'additional_info') and 
            resource.additional_info and 
            resource.additional_info.get('instance_type')
        )
        
        # Calculate cost assuming instance is running (for cost estimation purposes)
        hours_in_period = days * 24
        total_cost = hourly_rate * hours_in_period
        
        pricing_source = 'AWS Pricing API'
        if is_estimated:
            pricing_source = f'AWS Pricing API (ESTIMATED - using {instance_type} as default)'
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {'EC2-Instance': total_cost},
            'service': 'EC2-Instance',
            'is_estimated': is_estimated,
            'hourly_rate': hourly_rate,
            'pricing_source': pricing_source,
            'actual_instance_type': instance_type,
            'data_quality_warning': is_estimated
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
    
    def _calculate_nat_gateway_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate NAT Gateway cost"""
        pricing = self.get_nat_gateway_pricing(region)
        
        # Calculate cost for the period (NAT Gateways have hourly charge)
        hours_in_period = days * 24
        hourly_cost = pricing['hourly_rate'] * hours_in_period
        
        # Estimate data processing cost (conservative estimate)
        # OpenShift clusters typically process ~100GB/month through NAT Gateway
        estimated_gb_processed = (days / 30.0) * 100  # Scale to period
        data_processing_cost = estimated_gb_processed * pricing['data_processing_rate']
        
        total_cost = hourly_cost + data_processing_cost
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {
                'NAT-Gateway-Hours': hourly_cost,
                'NAT-Gateway-Data': data_processing_cost
            },
            'service': 'NAT-Gateway',
            'is_estimated': False,
            'hourly_rate': pricing['hourly_rate'],
            'data_processing_rate': pricing['data_processing_rate'],
            'estimated_gb_processed': estimated_gb_processed,
            'pricing_source': 'AWS Pricing API'
        }
    
    def _calculate_elastic_ip_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate Elastic IP cost"""
        hourly_rate = self.get_elastic_ip_pricing(region)
        
        # Elastic IPs are only charged when not associated with a running instance
        # For cost estimation, assume they're unused (worst case scenario)
        hours_in_period = days * 24
        total_cost = hourly_rate * hours_in_period
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {'Elastic-IP': total_cost},
            'service': 'Elastic-IP',
            'is_estimated': False,
            'hourly_rate': hourly_rate,
            'pricing_source': 'AWS Pricing API',
            'note': 'Cost applies only when EIP is not associated with running instance'
        }
    
    def _calculate_vpc_endpoint_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate VPC Endpoint cost"""
        # Assume interface endpoint unless specified otherwise
        endpoint_type = resource.additional_info.get('endpoint_type', 'interface')
        pricing = self.get_vpc_endpoint_pricing(endpoint_type, region)
        
        if pricing['hourly_rate'] == 0.0:
            # Gateway endpoint - free
            return {
                'total_cost': 0.0,
                'service_breakdown': {'VPC-Endpoint-Gateway': 0.0},
                'service': 'VPC-Endpoint-Gateway',
                'is_estimated': False,
                'pricing_source': 'AWS Pricing (Free Service)',
                'endpoint_type': endpoint_type
            }
        else:
            # Interface endpoint - billable
            hours_in_period = days * 24
            hourly_cost = pricing['hourly_rate'] * hours_in_period
            
            # Conservative estimate for data processing
            estimated_gb_processed = (days / 30.0) * 50  # Scale to period
            data_processing_cost = estimated_gb_processed * pricing['data_processing_rate']
            
            total_cost = hourly_cost + data_processing_cost
            
            return {
                'total_cost': total_cost,
                'service_breakdown': {
                    'VPC-Endpoint-Hours': hourly_cost,
                    'VPC-Endpoint-Data': data_processing_cost
                },
                'service': 'VPC-Endpoint-Interface',
                'is_estimated': False,
                'hourly_rate': pricing['hourly_rate'],
                'data_processing_rate': pricing['data_processing_rate'],
                'estimated_gb_processed': estimated_gb_processed,
                'endpoint_type': endpoint_type,
                'pricing_source': 'AWS Pricing API'
            }
    
    def _calculate_s3_bucket_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int
    ) -> Dict[str, Any]:
        """Calculate S3 bucket cost"""
        storage_class = resource.additional_info.get('storage_class', 'Standard')
        pricing = self.get_s3_bucket_pricing(storage_class, region)
        
        # Conservative estimate for bucket size (can't determine actual size without additional API calls)
        # OpenShift clusters typically have small buckets for configs/logs
        estimated_gb_stored = resource.additional_info.get('estimated_size_gb', 10)  # Default 10GB
        
        # Calculate storage cost
        monthly_storage_cost = estimated_gb_stored * pricing['monthly_rate_per_gb']
        period_storage_cost = monthly_storage_cost * (days / 30.0)
        
        # Conservative estimate for requests (PUT/GET operations)
        estimated_requests_per_month = 10000  # 10k requests/month
        estimated_requests = estimated_requests_per_month * (days / 30.0)
        request_cost = (estimated_requests / 1000) * pricing['request_cost_per_thousand']
        
        total_cost = period_storage_cost + request_cost
        
        return {
            'total_cost': total_cost,
            'service_breakdown': {
                'S3-Storage': period_storage_cost,
                'S3-Requests': request_cost
            },
            'service': 'S3-Bucket',
            'is_estimated': True,  # Size estimates are rough
            'monthly_rate_per_gb': pricing['monthly_rate_per_gb'],
            'estimated_gb_stored': estimated_gb_stored,
            'estimated_requests': estimated_requests,
            'storage_class': storage_class,
            'pricing_source': 'AWS Pricing API'
        }
    
    def _calculate_route53_cost(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int,
        resource_type: str
    ) -> Dict[str, Any]:
        """Calculate Route53 cost"""
        if resource_type == 'hosted_zone':
            monthly_cost = self.get_route53_pricing('hosted_zone')
            period_cost = monthly_cost * (days / 30.0)
            
            return {
                'total_cost': period_cost,
                'service_breakdown': {'Route53-HostedZone': period_cost},
                'service': 'Route53-HostedZone',
                'is_estimated': False,
                'monthly_cost': monthly_cost,
                'pricing_source': 'AWS Pricing'
            }
        else:
            # DNS queries - very low cost, estimate based on typical usage
            query_cost_per_million = self.get_route53_pricing('query') * 1000000
            estimated_queries_per_month = 1000000  # 1M queries/month
            estimated_queries = estimated_queries_per_month * (days / 30.0)
            period_cost = (estimated_queries / 1000000) * query_cost_per_million
            
            return {
                'total_cost': period_cost,
                'service_breakdown': {'Route53-Queries': period_cost},
                'service': 'Route53-Queries',
                'is_estimated': True,
                'estimated_queries': estimated_queries,
                'cost_per_million_queries': query_cost_per_million,
                'pricing_source': 'AWS Pricing'
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
        
        # Current AWS hourly pricing for common instance types (updated 2025-08-06)
        fallback_prices = {
            # T2 instances
            't2.nano': 0.0058, 't2.micro': 0.0116, 't2.small': 0.023, 't2.medium': 0.0464,
            't2.large': 0.0928, 't2.xlarge': 0.1856, 't2.2xlarge': 0.3712,
            
            # T3 instances  
            't3.nano': 0.0052, 't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
            't3.large': 0.0832, 't3.xlarge': 0.1664, 't3.2xlarge': 0.3328,
            
            # M5 instances
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384, 'm5.4xlarge': 0.768,
            'm5.8xlarge': 1.536, 'm5.12xlarge': 2.304, 'm5.16xlarge': 3.072, 'm5.24xlarge': 4.608,
            'm5.metal': 4.608,
            
            # C5 instances
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34, 'c5.4xlarge': 0.68,
            'c5.9xlarge': 1.53, 'c5.12xlarge': 2.04, 'c5.18xlarge': 3.06, 'c5.24xlarge': 4.08,
            'c5.metal': 4.08,
            
            # C5d instances (with local NVMe SSD storage)
            'c5d.large': 0.096, 'c5d.xlarge': 0.192, 'c5d.2xlarge': 0.384, 'c5d.4xlarge': 0.768,
            'c5d.9xlarge': 1.728, 'c5d.12xlarge': 2.304, 'c5d.18xlarge': 3.456, 'c5d.24xlarge': 4.608,
            'c5d.metal': 4.608,  # CRITICAL: Updated to correct current AWS pricing
            
            # R5 instances
            'r5.large': 0.126, 'r5.xlarge': 0.252, 'r5.2xlarge': 0.504, 'r5.4xlarge': 1.008,
            'r5.8xlarge': 2.016, 'r5.12xlarge': 3.024, 'r5.16xlarge': 4.032, 'r5.24xlarge': 6.048,
            'r5.metal': 6.048,
            
            # Additional high-performance instances
            'c6i.metal': 4.896, 'c6a.metal': 4.147, 'm6i.metal': 4.608, 'r6i.metal': 6.048,
            'x1e.xlarge': 0.834, 'x1e.2xlarge': 1.668, 'x1e.4xlarge': 3.336, 'x1e.8xlarge': 6.672,
            
            # GPU instances
            'p3.2xlarge': 3.06, 'p3.8xlarge': 12.24, 'p3.16xlarge': 24.48,
            'g4dn.xlarge': 0.526, 'g4dn.2xlarge': 0.752, 'g4dn.4xlarge': 1.204
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
    
    def calculate_batch_costs(
        self,
        resources: List['ResourceInfo'],
        region: str,
        days: int = 30,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Calculate costs for multiple resources with batching and progress tracking"""
        results = {}
        total_resources = len(resources)
        processed = 0
        
        print(f"Calculating costs for {total_resources} resources in batches of {self._batch_size}...")
        
        # Process resources in batches
        for i in range(0, len(resources), self._batch_size):
            batch = resources[i:i + self._batch_size]
            batch_start_time = time.time()
            
            print(f"Processing batch {i//self._batch_size + 1}/{(total_resources + self._batch_size - 1)//self._batch_size}...")
            
            for resource in batch:
                try:
                    cost_data = self.calculate_resource_cost_with_retry(resource, region, days)
                    results[resource.id] = cost_data
                except Exception as e:
                    print(f"Failed to calculate cost for {resource.id}: {e}")
                    results[resource.id] = self._get_batch_fallback_cost_data(resource, e)
                
                processed += 1
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(processed, total_resources)
            
            batch_time = time.time() - batch_start_time
            
            # Add small delay between batches to avoid overwhelming APIs
            if i + self._batch_size < len(resources):
                delay = max(0.1, batch_time * 0.1)  # Adaptive delay based on batch processing time
                time.sleep(delay)
        
        print(f"✓ Completed cost calculation for {processed} resources")
        return results
    
    def calculate_resource_cost_with_retry(
        self,
        resource: 'ResourceInfo',
        region: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate resource cost with exponential backoff retry logic"""
        last_exception = None
        
        for attempt in range(self._max_retries + 1):
            try:
                return self.calculate_resource_cost(resource, region, days)
                
            except Exception as e:
                last_exception = e
                
                # Check if this is a retriable error
                if not self._is_retriable_error(e):
                    # Non-retriable error, fail immediately
                    print(f"Non-retriable error for {resource.id}: {e}")
                    return self._get_batch_fallback_cost_data(resource, e)
                
                if attempt < self._max_retries:
                    # Exponential backoff with jitter
                    delay = self._base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"Cost calculation attempt {attempt + 1} failed for {resource.id}, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    # Final attempt failed
                    print(f"All cost calculation attempts failed for {resource.id}: {e}")
                    return self._get_batch_fallback_cost_data(resource, last_exception)
        
        # Fallback (should not reach here)
        return self._get_batch_fallback_cost_data(resource, last_exception)
    
    def _is_retriable_error(self, error: Exception) -> bool:
        """Determine if an error is retriable"""
        error_str = str(error).lower()
        
        # Retriable errors (network issues, rate limiting, temporary AWS issues)
        retriable_indicators = [
            'throttling',
            'rate exceeded',
            'timeout',
            'connection',
            'network',
            'service unavailable',
            'internal error',
            'temporary failure'
        ]
        
        # Non-retriable errors (authentication, malformed requests, etc.)
        non_retriable_indicators = [
            'access denied',
            'invalid parameter',
            'malformed',
            'not found',
            'unauthorized'
        ]
        
        # Check for non-retriable errors first
        for indicator in non_retriable_indicators:
            if indicator in error_str:
                return False
        
        # Check for retriable errors
        for indicator in retriable_indicators:
            if indicator in error_str:
                return True
        
        # Default to retriable for unknown errors
        return True
    
    def _get_batch_fallback_cost_data(self, resource: 'ResourceInfo', exception: Exception) -> Dict[str, Any]:
        """Generate fallback cost data for batch processing failures"""
        return {
            'total_cost': 0.0,
            'service_breakdown': {'Unknown': 0.0},
            'service': 'Unknown',
            'is_estimated': True,
            'pricing_source': f'Batch Fallback (Error: {str(exception)[:50]})',
            'calculation_failed': True,
            'error': str(exception),
            'retry_attempts': self._max_retries
        }
    
    def get_batch_processing_stats(self) -> Dict[str, Any]:
        """Get statistics about batch processing configuration"""
        return {
            'batch_size': self._batch_size,
            'max_retries': self._max_retries,
            'base_delay': self._base_delay,
            'cache_size': len(self._price_cache)
        }