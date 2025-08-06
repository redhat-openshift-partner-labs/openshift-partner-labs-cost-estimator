#!/usr/bin/env python3
"""
Test script for cost filtering and sorting functionality.
"""

import sys
import os
from unittest.mock import Mock

# Add the aws directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import _apply_cost_filters_and_sorting
from cost.cost_aggregator import ComprehensiveCostSummary, ResourceCostSummary
from cost.cost_categories import CostCategory, CostPriority
from datetime import datetime


def test_cost_filtering():
    """Test cost filtering and sorting functionality"""
    print("🧪 TESTING COST FILTERING AND SORTING")
    print("=" * 60)
    
    # Create test resource summaries with different cost levels
    test_resources = [
        ResourceCostSummary(
            resource_id='i-high-cost',
            resource_name='expensive-instance',
            resource_type='instances',
            service='EC2-Instance',
            region='us-east-1',
            cost_category=CostCategory.BILLABLE_COMPUTE,
            cost_priority=CostPriority.HIGH,
            total_cost=100.0,  # High cost
            service_breakdown={'EC2-Instance': 100.0},
            is_estimated=False,
            pricing_source='AWS Pricing API'
        ),
        ResourceCostSummary(
            resource_id='nat-medium-cost',
            resource_name='nat-gateway',
            resource_type='nat_gateways',
            service='NAT-Gateway',
            region='us-east-1',
            cost_category=CostCategory.BILLABLE_NETWORKING,
            cost_priority=CostPriority.MEDIUM,
            total_cost=25.0,  # Medium cost
            service_breakdown={'NAT-Gateway': 25.0},
            is_estimated=False,
            pricing_source='AWS Pricing API'
        ),
        ResourceCostSummary(
            resource_id='vol-low-cost',
            resource_name='small-volume',
            resource_type='volumes',
            service='EBS-Volume',
            region='us-east-1',
            cost_category=CostCategory.BILLABLE_STORAGE,
            cost_priority=CostPriority.LOW,
            total_cost=5.0,  # Low cost
            service_breakdown={'EBS-Volume': 5.0},
            is_estimated=False,
            pricing_source='AWS Pricing API'
        ),
        ResourceCostSummary(
            resource_id='vpc-free',
            resource_name='vpc',
            resource_type='vpcs',
            service='VPC',
            region='us-east-1',
            cost_category=CostCategory.FREE_NETWORKING,
            cost_priority=CostPriority.FREE,
            total_cost=0.0,  # Free
            service_breakdown={'VPC': 0.0},
            is_estimated=False,
            pricing_source='AWS Pricing (Free Service)'
        )
    ]
    
    # Create test summary
    test_summary = ComprehensiveCostSummary(
        cluster_id='test-cluster',
        region='us-east-1',
        analysis_date=datetime.now(),
        period_days=30,
        total_monthly_cost=130.0,
        total_billable_cost=130.0,
        total_resources=4,
        billable_resources=3,
        free_resources=1,
        cost_by_category={},
        cost_by_service={},
        cost_by_priority={},
        cost_by_region={},
        resource_summaries=test_resources,
        highest_cost_resources=test_resources,
        cost_distribution_analysis={},
        optimization_potential={}
    )
    
    # Test 1: High cost filter
    print("\n📊 Test 1: High Cost Filter (≥$50)")
    args_high = Mock()
    args_high.cost_filter = 'high'
    args_high.cost_threshold = None
    args_high.sort_by_cost = False
    
    filtered_summary = _apply_cost_filters_and_sorting(test_summary, args_high)
    high_cost_resources = [r for r in filtered_summary.resource_summaries if r.total_cost >= 50]
    
    if len(high_cost_resources) == 1 and high_cost_resources[0].resource_id == 'i-high-cost':
        print("✅ High cost filter working correctly")
    else:
        print("❌ High cost filter failed")
        return False
    
    # Test 2: Medium cost filter
    print("\n📊 Test 2: Medium Cost Filter ($10-$50)")
    args_medium = Mock()
    args_medium.cost_filter = 'medium'
    args_medium.cost_threshold = None
    args_medium.sort_by_cost = False
    
    filtered_summary = _apply_cost_filters_and_sorting(test_summary, args_medium)
    medium_cost_resources = filtered_summary.resource_summaries
    
    if len(medium_cost_resources) == 1 and medium_cost_resources[0].resource_id == 'nat-medium-cost':
        print("✅ Medium cost filter working correctly")
    else:
        print("❌ Medium cost filter failed")
        return False
    
    # Test 3: Cost threshold filter
    print("\n📊 Test 3: Cost Threshold Filter (≥$20)")
    args_threshold = Mock()
    args_threshold.cost_threshold = 20.0
    args_threshold.cost_filter = None
    args_threshold.sort_by_cost = False
    
    filtered_summary = _apply_cost_filters_and_sorting(test_summary, args_threshold)
    threshold_resources = filtered_summary.resource_summaries
    
    expected_ids = {'i-high-cost', 'nat-medium-cost'}
    actual_ids = {r.resource_id for r in threshold_resources}
    
    if actual_ids == expected_ids:
        print("✅ Cost threshold filter working correctly")
    else:
        print(f"❌ Cost threshold filter failed. Expected: {expected_ids}, Got: {actual_ids}")
        return False
    
    # Test 4: Sort by cost
    print("\n📊 Test 4: Sort by Cost (Highest First)")
    args_sort = Mock()
    args_sort.sort_by_cost = True
    args_sort.cost_filter = None
    args_sort.cost_threshold = None
    
    sorted_summary = _apply_cost_filters_and_sorting(test_summary, args_sort)
    sorted_costs = [r.total_cost for r in sorted_summary.resource_summaries]
    
    if sorted_costs == [100.0, 25.0, 5.0, 0.0]:
        print("✅ Cost sorting working correctly")
    else:
        print(f"❌ Cost sorting failed. Expected: [100.0, 25.0, 5.0, 0.0], Got: {sorted_costs}")
        return False
    
    # Test 5: Free resources filter
    print("\n📊 Test 5: Free Resources Filter")
    args_free = Mock()
    args_free.cost_filter = 'free'
    args_free.cost_threshold = None
    args_free.sort_by_cost = False
    
    filtered_summary = _apply_cost_filters_and_sorting(test_summary, args_free)
    free_resources = filtered_summary.resource_summaries
    
    if len(free_resources) == 1 and free_resources[0].resource_id == 'vpc-free':
        print("✅ Free resources filter working correctly")
    else:
        print("❌ Free resources filter failed")
        return False
    
    print("\n🎉 ALL FILTERING TESTS PASSED!")
    return True


def main():
    """Run cost filtering tests"""
    try:
        success = test_cost_filtering()
        if success:
            print("\n✅ Cost filtering and sorting implementation verified!")
            return 0
        else:
            print("\n❌ Cost filtering tests failed!")
            return 1
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)