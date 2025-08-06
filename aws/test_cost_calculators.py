#!/usr/bin/env python3
"""
Test script for the enhanced cost calculators.

This script tests the new cost calculators with sample resource data
to ensure they work correctly with our ResourceGroups discovery.
"""

import sys
import os
import boto3
from cost.pricing_service import PricingService
from services.base import ResourceInfo

def create_test_resources():
    """Create test ResourceInfo objects for each new resource type"""
    test_resources = []
    
    # NAT Gateway
    test_resources.append(ResourceInfo(
        id='nat-0123456789abcdef0',
        name='test-nat-gateway',
        type='natgateway',
        region='us-east-2',
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 'ec2',
            'resource_type': 'natgateway',
            'arn': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-0123456789abcdef0'
        }
    ))
    
    # Elastic IP
    test_resources.append(ResourceInfo(
        id='eipalloc-0123456789abcdef0',
        name='test-elastic-ip',
        type='elastic-ip',
        region='us-east-2',
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 'ec2',
            'resource_type': 'elastic-ip',
            'arn': 'arn:aws:ec2:us-east-2:123456789012:elastic-ip/eipalloc-0123456789abcdef0'
        }
    ))
    
    # VPC Endpoint
    test_resources.append(ResourceInfo(
        id='vpce-0123456789abcdef0',
        name='test-vpc-endpoint',
        type='vpc-endpoint',
        region='us-east-2',
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 'ec2',
            'resource_type': 'vpc-endpoint',
            'endpoint_type': 'interface',
            'arn': 'arn:aws:ec2:us-east-2:123456789012:vpc-endpoint/vpce-0123456789abcdef0'
        }
    ))
    
    # S3 Bucket
    test_resources.append(ResourceInfo(
        id='test-openshift-bucket',
        name='test-openshift-bucket',
        type='bucket',
        region='us-east-2',
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 's3',
            'resource_type': 'test-openshift-bucket',
            'storage_class': 'Standard',
            'estimated_size_gb': 15,
            'arn': 'arn:aws:s3:::test-openshift-bucket'
        }
    ))
    
    # Route53 Hosted Zone
    test_resources.append(ResourceInfo(
        id='Z123456789ABCDEFGH',
        name='example.com',
        type='hostedzone',
        region='us-east-1',  # Route53 is global
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 'route53',
            'resource_type': 'hostedzone',
            'arn': 'arn:aws:route53:::hostedzone/Z123456789ABCDEFGH'
        }
    ))
    
    return test_resources

def test_cost_calculations():
    """Test cost calculations for all new resource types"""
    print("Testing enhanced cost calculators...")
    print("=" * 50)
    
    # Create pricing service
    pricing_service = PricingService()
    
    # Mock session (pricing service will handle API failures gracefully)
    session = boto3.Session()
    pricing_service.get_client(session)
    
    # Create test resources
    test_resources = create_test_resources()
    
    total_estimated_cost = 0.0
    region = 'us-east-2'
    days = 30
    
    print(f"Cost estimation for {days} days in region {region}:")
    print()
    
    for resource in test_resources:
        try:
            cost_data = pricing_service.calculate_resource_cost(resource, region, days)
            total_cost = cost_data.get('total_cost', 0.0)
            service = cost_data.get('service', 'Unknown')
            is_estimated = cost_data.get('is_estimated', False)
            pricing_source = cost_data.get('pricing_source', 'Unknown')
            
            total_estimated_cost += total_cost
            
            print(f"✓ {resource.id} ({service})")
            print(f"  Monthly Cost: ${total_cost:.2f}")
            print(f"  Estimated: {is_estimated}")
            print(f"  Source: {pricing_source}")
            
            # Show breakdown if available
            breakdown = cost_data.get('service_breakdown', {})
            if len(breakdown) > 1:
                print(f"  Breakdown:")
                for component, cost in breakdown.items():
                    print(f"    {component}: ${cost:.2f}")
            
            # Show additional details for some services
            if 'hourly_rate' in cost_data:
                print(f"  Hourly Rate: ${cost_data['hourly_rate']:.4f}")
            if 'data_processing_rate' in cost_data:
                print(f"  Data Processing: ${cost_data['data_processing_rate']:.4f}/GB")
            if 'estimated_gb_processed' in cost_data:
                print(f"  Est. Data Processed: {cost_data['estimated_gb_processed']:.1f} GB")
            
            print()
            
        except Exception as e:
            print(f"✗ Error calculating cost for {resource.id}: {e}")
            print()
    
    print("=" * 50)
    print(f"Total Estimated Monthly Cost: ${total_estimated_cost:.2f}")
    print()
    print("Cost Breakdown by Service Type:")
    
    # Group costs by service type
    service_costs = {}
    for resource in test_resources:
        try:
            cost_data = pricing_service.calculate_resource_cost(resource, region, days)
            service = cost_data.get('service', 'Unknown')
            cost = cost_data.get('total_cost', 0.0)
            
            if service not in service_costs:
                service_costs[service] = 0.0
            service_costs[service] += cost
            
        except Exception:
            continue
    
    for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True):
        percentage = (cost / total_estimated_cost * 100) if total_estimated_cost > 0 else 0
        print(f"  {service}: ${cost:.2f} ({percentage:.1f}%)")

def test_pricing_api_methods():
    """Test individual pricing API methods"""
    print("\nTesting individual pricing API methods...")
    print("=" * 50)
    
    pricing_service = PricingService()
    session = boto3.Session()
    pricing_service.get_client(session)
    
    region = 'us-east-2'
    
    # Test NAT Gateway pricing
    try:
        nat_pricing = pricing_service.get_nat_gateway_pricing(region)
        print(f"✓ NAT Gateway Pricing:")
        print(f"  Hourly: ${nat_pricing['hourly_rate']:.4f}")
        print(f"  Data Processing: ${nat_pricing['data_processing_rate']:.4f}/GB")
        print()
    except Exception as e:
        print(f"✗ NAT Gateway pricing error: {e}")
    
    # Test Elastic IP pricing
    try:
        eip_pricing = pricing_service.get_elastic_ip_pricing(region)
        print(f"✓ Elastic IP Pricing: ${eip_pricing:.4f}/hour")
        print()
    except Exception as e:
        print(f"✗ Elastic IP pricing error: {e}")
    
    # Test VPC Endpoint pricing
    try:
        vpce_pricing = pricing_service.get_vpc_endpoint_pricing('interface', region)
        print(f"✓ VPC Endpoint (Interface) Pricing:")
        print(f"  Hourly: ${vpce_pricing['hourly_rate']:.4f}")
        print(f"  Data Processing: ${vpce_pricing['data_processing_rate']:.4f}/GB")
        print()
    except Exception as e:
        print(f"✗ VPC Endpoint pricing error: {e}")
    
    # Test S3 pricing
    try:
        s3_pricing = pricing_service.get_s3_bucket_pricing('Standard', region)
        print(f"✓ S3 Standard Storage Pricing:")
        print(f"  Monthly per GB: ${s3_pricing['monthly_rate_per_gb']:.4f}")
        print(f"  Request cost per 1000: ${s3_pricing['request_cost_per_thousand']:.4f}")
        print()
    except Exception as e:
        print(f"✗ S3 pricing error: {e}")
    
    # Test Route53 pricing
    try:
        route53_zone_pricing = pricing_service.get_route53_pricing('hosted_zone')
        print(f"✓ Route53 Hosted Zone Pricing: ${route53_zone_pricing:.2f}/month")
        print()
    except Exception as e:
        print(f"✗ Route53 pricing error: {e}")

if __name__ == '__main__':
    print("Enhanced Cost Calculator Test")
    print("=" * 50)
    print("This script tests the new cost calculators for:")
    print("- NAT Gateways")
    print("- Elastic IPs") 
    print("- VPC Endpoints")
    print("- S3 Buckets")
    print("- Route53 Hosted Zones")
    print()
    
    try:
        test_cost_calculations()
        test_pricing_api_methods()
        print("✓ All cost calculator tests completed successfully!")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        sys.exit(1)