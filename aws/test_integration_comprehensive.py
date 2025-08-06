#!/usr/bin/env python3
"""
Comprehensive integration test for the complete cost estimation system.

This test validates the end-to-end workflow from resource discovery 
through comprehensive cost estimation and reporting.
"""

import sys
import os
import subprocess
import tempfile
from unittest.mock import Mock, patch

# Add the aws directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import perform_comprehensive_cost_analysis, _generate_validation_stats
from services.resource_groups_service import ResourceGroupsService
from cost.pricing_service import PricingService
from cost.cost_aggregator import CostAggregator
from cost.enhanced_reporter import EnhancedCostReporter
from services.base import ResourceInfo
import boto3


def test_cli_integration():
    """Test CLI integration with new comprehensive cost flags"""
    print("🔍 TESTING CLI INTEGRATION")
    print("=" * 60)
    
    # Test help message includes new flags
    try:
        result = subprocess.run([sys.executable, 'main.py', '--help'], 
                              capture_output=True, text=True, timeout=10)
        
        help_output = result.stdout
        
        # Check for new comprehensive cost flags
        required_flags = [
            '--comprehensive-costs',
            '--cost-validation',
            '--export-format',
            '--export-file'
        ]
        
        missing_flags = []
        for flag in required_flags:
            if flag not in help_output:
                missing_flags.append(flag)
        
        if missing_flags:
            print(f"❌ Missing CLI flags: {missing_flags}")
            return False
        else:
            print(f"✓ All comprehensive cost CLI flags present")
            return True
            
    except subprocess.TimeoutExpired:
        print(f"❌ CLI help command timed out")
        return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False


def test_comprehensive_cost_workflow():
    """Test the complete comprehensive cost analysis workflow"""
    print("\n🔍 TESTING COMPREHENSIVE COST WORKFLOW")
    print("=" * 60)
    
    # Create test resources with realistic data
    test_resources = [
        # High-cost metal instance
        ResourceInfo(
            id='i-0a2e15cdec20b7b08',
            name='metal-master-node',
            type='instance',  # Generic from ResourceGroups
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'instance',
                'instance_type': 'c5d.metal',  # Enriched data
                'arn': 'arn:aws:ec2:us-east-2:263353997467:instance/i-0a2e15cdec20b7b08'
            }
        ),
        # NAT Gateway
        ResourceInfo(
            id='nat-01234567890abcdef',
            name='nat-gateway-1',
            type='natgateway',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'natgateway',
                'arn': 'arn:aws:ec2:us-east-2:263353997467:natgateway/nat-01234567890abcdef'
            }
        ),
        # EBS Volume
        ResourceInfo(
            id='vol-0123456789abcdef0',
            name='master-root-volume',
            type='volume',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'volume',
                'size_gb': 100,
                'volume_type': 'gp3',
                'arn': 'arn:aws:ec2:us-east-2:263353997467:volume/vol-0123456789abcdef0'
            }
        ),
        # Free resource
        ResourceInfo(
            id='vpc-0123456789abcdef0',
            name='cluster-vpc',
            type='vpc',
            region='us-east-2',
            additional_info={
                'discovery_method': 'resource_groups_api',
                'service': 'ec2',
                'resource_type': 'vpc',
                'arn': 'arn:aws:ec2:us-east-2:263353997467:vpc/vpc-0123456789abcdef0'
            }
        )
    ]
    
    # Create a mock session
    mock_session = Mock(spec=boto3.Session)
    mock_session.region_name = 'us-east-2'
    
    # Create a mock args object
    class MockArgs:
        cost_period = 30
        cost_validation = True
        export_format = 'json'
        export_file = None
    
    args = MockArgs()
    
    try:
        # Test the comprehensive cost analysis workflow
        with patch('main.create_cost_calculation_system') as mock_cost_system:
            # Mock the cost calculation system
            mock_registry = Mock()
            mock_pricing_service = Mock()
            mock_cost_system.return_value = (mock_registry, mock_pricing_service)
            
            # Mock cost calculation results
            mock_cost_results = {
                'i-0a2e15cdec20b7b08': {
                    'total_cost': 3317.76,  # c5d.metal pricing
                    'service_breakdown': {'EC2-Instance': 3317.76},
                    'service': 'EC2-Instance',
                    'is_estimated': False,
                    'hourly_rate': 4.608,
                    'actual_instance_type': 'c5d.metal',
                    'pricing_source': 'AWS Pricing API'
                },
                'nat-01234567890abcdef': {
                    'total_cost': 36.90,
                    'service_breakdown': {'NAT-Gateway': 36.90},
                    'service': 'NAT-Gateway',
                    'is_estimated': False,
                    'pricing_source': 'AWS Pricing API'
                },
                'vol-0123456789abcdef0': {
                    'total_cost': 8.00,
                    'service_breakdown': {'EBS-Volume': 8.00},
                    'service': 'EBS-Volume',
                    'is_estimated': False,
                    'pricing_source': 'AWS Pricing API'
                },
                'vpc-0123456789abcdef0': {
                    'total_cost': 0.0,
                    'service_breakdown': {'VPC': 0.0},
                    'service': 'VPC',
                    'is_estimated': False,
                    'pricing_source': 'AWS Pricing (Free Service)'
                }
            }
            
            mock_pricing_service.calculate_resource_cost_with_retry.side_effect = \
                lambda resource, region, days: mock_cost_results[resource.id]
            
            # Simulate the all_resources structure as it would come from discoverer
            all_resources = {
                'ResourceGroups': {
                    'instances': [test_resources[0]],
                    'nat_gateways': [test_resources[1]], 
                    'volumes': [test_resources[2]],
                    'vpcs': [test_resources[3]]
                }
            }
            
            # Test the comprehensive cost analysis
            success = perform_comprehensive_cost_analysis(
                mock_session, all_resources, 'test-cluster', 'us-east-2', args
            )
            
            if success:
                print("✓ Comprehensive cost analysis workflow completed successfully")
                
                # Verify the mock was called correctly
                assert mock_cost_system.called, "Cost calculation system should be created"
                assert mock_pricing_service.calculate_resource_cost_with_retry.call_count == 4, \
                    "Should calculate costs for all 4 resources"
                
                return True
            else:
                print("❌ Comprehensive cost analysis workflow failed")
                return False
                
    except Exception as e:
        print(f"❌ Comprehensive cost workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_stats():
    """Test cost validation statistics generation"""
    print("\n🔍 TESTING VALIDATION STATISTICS")
    print("=" * 60)
    
    # Create test cost results with different quality levels
    cost_results = {
        'resource1': {'is_estimated': False, 'calculation_failed': False},  # Precise
        'resource2': {'is_estimated': True, 'calculation_failed': False},   # Estimated
        'resource3': {'is_estimated': False, 'calculation_failed': True},   # Failed
        'resource4': {'is_estimated': False, 'calculation_failed': False},  # Precise
    }
    
    resources = [Mock() for _ in range(4)]
    
    try:
        stats = _generate_validation_stats(cost_results, resources)
        
        print("Generated validation statistics:")
        for stat_name, stat_value in stats.items():
            print(f"  {stat_name}: {stat_value}")
        
        # Verify calculations
        assert stats['Total Resources'] == 4
        assert stats['Costs Calculated'] == 4
        assert "50.0%" in stats['Precise Pricing']  # 2/4 precise
        assert "25.0%" in stats['Estimated Pricing']  # 1/4 estimated
        assert stats['Failed Calculations'] == 1
        
        print("✓ Validation statistics generation working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Validation statistics test failed: {e}")
        return False


def test_export_functionality():
    """Test export functionality with temporary files"""
    print("\n🔍 TESTING EXPORT FUNCTIONALITY")
    print("=" * 60)
    
    # Create a simple cost summary for testing
    from cost.cost_aggregator import ComprehensiveCostSummary, ResourceCostSummary
    from cost.cost_categories import CostCategory, CostPriority
    from datetime import datetime
    
    try:
        # Create test data
        resource_summaries = [
            ResourceCostSummary(
                resource_id='i-test',
                resource_name='test-instance',
                resource_type='instances',
                service='EC2-Instance',
                region='us-east-2',
                cost_category=CostCategory.BILLABLE_COMPUTE,
                cost_priority=CostPriority.HIGH,
                total_cost=3317.76,
                service_breakdown={'EC2-Instance': 3317.76},
                is_estimated=False,
                pricing_source='AWS Pricing API'
            )
        ]
        
        test_summary = ComprehensiveCostSummary(
            cluster_id='test-cluster',
            region='us-east-2',
            analysis_date=datetime.now(),
            period_days=30,
            total_monthly_cost=3317.76,
            total_billable_cost=3317.76,
            total_resources=1,
            billable_resources=1,
            free_resources=0,
            cost_by_category={CostCategory.BILLABLE_COMPUTE: 3317.76},
            cost_by_service={'EC2-Instance': 3317.76},
            cost_by_priority={CostPriority.HIGH: 3317.76},
            cost_by_region={'us-east-2': 3317.76},
            resource_summaries=resource_summaries,
            highest_cost_resources=resource_summaries,
            cost_distribution_analysis={},
            optimization_potential={}
        )
        
        # Test JSON export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as json_file:
            from cost.cost_aggregator import export_cost_summary_to_json
            export_cost_summary_to_json(test_summary, json_file.name)
            
            # Verify file was created and has content
            if os.path.exists(json_file.name) and os.path.getsize(json_file.name) > 0:
                print("✓ JSON export working")
                os.unlink(json_file.name)
            else:
                print("❌ JSON export failed")
                return False
        
        # Test HTML export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
            reporter = EnhancedCostReporter()
            reporter.generate_html_report(test_summary, html_file.name)
            
            # Verify file was created and has content
            if os.path.exists(html_file.name) and os.path.getsize(html_file.name) > 0:
                print("✓ HTML export working")
                os.unlink(html_file.name)
            else:
                print("❌ HTML export failed")
                return False
        
        print("✓ Export functionality working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Export functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resource_enrichment_integration():
    """Test that resource enrichment properly integrates with cost calculation"""
    print("\n🔍 TESTING RESOURCE ENRICHMENT INTEGRATION")
    print("=" * 60)
    
    try:
        # Test ResourceGroups service with enrichment
        service = ResourceGroupsService()
        
        # Create mock session and client
        mock_session = Mock(spec=boto3.Session)
        mock_ec2_client = Mock()
        mock_session.client.return_value = mock_ec2_client
        
        # Mock EC2 describe_instances response
        mock_ec2_client.describe_instances.return_value = {
            'Reservations': [{
                'Instances': [{
                    'InstanceId': 'i-test',
                    'InstanceType': 'c5d.metal',
                    'State': {'Name': 'running'},
                    'LaunchTime': '2025-01-01T00:00:00Z',
                    'VpcId': 'vpc-123',
                    'SubnetId': 'subnet-123'
                }]
            }]
        }
        
        # Create unenriched resource
        unenriched = ResourceInfo(
            id='i-test',
            name='test-instance',
            type='instance',  # Generic
            region='us-east-2',
            additional_info={
                'service': 'ec2',
                'resource_type': 'instance'
            }
        )
        
        # Test enrichment
        enriched = service._enrich_ec2_resource(unenriched, mock_session)
        
        # Verify enrichment
        instance_type = enriched.additional_info.get('instance_type')
        if instance_type == 'c5d.metal':
            print(f"✓ Resource enrichment successfully extracted: {instance_type}")
            
            # Test that this would now provide accurate pricing
            pricing_service = PricingService()
            
            with patch.object(pricing_service, 'get_ec2_instance_pricing', return_value=4.608):
                cost_data = pricing_service._calculate_ec2_instance_cost(enriched, 'us-east-2', 30)
                
                if abs(cost_data['total_cost'] - 3317.76) < 1:
                    print(f"✓ Enriched resource provides accurate pricing: ${cost_data['total_cost']:.2f}")
                    return True
                else:
                    print(f"❌ Enriched resource pricing incorrect: ${cost_data['total_cost']:.2f}")
                    return False
        else:
            print(f"❌ Resource enrichment failed: {instance_type}")
            return False
            
    except Exception as e:
        print(f"❌ Resource enrichment integration test failed: {e}")
        return False


def main():
    """Run all comprehensive integration tests"""
    print("COMPREHENSIVE INTEGRATION TEST")
    print("Testing complete end-to-end cost estimation system")
    print("=" * 80)
    
    tests = [
        test_cli_integration,
        test_comprehensive_cost_workflow,
        test_validation_stats,
        test_export_functionality,
        test_resource_enrichment_integration
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} failed with exception: {e}")
            failed += 1
    
    print("\n" + "=" * 80)
    print("🎯 COMPREHENSIVE INTEGRATION TEST RESULTS")
    print("=" * 80)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL INTEGRATION TESTS PASSED!")
        print("✅ Comprehensive cost estimation system is ready for production")
        print("✅ CLI integration working correctly")
        print("✅ Cost calculation accuracy validated")
        print("✅ Export functionality operational")
        print("✅ Resource enrichment providing accurate pricing")
        return 0
    else:
        print(f"\n❌ {failed} integration tests failed")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)