#!/usr/bin/env python3
"""
Test script for unified resource discovery using ResourceGroups API

This script tests the new ResourceGroupsService implementation and compares
it with the existing modular approach for validation.

Usage:
    python test_unified_discovery.py --cluster-uid your-cluster-uid [--profile your-aws-profile]
"""

import argparse
import boto3
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

# Import required modules
from services.registry import SERVICE_REGISTRY, SERVICE_CONFIG
from services.resource_groups_service import ResourceGroupsService
from utils.discoverer import AWSResourceDiscoverer


def parse_test_args():
    """Parse command line arguments for testing"""
    parser = argparse.ArgumentParser(description='Test unified resource discovery')
    parser.add_argument('--cluster-uid', required=True, help='Kubernetes cluster UID to test with')
    parser.add_argument('--profile', help='AWS profile to use')
    parser.add_argument('--region', help='AWS region to use')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    return parser.parse_args()


def get_session(profile: str = None, region: str = None) -> boto3.Session:
    """Create boto3 session with optional profile and region"""
    session_args = {}
    if profile:
        session_args['profile_name'] = profile
    if region:
        session_args['region_name'] = region
    return boto3.Session(**session_args)


def test_arn_parsing():
    """Test ARN parsing functionality"""
    print("=== Testing ARN Parsing ===")
    
    from services.resource_groups_service import ARNInfo
    
    test_arns = [
        "arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0",
        "arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0",
        "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188",
        "arn:aws:s3:::my-bucket",
        "arn:aws:lambda:us-east-1:123456789012:function:my-function"
    ]
    
    for arn in test_arns:
        arn_info = ARNInfo(arn)
        print(f"ARN: {arn}")
        print(f"  Service: {arn_info.service}")
        print(f"  Resource Type: {arn_info.resource_type}")
        print(f"  Resource ID: {arn_info.resource_id}")
        print(f"  Region: {arn_info.region}")
        print()


def test_resource_categorization():
    """Test resource categorization logic"""
    print("=== Testing Resource Categorization ===")
    
    service = ResourceGroupsService()
    from services.resource_groups_service import ARNInfo
    
    test_cases = [
        ("arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0", "instances"),
        ("arn:aws:ec2:us-east-1:123456789012:volume/vol-1234567890abcdef0", "volumes"),
        ("arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/123", "albs_nlbs"),
        ("arn:aws:s3:::my-bucket", "s3_buckets"),
        ("arn:aws:lambda:us-east-1:123456789012:function:my-function", "lambda_functions")
    ]
    
    for arn, expected_category in test_cases:
        arn_info = ARNInfo(arn)
        actual_category = service._categorize_resource(arn_info)
        status = "✓" if actual_category == expected_category else "✗"
        print(f"{status} {arn} -> {actual_category} (expected: {expected_category})")


def test_unified_discovery(session: boto3.Session, tag_key: str, tag_value: str, verbose: bool = False):
    """Test unified discovery approach"""
    print("=== Testing Unified Discovery ===")
    
    try:
        # Configure for unified discovery
        SERVICE_CONFIG['ResourceGroups']['enabled'] = True
        SERVICE_CONFIG['ResourceGroups']['unified_discovery'] = True
        
        discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
        unified_results = discoverer.discover_all_resources()
        
        print(f"Unified discovery completed successfully")
        
        # Count total resources found
        total_resources = 0
        for service_name, service_resources in unified_results.items():
            for resource_type, resources in service_resources.items():
                count = len(resources)
                total_resources += count
                if count > 0 or verbose:
                    print(f"  {service_name}.{resource_type}: {count} resources")
        
        print(f"Total resources found: {total_resources}")
        return unified_results, None
        
    except Exception as e:
        print(f"Unified discovery failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None, str(e)


def test_modular_discovery(session: boto3.Session, tag_key: str, tag_value: str, verbose: bool = False):
    """Test modular discovery approach"""
    print("=== Testing Modular Discovery ===")
    
    try:
        # Configure for modular discovery
        SERVICE_CONFIG['ResourceGroups']['enabled'] = False
        SERVICE_CONFIG['ResourceGroups']['unified_discovery'] = False
        
        discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
        modular_results = discoverer.discover_all_resources()
        
        print(f"Modular discovery completed successfully")
        
        # Count total resources found
        total_resources = 0
        for service_name, service_resources in modular_results.items():
            for resource_type, resources in service_resources.items():
                count = len(resources)
                total_resources += count
                if count > 0 or verbose:
                    print(f"  {service_name}.{resource_type}: {count} resources")
        
        print(f"Total resources found: {total_resources}")
        return modular_results, None
        
    except Exception as e:
        print(f"Modular discovery failed: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None, str(e)


def compare_results(unified_results, modular_results, verbose: bool = False):
    """Compare results between unified and modular discovery"""
    print("=== Comparing Results ===")
    
    if unified_results is None or modular_results is None:
        print("Cannot compare results - one or both discovery methods failed")
        return
    
    # Flatten results for comparison
    def flatten_results(results):
        flattened = {}
        for service_name, service_resources in results.items():
            for resource_type, resources in service_resources.items():
                key = f"{service_name}.{resource_type}"
                flattened[key] = {r.id for r in resources}  # Use set of resource IDs
        return flattened
    
    unified_flat = flatten_results(unified_results)
    modular_flat = flatten_results(modular_results)
    
    # Compare resource counts
    all_keys = set(unified_flat.keys()) | set(modular_flat.keys())
    
    print("Resource Type Comparison:")
    discrepancies = 0
    
    for key in sorted(all_keys):
        unified_count = len(unified_flat.get(key, set()))
        modular_count = len(modular_flat.get(key, set()))
        
        if unified_count != modular_count:
            discrepancies += 1
            status = "⚠️"
        else:
            status = "✓"
        
        print(f"  {status} {key}: Unified={unified_count}, Modular={modular_count}")
        
        if verbose and unified_count != modular_count:
            unified_ids = unified_flat.get(key, set())
            modular_ids = modular_flat.get(key, set())
            only_unified = unified_ids - modular_ids
            only_modular = modular_ids - unified_ids
            
            if only_unified:
                print(f"    Only in unified: {only_unified}")
            if only_modular:
                print(f"    Only in modular: {only_modular}")
    
    if discrepancies == 0:
        print(f"✅ All resource counts match between unified and modular discovery!")
    else:
        print(f"⚠️  Found {discrepancies} discrepancies between discovery methods")


def test_permissions():
    """Test required permissions for ResourceGroups API"""
    print("=== Testing Permissions ===")
    
    try:
        session = boto3.Session()
        client = session.client('resourcegroupstaggingapi')
        
        # Test basic permissions
        response = client.get_resources(ResourcesPerPage=1)
        print("✓ resourcegroupstaggingapi:GetResources - OK")
        
        response = client.get_tag_keys()
        print("✓ resourcegroupstaggingapi:GetTagKeys - OK")
        
        response = client.get_tag_values(Key='Name')
        print("✓ resourcegroupstaggingapi:GetTagValues - OK")
        
    except Exception as e:
        print(f"✗ Permission test failed: {e}")
        print("Make sure you have the required ResourceGroups Tagging API permissions")


def main():
    """Main test function"""
    args = parse_test_args()
    
    print("Starting unified resource discovery tests...")
    print(f"Cluster UID: {args.cluster_uid}")
    
    # Test ARN parsing and categorization
    test_arn_parsing()
    test_resource_categorization()
    
    # Test permissions
    test_permissions()
    
    # Create session
    try:
        session = get_session(profile=args.profile, region=args.region)
        region = session.region_name or 'us-east-1'
        print(f"Using region: {region}")
    except Exception as e:
        print(f"Failed to create AWS session: {e}")
        sys.exit(1)
    
    # Build tag key and value
    tag_key = f"kubernetes.io/cluster/{args.cluster_uid}"
    tag_value = "owned"
    print(f"Searching for resources with tag {tag_key}:{tag_value}")
    
    # Test both discovery methods
    unified_results, unified_error = test_unified_discovery(session, tag_key, tag_value, args.verbose)
    modular_results, modular_error = test_modular_discovery(session, tag_key, tag_value, args.verbose)
    
    # Compare results
    compare_results(unified_results, modular_results, args.verbose)
    
    # Summary
    print("\n=== Test Summary ===")
    if unified_error:
        print(f"❌ Unified discovery failed: {unified_error}")
    else:
        print("✅ Unified discovery succeeded")
    
    if modular_error:
        print(f"❌ Modular discovery failed: {modular_error}")
    else:
        print("✅ Modular discovery succeeded")
    
    if not unified_error and not modular_error:
        print("🎉 Both discovery methods are working!")
    
    print("\nTest completed.")


if __name__ == "__main__":
    main()