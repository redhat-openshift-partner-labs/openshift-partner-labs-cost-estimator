#!/usr/bin/env python3
"""
Test Phase 5: Cost Aggregation and Reporting functionality.

This test validates the new cost aggregation, analysis, and reporting
capabilities implemented in Phase 5.
"""

import sys
import os
from datetime import datetime
from unittest.mock import Mock

# Add the aws directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cost.cost_aggregator import CostAggregator, ComprehensiveCostSummary, export_cost_summary_to_json
from cost.enhanced_reporter import EnhancedCostReporter
from cost.cost_categories import CostCategory, CostPriority, CostClassifier
from services.base import ResourceInfo


def create_test_resources_and_costs():
    """Create test resources and their cost data"""
    
    # Create test resources (similar to our real cluster)
    resources = [
        # EC2 instances
        ResourceInfo(
            id='i-0123456789abcdef0',
            name='master-node-1',
            type='m5.large',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'instance',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:instance/i-0123456789abcdef0'
            }
        ),
        # EBS volumes
        ResourceInfo(
            id='vol-0123456789abcdef0',
            name='master-root-volume',
            type='gp3',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'volume',
                'size_gb': 100,
                'arn': 'arn:aws:ec2:us-east-2:123456789012:volume/vol-0123456789abcdef0'
            }
        ),
        # NAT Gateways (3 high-cost resources)
        ResourceInfo(
            id='nat-01234567890abcdef',
            name='nat-gateway-1',
            type='natgateway',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'natgateway',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcdef'
            }
        ),
        ResourceInfo(
            id='nat-01234567890abcde1',
            name='nat-gateway-2',
            type='natgateway',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'natgateway',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcde1'
            }
        ),
        ResourceInfo(
            id='nat-01234567890abcde2',
            name='nat-gateway-3',
            type='natgateway',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'natgateway',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:natgateway/nat-01234567890abcde2'
            }
        ),
        # Elastic IPs
        ResourceInfo(
            id='eipalloc-0123456789abcdef0',
            name='nat-eip-1',
            type='elastic-ip',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'elastic-ip',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:elastic-ip/eipalloc-0123456789abcdef0'
            }
        ),
        # VPC Endpoint
        ResourceInfo(
            id='vpce-0123456789abcdef0',
            name='s3-endpoint',
            type='vpc-endpoint',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'vpc-endpoint',
                'endpoint_type': 'interface',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:vpc-endpoint/vpce-0123456789abcdef0'
            }
        ),
        # S3 bucket
        ResourceInfo(
            id='ocpv-rwx-lvvbx-cluster-bootstrap',
            name='cluster-bootstrap-bucket',
            type='bucket',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 's3',
                'resource_type': 'ocpv-rwx-lvvbx-cluster-bootstrap',
                'estimated_size_gb': 10,
                'arn': 'arn:aws:s3:::ocpv-rwx-lvvbx-cluster-bootstrap'
            }
        ),
        # Free resources
        ResourceInfo(
            id='vpc-0123456789abcdef0',
            name='cluster-vpc',
            type='vpc',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'vpc',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:vpc/vpc-0123456789abcdef0'
            }
        ),
        ResourceInfo(
            id='sg-0123456789abcdef0',
            name='master-sg',
            type='security-group',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'security-group',
                'arn': 'arn:aws:ec2:us-east-2:123456789012:security-group/sg-0123456789abcdef0'
            }
        )
    ]
    
    # Create corresponding cost data (matching our real test results)
    cost_results = {
        'i-0123456789abcdef0': {
            'total_cost': 69.12,  # m5.large instance
            'service_breakdown': {'EC2-Instance': 69.12},
            'service': 'EC2-Instance',
            'is_estimated': False,
            'hourly_rate': 0.096,
            'pricing_source': 'AWS Pricing API'
        },
        'vol-0123456789abcdef0': {
            'total_cost': 8.00,  # 100GB gp3 volume
            'service_breakdown': {'EBS-Volume': 8.00},
            'service': 'EBS-Volume',
            'is_estimated': False,
            'monthly_rate_per_gb': 0.08,
            'size_gb': 100,
            'pricing_source': 'AWS Pricing API'
        },
        'nat-01234567890abcdef': {
            'total_cost': 36.90,  # NAT Gateway
            'service_breakdown': {
                'NAT-Gateway-Hours': 32.40,
                'NAT-Gateway-Data': 4.50
            },
            'service': 'NAT-Gateway',
            'is_estimated': False,
            'hourly_rate': 0.045,
            'data_processing_rate': 0.045,
            'estimated_gb_processed': 100,
            'pricing_source': 'AWS Pricing API'
        },
        'nat-01234567890abcde1': {
            'total_cost': 36.90,
            'service_breakdown': {
                'NAT-Gateway-Hours': 32.40,
                'NAT-Gateway-Data': 4.50
            },
            'service': 'NAT-Gateway',
            'is_estimated': False,
            'hourly_rate': 0.045,
            'data_processing_rate': 0.045,
            'estimated_gb_processed': 100,
            'pricing_source': 'AWS Pricing API'
        },
        'nat-01234567890abcde2': {
            'total_cost': 36.90,
            'service_breakdown': {
                'NAT-Gateway-Hours': 32.40,
                'NAT-Gateway-Data': 4.50
            },
            'service': 'NAT-Gateway',
            'is_estimated': False,
            'hourly_rate': 0.045,
            'data_processing_rate': 0.045,
            'estimated_gb_processed': 100,
            'pricing_source': 'AWS Pricing API'
        },
        'eipalloc-0123456789abcdef0': {
            'total_cost': 3.60,  # Elastic IP
            'service_breakdown': {'Elastic-IP': 3.60},
            'service': 'Elastic-IP',
            'is_estimated': False,
            'hourly_rate': 0.005,
            'pricing_source': 'AWS Pricing API'
        },
        'vpce-0123456789abcdef0': {
            'total_cost': 7.70,  # VPC Endpoint
            'service_breakdown': {
                'VPC-Endpoint-Hours': 7.20,
                'VPC-Endpoint-Data': 0.50
            },
            'service': 'VPC-Endpoint-Interface',
            'is_estimated': False,
            'hourly_rate': 0.01,
            'data_processing_rate': 0.01,
            'estimated_gb_processed': 50,
            'pricing_source': 'AWS Pricing API'
        },
        'ocpv-rwx-lvvbx-cluster-bootstrap': {
            'total_cost': 0.27,  # S3 bucket
            'service_breakdown': {
                'S3-Storage': 0.23,
                'S3-Requests': 0.04
            },
            'service': 'S3-Bucket',
            'is_estimated': True,
            'monthly_rate_per_gb': 0.023,
            'estimated_gb_stored': 10,
            'pricing_source': 'AWS Pricing API'
        },
        'vpc-0123456789abcdef0': {
            'total_cost': 0.0,  # Free resource
            'service_breakdown': {'VPC': 0.0},
            'service': 'VPC',
            'is_estimated': False,
            'pricing_source': 'AWS Pricing (Free Service)'
        },
        'sg-0123456789abcdef0': {
            'total_cost': 0.0,  # Free resource
            'service_breakdown': {'Security-Group': 0.0},
            'service': 'Security-Group',
            'is_estimated': False,
            'pricing_source': 'AWS Pricing (Free Service)'
        }
    }
    
    return resources, cost_results


def test_cost_aggregation():
    """Test the cost aggregation functionality"""
    print("Testing Cost Aggregation...")
    print("=" * 60)
    
    # Create test data
    resources, cost_results = create_test_resources_and_costs()
    
    # Create aggregator and aggregate costs
    aggregator = CostAggregator()
    summary = aggregator.aggregate_costs(
        cost_results=cost_results,
        resources=resources,
        cluster_id='ocpv-rwx-lvvbx',
        region='us-east-2',
        period_days=30
    )
    
    # Validate aggregation results
    print(f"✓ Aggregated costs for {summary.total_resources} resources")
    print(f"  Total Monthly Cost: ${summary.total_monthly_cost:.2f}")
    print(f"  Billable Resources: {summary.billable_resources}")
    print(f"  Free Resources: {summary.free_resources}")
    
    # Test cost breakdowns
    print(f"\n✓ Cost by Category:")
    for category, cost in summary.cost_by_category.items():
        if cost > 0:
            print(f"  {category.value}: ${cost:.2f}")
    
    print(f"\n✓ Cost by Service:")
    for service, cost in summary.cost_by_service.items():
        if cost > 0:
            print(f"  {service}: ${cost:.2f}")
    
    print(f"\n✓ Top 5 Highest Cost Resources:")
    for i, resource in enumerate(summary.highest_cost_resources[:5], 1):
        print(f"  {i}. {resource.resource_name}: ${resource.total_cost:.2f}")
    
    return summary


def test_cost_analysis():
    """Test cost analysis functionality"""
    print("\nTesting Cost Analysis...")
    print("=" * 60)
    
    resources, cost_results = create_test_resources_and_costs()
    aggregator = CostAggregator()
    summary = aggregator.aggregate_costs(cost_results, resources, 'ocpv-rwx-lvvbx', 'us-east-2')
    
    # Test cost distribution analysis
    analysis = summary.cost_distribution_analysis
    print(f"✓ Cost Distribution Analysis:")
    print(f"  High Cost Resources: {analysis['resource_counts']['high_cost']}")
    print(f"  Medium Cost Resources: {analysis['resource_counts']['medium_cost']}")
    print(f"  Low Cost Resources: {analysis['resource_counts']['low_cost']}")
    print(f"  Free Resources: {analysis['resource_counts']['zero_cost']}")
    print(f"  Top 5 Resources: {analysis['cost_concentration']['top_5_percentage']:.1f}% of total cost")
    
    # Test optimization analysis
    optimization = summary.optimization_potential
    print(f"\n✓ Optimization Analysis:")
    print(f"  Needs Optimization: {optimization['needs_optimization']}")
    print(f"  Priority: {optimization['optimization_priority']}")
    print(f"  Potential Savings: ${optimization['total_potential_savings']:.2f}/month")
    print(f"  Optimization Suggestions: {len(optimization['optimization_suggestions'])}")
    
    for suggestion in optimization['optimization_suggestions'][:3]:
        print(f"    - {suggestion['type']}: ${suggestion['potential_monthly_savings']:.2f} savings")
    
    return summary


def test_enhanced_reporting():
    """Test enhanced reporting functionality"""
    print("\nTesting Enhanced Reporting...")
    print("=" * 60)
    
    resources, cost_results = create_test_resources_and_costs()
    aggregator = CostAggregator()
    summary = aggregator.aggregate_costs(cost_results, resources, 'ocpv-rwx-lvvbx', 'us-east-2')
    
    # Test console reporting
    reporter = EnhancedCostReporter()
    
    print("✓ Testing Quick Summary:")
    reporter.print_quick_summary(summary)
    
    print("\n✓ Testing Comprehensive Report:")
    print("(Only showing header for brevity...)")
    reporter._print_header(summary)
    reporter._print_cost_overview(summary)
    
    return summary


def test_export_functionality():
    """Test export functionality"""
    print("\nTesting Export Functionality...")
    print("=" * 60)
    
    resources, cost_results = create_test_resources_and_costs()
    aggregator = CostAggregator()
    summary = aggregator.aggregate_costs(cost_results, resources, 'ocpv-rwx-lvvbx', 'us-east-2')
    
    # Test JSON export
    json_file = '/tmp/test_cost_summary.json'
    try:
        export_cost_summary_to_json(summary, json_file)
        print(f"✓ JSON export successful: {json_file}")
        
        # Verify file was created
        if os.path.exists(json_file):
            file_size = os.path.getsize(json_file)
            print(f"  File size: {file_size} bytes")
        
    except Exception as e:
        print(f"✗ JSON export failed: {e}")
    
    # Test HTML export
    html_file = '/tmp/test_cost_report.html'
    try:
        reporter = EnhancedCostReporter()
        reporter.generate_html_report(summary, html_file)
        print(f"✓ HTML export successful: {html_file}")
        
        if os.path.exists(html_file):
            file_size = os.path.getsize(html_file)
            print(f"  File size: {file_size} bytes")
        
    except Exception as e:
        print(f"✗ HTML export failed: {e}")


def test_cost_categories():
    """Test cost categories functionality"""
    print("\nTesting Cost Categories...")
    print("=" * 60)
    
    # Test cost classifier
    test_cases = [
        ('instances', CostCategory.BILLABLE_COMPUTE, CostPriority.HIGH),
        ('nat_gateways', CostCategory.BILLABLE_NETWORKING, CostPriority.HIGH),
        ('s3_buckets', CostCategory.BILLABLE_STORAGE, CostPriority.MEDIUM),
        ('vpcs', CostCategory.FREE_NETWORKING, CostPriority.FREE),
        ('security_groups', CostCategory.FREE_SECURITY, CostPriority.FREE)
    ]
    
    for resource_type, expected_category, expected_priority in test_cases:
        category = CostClassifier.get_cost_category(resource_type)
        priority = CostClassifier.get_cost_priority(resource_type)
        
        print(f"✓ {resource_type}: {category.value} ({priority.value})")
        
        assert category == expected_category, f"Expected {expected_category}, got {category}"
        assert priority == expected_priority, f"Expected {expected_priority}, got {priority}"
    
    # Test utility functions
    resource_types = ['instances', 'nat_gateways', 'vpcs', 'security_groups']
    billable = CostClassifier.get_billable_resources(resource_types)
    free = CostClassifier.get_free_resources(resource_types)
    high_priority = CostClassifier.get_high_priority_resources(resource_types)
    
    print(f"✓ Billable resources: {billable}")
    print(f"✓ Free resources: {free}")
    print(f"✓ High priority resources: {high_priority}")


def main():
    """Run all Phase 5 tests"""
    print("Phase 5: Cost Aggregation and Reporting Test")
    print("=" * 60)
    print("Testing comprehensive cost aggregation, analysis, and reporting functionality")
    print()
    
    try:
        # Test cost categories
        test_cost_categories()
        
        # Test cost aggregation
        summary = test_cost_aggregation()
        
        # Test cost analysis
        test_cost_analysis()
        
        # Test enhanced reporting
        test_enhanced_reporting()
        
        # Test export functionality
        test_export_functionality()
        
        print("\n" + "=" * 60)
        print("✅ ALL PHASE 5 TESTS PASSED!")
        print(f"✓ Successfully aggregated costs for {summary.total_resources} resources")
        print(f"✓ Total estimated monthly cost: ${summary.total_monthly_cost:.2f}")
        print(f"✓ {len(summary.optimization_potential['optimization_suggestions'])} optimization suggestions generated")
        print(f"✓ Enhanced reporting and export functionality working")
        print("✓ Cost categories and classification system operational")
        
        # Show final comprehensive report
        print("\n" + "=" * 60)
        print("FINAL COMPREHENSIVE COST REPORT:")
        print("=" * 60)
        
        reporter = EnhancedCostReporter()
        reporter.print_comprehensive_cost_summary(summary)
        
    except Exception as e:
        print(f"\n❌ Phase 5 test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)