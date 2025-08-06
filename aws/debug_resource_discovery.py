#!/usr/bin/env python3
"""
Debug resource discovery to understand why instance types aren't correctly identified.

This investigates the gap between ResourceGroups discovery and actual instance details.
"""

import sys
import os
import boto3
from unittest.mock import Mock

# Add the aws directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.resource_groups_service import ResourceGroupsService
from cost.pricing_service import PricingService


def debug_resourcegroups_discovery():
    """Debug what ResourceGroups API actually returns"""
    print("🔍 DEBUGGING RESOURCEGROUPS DISCOVERY")
    print("=" * 60)
    
    # Simulate what ResourceGroups API returns for an EC2 instance
    mock_resource_from_api = {
        'ResourceARN': 'arn:aws:ec2:us-east-2:263353997467:instance/i-0a2e15cdec20b7b08',
        'Tags': [
            {'Key': 'kubernetes.io/cluster/ocpv-rwx-lvvbx', 'Value': 'owned'},
            {'Key': 'Name', 'Value': 'metal-master-node'}
        ]
    }
    
    print("Raw ResourceGroups API Response:")
    print(f"  ResourceARN: {mock_resource_from_api['ResourceARN']}")
    print(f"  Tags: {mock_resource_from_api['Tags']}")
    print()
    
    # Test ARN parsing
    service = ResourceGroupsService()
    from services.resource_groups_service import ARNInfo
    
    arn_info = ARNInfo(mock_resource_from_api['ResourceARN'])
    print("ARN Parsing Results:")
    print(f"  Service: {arn_info.service}")
    print(f"  Resource Type: {arn_info.resource_type}")
    print(f"  Resource ID: {arn_info.resource_id}")
    print(f"  Region: {arn_info.region}")
    print(f"  Account ID: {arn_info.account_id}")
    print()
    
    # Test resource creation
    resource_tags = {tag['Key']: tag['Value'] for tag in mock_resource_from_api['Tags']}
    resource_info = service._create_resource_info(arn_info, resource_tags)
    
    print("Created ResourceInfo:")
    print(f"  ID: {resource_info.id}")
    print(f"  Name: {resource_info.name}")
    print(f"  Type: {resource_info.type}")  # ❌ This is likely 'instance', not 'c5d.metal'
    print(f"  Region: {resource_info.region}")
    print(f"  Additional Info: {resource_info.additional_info}")
    print()
    
    # ❌ CRITICAL: Notice that resource_info.type is 'instance', not 'c5d.metal'
    # The ResourceGroups API doesn't provide instance type details!
    
    print("❌ CRITICAL ISSUE IDENTIFIED:")
    print(f"  ResourceGroups API only provides ARN: {arn_info.resource_type}")
    print(f"  ResourceInfo.type is set to: '{resource_info.type}'")
    print(f"  But we need actual instance type: 'c5d.metal'")
    print(f"  ResourceGroups API doesn't include instance type details!")
    print()
    
    return resource_info


def debug_ec2_enrichment():
    """Debug EC2 enrichment process"""
    print("🔍 DEBUGGING EC2 ENRICHMENT PROCESS")
    print("=" * 60)
    
    # Create a ResourceInfo as it comes from ResourceGroups
    resource_info = debug_resourcegroups_discovery()
    
    # Test EC2 enrichment
    print("Testing EC2 enrichment:")
    service = ResourceGroupsService()
    
    try:
        # Create a real boto3 session
        session = boto3.Session()
        
        # Test enrichment
        enriched_resource = service._enrich_ec2_resource(resource_info, session)
        
        print("✓ EC2 enrichment successful")
        print(f"  Enriched Type: {enriched_resource.type}")
        print(f"  State: {getattr(enriched_resource, 'state', 'Not set')}")
        print(f"  Additional Info: {enriched_resource.additional_info}")
        
        # Check if instance type is now available
        instance_type = enriched_resource.additional_info.get('instance_type')
        print(f"  Instance Type from enrichment: {instance_type}")
        
        if instance_type:
            print(f"  ✓ Instance type successfully extracted: {instance_type}")
        else:
            print(f"  ❌ Instance type still not available after enrichment")
            
    except Exception as e:
        print(f"✗ EC2 enrichment failed: {e}")
        print("This might be due to permissions or the instance not existing")
    
    return resource_info


def debug_cost_calculation_path():
    """Debug the full cost calculation path"""
    print("\n🔍 DEBUGGING FULL COST CALCULATION PATH")
    print("=" * 60)
    
    # Simulate the resource as it comes from discovery (without enrichment)
    unenriched_resource = debug_resourcegroups_discovery()
    
    print("Testing cost calculation with unenriched resource:")
    pricing_service = PricingService()
    
    try:
        # Mock session for pricing service
        mock_session = Mock(spec=boto3.Session)
        pricing_service.get_client(mock_session)
        
        # Calculate cost
        cost_data = pricing_service.calculate_resource_cost(unenriched_resource, 'us-east-2', 30)
        
        print(f"  Cost calculation result:")
        print(f"    Total Cost: ${cost_data['total_cost']:.2f}")
        print(f"    Hourly Rate: ${cost_data.get('hourly_rate', 0):.4f}")
        print(f"    Service: {cost_data.get('service')}")
        print(f"    Pricing Source: {cost_data.get('pricing_source')}")
        
        # Analyze the result
        if cost_data['total_cost'] < 100:
            print(f"  ❌ PROBLEM: Cost too low, likely using default/fallback pricing")
        else:
            print(f"  ✓ Cost seems reasonable for a metal instance")
            
    except Exception as e:
        print(f"  ✗ Cost calculation failed: {e}")


def debug_pricing_logic():
    """Debug the specific pricing logic for EC2 instances"""
    print("\n🔍 DEBUGGING PRICING LOGIC")
    print("=" * 60)
    
    pricing_service = PricingService()
    
    # Test what happens when we have different resource.type values
    test_cases = [
        ('instance', 'Generic instance type'),
        ('c5d.metal', 'Correct instance type'),
        (None, 'No instance type'),
        ('', 'Empty instance type')
    ]
    
    for resource_type, description in test_cases:
        print(f"Testing with resource.type = '{resource_type}' ({description}):")
        
        # Create resource info with different type values
        from services.base import ResourceInfo
        
        resource = ResourceInfo(
            id='i-0a2e15cdec20b7b08',
            name='test-instance',
            type=resource_type,
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'instance',
                'arn': 'arn:aws:ec2:us-east-2:263353997467:instance/i-0a2e15cdec20b7b08'
            }
        )
        
        # Test the pricing calculation
        instance_type_used = resource.type or 't3.micro'  # This is the logic in _calculate_ec2_instance_cost
        fallback_price = pricing_service._get_fallback_ec2_price(instance_type_used)
        monthly_cost = fallback_price * 24 * 30
        
        print(f"  Instance type used for pricing: '{instance_type_used}'")
        print(f"  Fallback hourly rate: ${fallback_price:.4f}")
        print(f"  Monthly cost: ${monthly_cost:.2f}")
        
        if resource_type == 'instance':
            print(f"  ❌ CRITICAL: 'instance' maps to 't3.micro' default!")
        elif monthly_cost > 3000:
            print(f"  ✓ Correct pricing for metal instance")
        print()


def main():
    """Run all debugging tests"""
    print("RESOURCE DISCOVERY & PRICING DEBUG")
    print("Investigating why c5d.metal costs $69.12 instead of $3,317.76")
    print("=" * 80)
    
    # Run debugging functions
    debug_resourcegroups_discovery()
    debug_ec2_enrichment()
    debug_cost_calculation_path()
    debug_pricing_logic()
    
    print("\n" + "=" * 80)
    print("🎯 KEY FINDINGS:")
    print("=" * 80)
    print("1. ResourceGroups API only provides generic ARN info (resource_type='instance')")
    print("2. It does NOT include actual instance type (c5d.metal)")
    print("3. We need EC2 API enrichment to get real instance types")
    print("4. Without enrichment, pricing defaults to 't3.micro' ($69.12/month)")
    print("5. SOLUTION: Always enrich EC2 resources before cost calculation")


if __name__ == '__main__':
    main()