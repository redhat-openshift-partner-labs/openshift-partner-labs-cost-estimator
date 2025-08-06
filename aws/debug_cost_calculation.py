#!/usr/bin/env python3
"""
Debug cost calculation for specific resources.

This script traces through the entire cost calculation process to identify
where the pricing calculation is going wrong.
"""

import sys
import os
import boto3
from unittest.mock import Mock

# Add the aws directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost.pricing_service import PricingService
from services.base import ResourceInfo


def debug_ec2_instance_pricing():
    """Debug EC2 instance pricing calculation step by step"""
    print("🔍 DEBUGGING EC2 INSTANCE COST CALCULATION")
    print("=" * 60)
    
    # Create the problematic resource
    resource = ResourceInfo(
        id='i-0a2e15cdec20b7b08',
        name='metal-instance',
        type='c5d.metal',  # This should be the instance type
        region='us-east-2',
        additional_info={
            'discovery_method': 'resource_groups_api',
            'service': 'ec2',
            'resource_type': 'instance',
            'account_id': '263353997467',
            'arn': 'arn:aws:ec2:us-east-2:263353997467:instance/i-0a2e15cdec20b7b08',
            'instance_type': 'c5d.metal'  # Also store here for redundancy
        }
    )
    
    print(f"Target Resource:")
    print(f"  ID: {resource.id}")
    print(f"  Name: {resource.name}")
    print(f"  Type: {resource.type}")
    print(f"  Region: {resource.region}")
    print(f"  ARN: {resource.additional_info.get('arn')}")
    print(f"  Instance Type in additional_info: {resource.additional_info.get('instance_type')}")
    print()
    
    print(f"Expected Calculation:")
    print(f"  Hourly Rate: $4.608")
    print(f"  Monthly Cost: $4.608 × 24 × 30 = $3,317.76")
    print()
    
    # Create pricing service
    pricing_service = PricingService()
    
    # Mock the AWS session since we might not have access to pricing API
    mock_session = Mock(spec=boto3.Session)
    mock_client = Mock()
    mock_session.client.return_value = mock_client
    
    # Test pricing service initialization
    try:
        pricing_service.get_client(mock_session)
        print(f"✓ Pricing service initialized")
    except Exception as e:
        print(f"✗ Pricing service initialization failed: {e}")
    
    # Step 1: Test instance type extraction
    print(f"\n1. Testing instance type extraction:")
    instance_type = resource.type or 't3.micro'
    print(f"   Resource.type: '{resource.type}'")
    print(f"   Used instance_type: '{instance_type}'")
    
    if instance_type != 'c5d.metal':
        print(f"   ❌ PROBLEM: Expected 'c5d.metal', got '{instance_type}'")
    else:
        print(f"   ✓ Instance type correctly identified")
    
    # Step 2: Test fallback pricing
    print(f"\n2. Testing fallback pricing:")
    fallback_price = pricing_service._get_fallback_ec2_price(instance_type)
    print(f"   Fallback hourly rate for {instance_type}: ${fallback_price:.4f}")
    print(f"   Fallback monthly cost: ${fallback_price * 24 * 30:.2f}")
    
    if fallback_price < 4.0:  # Way too low for c5d.metal
        print(f"   ❌ PROBLEM: Fallback price too low for c5d.metal")
    else:
        print(f"   ✓ Fallback price seems reasonable")
    
    # Step 3: Test cost calculation method
    print(f"\n3. Testing _calculate_ec2_instance_cost method:")
    try:
        cost_data = pricing_service._calculate_ec2_instance_cost(resource, 'us-east-2', 30)
        print(f"   Calculated cost data: {cost_data}")
        
        calculated_cost = cost_data.get('total_cost', 0)
        hourly_rate = cost_data.get('hourly_rate', 0)
        
        print(f"   Calculated monthly cost: ${calculated_cost:.2f}")
        print(f"   Calculated hourly rate: ${hourly_rate:.4f}")
        
        if calculated_cost < 3000:  # Should be ~$3,317
            print(f"   ❌ PROBLEM: Calculated cost way too low")
        else:
            print(f"   ✓ Calculated cost seems reasonable")
            
    except Exception as e:
        print(f"   ✗ Cost calculation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Test full resource cost calculation
    print(f"\n4. Testing calculate_resource_cost method:")
    try:
        full_cost_data = pricing_service.calculate_resource_cost(resource, 'us-east-2', 30)
        print(f"   Full cost calculation result:")
        for key, value in full_cost_data.items():
            print(f"     {key}: {value}")
        
        total_cost = full_cost_data.get('total_cost', 0)
        if total_cost < 3000:
            print(f"   ❌ CRITICAL PROBLEM: Total cost ${total_cost:.2f} is way too low")
            print(f"   Expected: ~$3,317.76")
        else:
            print(f"   ✓ Total cost seems reasonable")
            
    except Exception as e:
        print(f"   ✗ Full cost calculation failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Step 5: Check resource category mapping
    print(f"\n5. Testing resource category mapping:")
    try:
        arn_service = resource.additional_info.get('service')
        arn_resource_type = resource.additional_info.get('resource_type')
        category = pricing_service._map_arn_to_category(arn_service, arn_resource_type)
        print(f"   ARN service: {arn_service}")
        print(f"   ARN resource type: {arn_resource_type}")
        print(f"   Mapped category: {category}")
        
        if category != 'instances':
            print(f"   ❌ PROBLEM: Expected 'instances', got '{category}'")
        else:
            print(f"   ✓ Category mapping correct")
            
    except Exception as e:
        print(f"   ✗ Category mapping failed: {e}")


def debug_fallback_pricing():
    """Debug the fallback pricing system"""
    print(f"\n🔍 DEBUGGING FALLBACK PRICING SYSTEM")
    print("=" * 60)
    
    pricing_service = PricingService()
    
    # Test various instance types
    test_instances = [
        ('c5d.metal', 4.608),   # The problematic one
        ('m5.large', 0.096),    # Common instance
        ('t3.micro', 0.0104),   # Small instance
        ('unknown.type', None)  # Unknown instance
    ]
    
    for instance_type, expected_rate in test_instances:
        fallback_rate = pricing_service._get_fallback_ec2_price(instance_type)
        print(f"Instance Type: {instance_type}")
        print(f"  Expected Rate: ${expected_rate}/hour" if expected_rate else "  Expected Rate: Unknown")
        print(f"  Fallback Rate: ${fallback_rate:.4f}/hour")
        print(f"  Monthly Cost: ${fallback_rate * 24 * 30:.2f}")
        
        if expected_rate and abs(fallback_rate - expected_rate) > 0.1:
            print(f"  ❌ PROBLEM: Significant difference from expected rate")
        elif expected_rate:
            print(f"  ✓ Fallback rate close to expected")
        print()


def debug_pricing_api_calls():
    """Debug AWS Pricing API calls"""
    print(f"\n🔍 DEBUGGING AWS PRICING API CALLS")
    print("=" * 60)
    
    pricing_service = PricingService()
    
    # Create a real boto3 session for testing
    try:
        session = boto3.Session()
        client = pricing_service.get_client(session)
        print(f"✓ Created real AWS Pricing client")
        
        # Test getting c5d.metal pricing
        try:
            hourly_rate = pricing_service.get_ec2_instance_pricing('c5d.metal', 'us-east-2')
            print(f"✓ AWS Pricing API call successful")
            print(f"  Hourly rate for c5d.metal: ${hourly_rate:.4f}")
            print(f"  Monthly cost: ${hourly_rate * 24 * 30:.2f}")
            
            if hourly_rate > 4.0:
                print(f"  ✓ Pricing API returned reasonable rate")
            else:
                print(f"  ❌ PROBLEM: Pricing API returned unexpectedly low rate")
                
        except Exception as e:
            print(f"  ✗ AWS Pricing API call failed: {e}")
            print(f"  Will fall back to hardcoded pricing")
            
    except Exception as e:
        print(f"✗ Failed to create AWS Pricing client: {e}")
        print(f"  This might be due to credentials or permissions")


def main():
    """Run all debugging tests"""
    print("CRITICAL COST CALCULATION DEBUG")
    print("User Report: c5d.metal calculated as $69.12/month instead of $3,317.76/month")
    print("=" * 80)
    
    # Run all debugging functions
    debug_ec2_instance_pricing()
    debug_fallback_pricing() 
    debug_pricing_api_calls()
    
    print("\n" + "=" * 80)
    print("🎯 SUMMARY OF FINDINGS:")
    print("=" * 80)
    print("Run this script to identify exactly where the cost calculation is failing.")
    print("Key areas to investigate:")
    print("1. Instance type extraction from ResourceInfo")
    print("2. Fallback pricing accuracy") 
    print("3. AWS Pricing API integration")
    print("4. Resource category mapping")
    print("\nExpected c5d.metal cost: $4.608/hour = $3,317.76/month")


if __name__ == '__main__':
    main()