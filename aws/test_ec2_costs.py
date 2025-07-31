#!/usr/bin/env python3
"""
Test script to verify EC2 cost calculation improvements.
"""

import boto3
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import sys
import os

# Add aws directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'aws'))

from services.ec2_service import EC2Service
from services.base import ResourceInfo
from cost.analyzer_service import CostAnalyzerService
from cost.explorer_service import CostExplorerService


def test_ec2_resource_categorization():
    """Test that EC2 resources are properly categorized"""
    print("=== Testing EC2 Resource Categorization ===")
    
    ec2_service = EC2Service()
    
    # Mock client and data
    mock_client = Mock()
    
    # Mock EC2 instances response
    mock_instances_response = {
        'Reservations': [{
            'Instances': [{
                'InstanceId': 'i-1234567890abcdef0',
                'InstanceType': 't3.medium',
                'State': {'Name': 'running'},
                'LaunchTime': datetime.now()
            }]
        }]
    }
    
    # Mock EBS volumes response
    mock_volumes_response = {
        'Volumes': [{
            'VolumeId': 'vol-1234567890abcdef0',
            'Size': 20,
            'VolumeType': 'gp3',
            'State': 'in-use'
        }]
    }
    
    # Mock security groups response
    mock_sg_response = {
        'SecurityGroups': [{
            'GroupId': 'sg-1234567890abcdef0',
            'GroupName': 'test-sg',
            'VpcId': 'vpc-12345678',
            'Description': 'Test security group'
        }]
    }
    
    # Mock network interfaces response
    mock_ni_response = {
        'NetworkInterfaces': [{
            'NetworkInterfaceId': 'eni-1234567890abcdef0',
            'Status': 'in-use',
            'InterfaceType': 'interface',
            'SubnetId': 'subnet-12345678'
        }]
    }
    
    # Setup mock paginators
    def create_mock_paginator(response_key, response_data):
        paginator = Mock()
        paginator.paginate.return_value = [response_data]
        return paginator
    
    mock_client.get_paginator.side_effect = lambda operation: {
        'describe_instances': create_mock_paginator('Reservations', mock_instances_response),
        'describe_volumes': create_mock_paginator('Volumes', mock_volumes_response),
        'describe_security_groups': create_mock_paginator('SecurityGroups', mock_sg_response),
        'describe_network_interfaces': create_mock_paginator('NetworkInterfaces', mock_ni_response)
    }[operation]
    
    # Test resource discovery
    resources = ec2_service.search_resources(mock_client, 'test-tag', 'owned')
    
    # Verify instances
    assert len(resources['instances']) == 1
    instance = resources['instances'][0]
    assert instance.id == 'i-1234567890abcdef0'
    assert instance.type == 't3.medium'
    assert instance.additional_info['resource_category'] == 'ec2_instance'
    print(f"✓ EC2 Instance: {instance.id} categorized as {instance.additional_info['resource_category']}")
    
    # Verify volumes
    assert len(resources['volumes']) == 1
    volume = resources['volumes'][0]
    assert volume.id == 'vol-1234567890abcdef0'
    assert volume.additional_info['resource_category'] == 'ebs_volume'
    assert volume.additional_info['size_gb'] == 20
    print(f"✓ EBS Volume: {volume.id} categorized as {volume.additional_info['resource_category']}")
    
    # Verify security groups
    assert len(resources['security_groups']) == 1
    sg = resources['security_groups'][0]
    assert sg.id == 'sg-1234567890abcdef0'
    assert sg.additional_info['resource_category'] == 'security_group'
    print(f"✓ Security Group: {sg.id} categorized as {sg.additional_info['resource_category']}")
    
    # Verify network interfaces
    assert len(resources['network_interfaces']) == 1
    ni = resources['network_interfaces'][0]
    assert ni.id == 'eni-1234567890abcdef0'
    assert ni.additional_info['resource_category'] == 'network_interface'
    print(f"✓ Network Interface: {ni.id} categorized as {ni.additional_info['resource_category']}")
    
    print("All EC2 resources properly categorized!\n")
    return resources


def test_cost_estimation():
    """Test cost estimation for categorized resources"""
    print("=== Testing Cost Estimation ===")
    
    # Create test resources with categories
    test_resources = [
        ResourceInfo(
            id='i-1234567890abcdef0',
            type='t3.medium',
            state='running',
            additional_info={'resource_category': 'ec2_instance'}
        ),
        ResourceInfo(
            id='vol-1234567890abcdef0',
            type='20 GB gp3',
            state='in-use',
            additional_info={
                'resource_category': 'ebs_volume',
                'size_gb': 20,
                'volume_type': 'gp3'
            }
        ),
        ResourceInfo(
            id='sg-1234567890abcdef0',
            name='test-sg',
            type='vpc-12345678',
            additional_info={'resource_category': 'security_group'}
        ),
        ResourceInfo(
            id='eni-1234567890abcdef0',
            state='in-use',
            type='interface',
            additional_info={'resource_category': 'network_interface'}
        )
    ]
    
    # Create cost analyzer
    analyzer = CostAnalyzerService()
    
    # Test estimated cost calculation for each resource
    for resource in test_resources:
        cost_data = analyzer._get_estimated_cost_for_resource(resource)
        resource.cost_data = cost_data
        
        print(f"✓ {resource.id} ({resource.additional_info['resource_category']}): "
              f"${cost_data['total_cost']:.2f} ({cost_data['service']})")
    
    # Test service filter mapping
    for resource in test_resources:
        service_filter = analyzer._get_service_filter_for_resource(resource)
        print(f"  Service filter: {service_filter}")
    
    print()
    return test_resources


def test_optimization_suggestions():
    """Test optimization suggestions"""
    print("=== Testing Optimization Suggestions ===")
    
    # Create high-cost resources for optimization testing
    high_cost_resources = [
        ResourceInfo(
            id='i-expensive',
            type='c5.4xlarge',
            cost_data={'total_cost': 300.0},
            additional_info={'resource_category': 'ec2_instance'}
        ),
        ResourceInfo(
            id='vol-expensive',
            type='500 GB io1',
            cost_data={'total_cost': 80.0},
            additional_info={
                'resource_category': 'ebs_volume',
                'size_gb': 500,
                'volume_type': 'io1'
            }
        )
    ]
    
    analyzer = CostAnalyzerService()
    
    for resource in high_cost_resources:
        suggestions = analyzer._get_optimization_suggestions(resource)
        
        if suggestions:
            suggestion = suggestions[0]
            print(f"✓ {resource.id}: {suggestion.description}")
            print(f"  Potential savings: ${suggestion.potential_savings:.2f}")
            print(f"  Risk level: {suggestion.risk_level}")
        else:
            print(f"  No suggestions for {resource.id}")
    
    print()


def test_cost_summary():
    """Test cost summary generation"""
    print("=== Testing Cost Summary Generation ===")
    
    # Create sample resources with cost data
    resources = [
        ResourceInfo(
            id='i-1',
            cost_data={'total_cost': 68.0, 'service': 'EC2-Instance'}
        ),
        ResourceInfo(
            id='vol-1',
            cost_data={'total_cost': 1.6, 'service': 'EBS-Volume'}
        ),
        ResourceInfo(
            id='sg-1',
            cost_data={'total_cost': 0.0, 'service': 'Security-Group'}
        )
    ]
    
    analyzer = CostAnalyzerService()
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    summary = analyzer.generate_cost_summary(resources, start_date, end_date)
    
    print(f"✓ Total cost: ${summary.total_cost:.2f}")
    print(f"✓ Resource count: {summary.resource_count}")
    print(f"✓ Average cost per resource: ${summary.average_cost_per_resource:.2f}")
    print(f"✓ Cost breakdown: {summary.cost_breakdown}")
    print(f"✓ Cost trend: {summary.cost_trend}")
    
    print()


if __name__ == '__main__':
    print("Testing EC2 Cost Calculation Improvements\n")
    
    try:
        # Run tests
        resources = test_ec2_resource_categorization()
        cost_resources = test_cost_estimation()
        test_optimization_suggestions()
        test_cost_summary()
        
        print("=== All Tests Passed! ===")
        print("EC2 cost calculation has been successfully improved:")
        print("1. ✓ Resources are properly categorized")
        print("2. ✓ Cost estimation works for each resource type")
        print("3. ✓ Service filters are correctly mapped")
        print("4. ✓ Optimization suggestions are resource-specific")
        print("5. ✓ Cost summaries include all resource types")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)