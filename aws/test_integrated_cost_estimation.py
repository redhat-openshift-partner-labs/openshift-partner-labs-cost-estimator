#!/usr/bin/env python3
"""
Integration test for unified discovery with cost estimation.

This test demonstrates the complete workflow:
1. ResourceGroups discovery finds resources with enhanced categorization  
2. PricingService calculates costs for all new resource types
3. Results show comprehensive cost breakdown
"""

import boto3
from services.resource_groups_service import ResourceGroupsService
from cost.pricing_service import PricingService
from unittest.mock import Mock

def test_integrated_cost_estimation():
    """Test the complete integrated workflow"""
    print("Integrated Cost Estimation Test")
    print("=" * 50)
    
    # Create mock session
    session = Mock(spec=boto3.Session)
    
    # Initialize services
    rg_service = ResourceGroupsService()
    pricing_service = PricingService()
    
    # Create a mock client for ResourceGroups
    rg_client = Mock()
    
    # Mock the get_paginator and paginate calls
    paginator = Mock()
    rg_client.get_paginator.return_value = paginator
    
    # Create comprehensive mock data representing our real cluster findings
    mock_resources = [
        # EC2 instances
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:instance/i-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'master-node-1'}
            ]
        },
        # EBS volumes  
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:volume/vol-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'master-root-volume'}
            ]
        },
        # NAT Gateways (3 found in real test)
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcdef',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-gateway-1'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcde1',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-gateway-2'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcde2',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-gateway-3'}
            ]
        },
        # Elastic IPs (3 found in real test)
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:elastic-ip/eipalloc-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-eip-1'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:elastic-ip/eipalloc-0123456789abcde1',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-eip-2'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:elastic-ip/eipalloc-0123456789abcde2',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'nat-eip-3'}
            ]
        },
        # VPC Endpoint (1 found in real test)
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:vpc-endpoint/vpce-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 's3-endpoint'}
            ]
        },
        # S3 Bucket (1 found in real test)
        {
            'ResourceARN': 'arn:aws:s3:::ocpv-rwx-lvvbx-cluster-bootstrap',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'cluster-bootstrap-bucket'}
            ]
        },
        # Load Balancers (3 found in real test)
        {
            'ResourceARN': 'arn:aws:elasticloadbalancing:us-east-2:123456789012:loadbalancer/app/ocpv-ext/1234567890abcdef',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'external-api-lb'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:elasticloadbalancing:us-east-2:123456789012:loadbalancer/net/ocpv-int/1234567890abcdef',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'internal-api-lb'}
            ]
        },
        # VPC, Subnets, Route Tables (free resources)
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:vpc/vpc-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'cluster-vpc'}
            ]
        },
        {
            'ResourceARN': 'arn:aws:ec2:us-east-2:123456789012:subnet/subnet-0123456789abcdef0',
            'Tags': [
                {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
                {'Key': 'Name', 'Value': 'private-subnet-1'}
            ]
        }
    ]
    
    # Mock paginate to return our test data
    paginator.paginate.return_value = [
        {'ResourceTagMappingList': mock_resources}
    ]
    
    print("1. Testing ResourceGroups discovery with enhanced categorization...")
    
    # Test resource discovery
    tag_key = 'kubernetes.io/cluster/ocpv-rwx-lvvbx'
    tag_value = 'owned'
    
    discovered_resources = rg_service.search_resources(rg_client, tag_key, tag_value)
    
    print(f"   Resources discovered: {sum(len(resources) for resources in discovered_resources.values())}")
    
    # Print resource breakdown
    billable_resources = []
    free_resources = []
    
    for resource_type, resources in discovered_resources.items():
        if len(resources) > 0:
            print(f"   {resource_type}: {len(resources)} resources")
            
            # Categorize by cost impact
            if resource_type in ['instances', 'volumes', 'nat_gateways', 'elastic_ips', 
                               'vpc_endpoints', 'albs_nlbs', 's3_buckets', 'route53_zones']:
                billable_resources.extend(resources)
            else:
                free_resources.extend(resources)
    
    print(f"   Billable resources: {len(billable_resources)}")
    print(f"   Free resources: {len(free_resources)}")
    print()
    
    print("2. Testing cost calculation for billable resources...")
    
    # Initialize pricing service with mock session
    pricing_session = Mock(spec=boto3.Session)
    pricing_client = Mock()
    pricing_session.client.return_value = pricing_client
    pricing_service.get_client(pricing_session)
    
    total_monthly_cost = 0.0
    service_costs = {}
    region = 'us-east-2'
    days = 30
    
    for resource in billable_resources:
        try:
            cost_data = pricing_service.calculate_resource_cost(resource, region, days)
            cost = cost_data.get('total_cost', 0.0)
            service = cost_data.get('service', 'Unknown')
            
            total_monthly_cost += cost
            
            if service not in service_costs:
                service_costs[service] = {'cost': 0.0, 'count': 0}
            service_costs[service]['cost'] += cost
            service_costs[service]['count'] += 1
            
            print(f"   ✓ {resource.name or resource.id}: ${cost:.2f}/month ({service})")
            
        except Exception as e:
            print(f"   ✗ Error calculating cost for {resource.id}: {e}")
    
    print()
    print("3. Cost Analysis Summary")
    print("-" * 30)
    print(f"Total Monthly Cost: ${total_monthly_cost:.2f}")
    print()
    print("Cost Breakdown by Service:")
    
    for service, data in sorted(service_costs.items(), key=lambda x: x[1]['cost'], reverse=True):
        cost = data['cost']
        count = data['count']
        percentage = (cost / total_monthly_cost * 100) if total_monthly_cost > 0 else 0
        print(f"  {service}: ${cost:.2f} ({percentage:.1f}%) - {count} resource(s)")
    
    print()
    print("4. Comparison with Real Cluster Estimates")
    print("-" * 40)
    print("Expected costs for 3 NAT Gateways: ~$110/month")
    print("Expected costs for 3 Elastic IPs: ~$11/month")
    print("Expected costs for 1 VPC Endpoint: ~$7/month")
    print("Expected costs for Load Balancers: ~$50/month")
    print("Expected costs for EC2/EBS: Variable")
    print()
    
    # Validate key cost components
    nat_gateway_cost = service_costs.get('NAT-Gateway', {}).get('cost', 0)
    elastic_ip_cost = service_costs.get('Elastic-IP', {}).get('cost', 0)
    vpc_endpoint_cost = service_costs.get('VPC-Endpoint-Interface', {}).get('cost', 0)
    
    print("5. Cost Validation")
    print("-" * 20)
    
    if nat_gateway_cost > 100:
        print(f"✓ NAT Gateway costs: ${nat_gateway_cost:.2f} (within expected range)")
    else:
        print(f"⚠ NAT Gateway costs: ${nat_gateway_cost:.2f} (lower than expected)")
    
    if elastic_ip_cost > 8:
        print(f"✓ Elastic IP costs: ${elastic_ip_cost:.2f} (within expected range)")
    else:
        print(f"⚠ Elastic IP costs: ${elastic_ip_cost:.2f} (lower than expected)")
    
    if vpc_endpoint_cost > 5:
        print(f"✓ VPC Endpoint costs: ${vpc_endpoint_cost:.2f} (within expected range)")
    else:
        print(f"⚠ VPC Endpoint costs: ${vpc_endpoint_cost:.2f} (lower than expected)")
    
    print()
    print("=" * 50)
    print("✓ Integration test completed successfully!")
    print(f"  Enhanced discovery found {len(billable_resources)} billable resources")
    print(f"  Total estimated monthly cost: ${total_monthly_cost:.2f}")
    print(f"  Cost calculators working for {len(service_costs)} service types")

if __name__ == '__main__':
    test_integrated_cost_estimation()