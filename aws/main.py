"""
Search AWS resources tagged with kubernetes.io/cluster/{cluster-uid}:owned

This module provides the main entry point for the modular AWS resource discovery framework.
It orchestrates the discovery process using services from the services package and
utilities from the utils package.

Architecture:
- services/ - AWS service implementations (EC2, ELB, etc.)
- cost/ - Cost estimation services (Cost Explorer, Analyzer, Reporter)
- utils/ - Utility classes for formatting and discovery
- main.py - Command-line interface and orchestration

The main script is intentionally lightweight, focusing only on:
1. Command-line argument parsing
2. AWS session management
3. Service orchestration
4. Cost estimation (optional)
5. Result formatting and output

All business logic is delegated to the modular services and utilities.
"""

import argparse
import boto3
import sys
from datetime import datetime, timedelta

# Import from modular services
from services import SERVICE_REGISTRY, SERVICE_CONFIG, get_available_services
from utils.formatter import ResourceFormatter
from utils.discoverer import AWSResourceDiscoverer
from cost.analyzer_service import CostAnalyzerService
from cost.reporter_service import CostReporterService
from cost.registry import COST_SERVICE_REGISTRY

# Import enhanced comprehensive cost system
from cost.pricing_service import PricingService
from cost.cost_aggregator import CostAggregator, export_cost_summary_to_json, export_cost_summary_to_csv
from cost.enhanced_reporter import EnhancedCostReporter
from cost.calculator_registry import create_cost_calculation_system
from services.resource_groups_service import ResourceGroupsService


def parse_args():
    """Enhanced argument parser with cost estimation options"""
    parser = argparse.ArgumentParser(
        description='Find AWS resources tagged for a specific Kubernetes cluster with optional cost estimation'
    )
    parser.add_argument(
        '--cluster-uid',
        required=True,
        help='Kubernetes cluster UID (e.g., 16a4ede1-weblogic-g4zwl)'
    )
    parser.add_argument(
        '--region',
        default=None,
        help='AWS region (default: use AWS config/environment)'
    )
    parser.add_argument(
        '--profile',
        default=None,
        help='AWS profile to use'
    )
    parser.add_argument(
        '--services',
        nargs='+',
        help='Specific AWS services to search (default: all enabled services)'
    )
    parser.add_argument(
        '--unified-discovery',
        action='store_true',
        help='Use unified resource discovery via ResourceGroups API instead of individual services'
    )
    parser.add_argument(
        '--enrich-resources',
        action='store_true',
        help='Fetch additional resource details when using unified discovery (slower but more complete)'
    )

    # New cost estimation arguments
    parser.add_argument('--include-costs', action='store_true',
                       help='Include cost estimation in the output')
    parser.add_argument('--cost-period', default='30', type=int,
                       help='Cost analysis period in days (default: 30)')
    parser.add_argument('--forecast-days', default='90', type=int,
                       help='Cost forecast period in days (default: 90)')
    parser.add_argument('--optimization', action='store_true',
                       help='Include cost optimization suggestions')
    parser.add_argument('--export-format', choices=['json', 'csv', 'html'],
                       help='Export cost report in specified format')
    parser.add_argument('--export-file', help='Output file for cost report export')
    parser.add_argument('--comprehensive-costs', action='store_true',
                       help='Use enhanced comprehensive cost estimation with aggregation and reporting')
    parser.add_argument('--cost-validation', action='store_true',
                       help='Enable cost validation and data quality warnings')
    parser.add_argument('--cost-filter', choices=['high', 'medium', 'low', 'billable', 'free'],
                       help='Filter resources by cost level (high: ≥$50, medium: $10-50, low: <$10)')
    parser.add_argument('--sort-by-cost', action='store_true',
                       help='Sort resources by cost (highest first)')
    parser.add_argument('--cost-threshold', type=float,
                       help='Show only resources above this cost threshold (monthly USD)')

    return parser.parse_args()


def get_session(profile: str = None, region: str = None) -> boto3.Session:
    """Create boto3 session with optional profile and region"""
    session_args = {}
    if profile:
        session_args['profile_name'] = profile
    if region:
        session_args['region_name'] = region
    return boto3.Session(**session_args)


def perform_comprehensive_cost_analysis(session: boto3.Session, all_resources: dict, 
                                       cluster_uid: str, region: str, args) -> bool:
    """Perform comprehensive cost analysis using our enhanced system"""
    print("\n" + "=" * 80)
    print("🚀 COMPREHENSIVE COST ESTIMATION")
    print("=" * 80)
    
    try:
        # Flatten resources for cost calculation
        flat_resources = []
        for service_name, service_resources in all_resources.items():
            if isinstance(service_resources, dict):
                for resource_type, resource_list in service_resources.items():
                    flat_resources.extend(resource_list)
            else:
                flat_resources.extend(service_resources)
        
        if not flat_resources:
            print("No resources found for cost analysis")
            return False
        
        print(f"🔍 Analyzing costs for {len(flat_resources)} discovered resources...")
        
        # Create enhanced cost calculation system
        registry, pricing_service = create_cost_calculation_system(session)
        
        # Progress callback for batch processing
        def progress_callback(processed: int, total: int):
            percentage = (processed / total * 100) if total > 0 else 0
            print(f"  Progress: {processed}/{total} resources ({percentage:.1f}%)")
        
        # Calculate costs for all resources
        if len(flat_resources) > 10:
            print("Using batch processing for large resource set...")
            cost_results = pricing_service.calculate_batch_costs(
                flat_resources, region, args.cost_period, progress_callback
            )
        else:
            cost_results = {}
            for i, resource in enumerate(flat_resources, 1):
                print(f"  Calculating cost for resource {i}/{len(flat_resources)}: {resource.id}")
                cost_results[resource.id] = pricing_service.calculate_resource_cost_with_retry(
                    resource, region, args.cost_period
                )
        
        print(f"✓ Cost calculation complete for {len(cost_results)} resources")
        
        # Aggregate costs
        aggregator = CostAggregator()
        comprehensive_summary = aggregator.aggregate_costs(
            cost_results=cost_results,
            resources=flat_resources,
            cluster_id=cluster_uid,
            region=region,
            period_days=args.cost_period
        )
        
        # Apply cost filtering and sorting if requested
        if hasattr(args, 'cost_filter') or hasattr(args, 'sort_by_cost') or hasattr(args, 'cost_threshold'):
            comprehensive_summary = _apply_cost_filters_and_sorting(comprehensive_summary, args)
        
        # Enhanced reporting
        reporter = EnhancedCostReporter()
        
        if args.cost_validation:
            # Show detailed validation information
            print(f"\n🔍 COST VALIDATION SUMMARY:")
            validation_stats = _generate_validation_stats(cost_results, flat_resources)
            for stat_name, stat_value in validation_stats.items():
                print(f"  {stat_name}: {stat_value}")
        
        # Print comprehensive report
        reporter.print_comprehensive_cost_summary(comprehensive_summary)
        
        # Export if requested
        if args.export_format and args.export_file:
            print(f"\n📄 Exporting cost report...")
            
            if args.export_format == 'json':
                export_cost_summary_to_json(comprehensive_summary, args.export_file)
                print(f"✓ JSON report exported to: {args.export_file}")
                
            elif args.export_format == 'csv':
                export_cost_summary_to_csv(comprehensive_summary, args.export_file)
                print(f"✓ CSV report exported to: {args.export_file}")
                
            elif args.export_format == 'html':
                reporter.generate_html_report(comprehensive_summary, args.export_file)
                print(f"✓ HTML report exported to: {args.export_file}")
        
        # Show final summary
        print(f"\n🎯 COST ESTIMATION SUMMARY:")
        print(f"  Total Monthly Cost: ${comprehensive_summary.total_monthly_cost:.2f}")
        print(f"  Billable Resources: {comprehensive_summary.billable_resources}")
        print(f"  Optimization Opportunities: {len(comprehensive_summary.optimization_potential.get('optimization_suggestions', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive cost analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def _apply_cost_filters_and_sorting(summary, args):
    """Apply cost filtering and sorting to the comprehensive summary"""
    from cost.cost_aggregator import ComprehensiveCostSummary
    
    filtered_resources = summary.resource_summaries[:]  # Copy the list
    
    # Apply cost threshold filter
    if hasattr(args, 'cost_threshold') and args.cost_threshold is not None:
        filtered_resources = [r for r in filtered_resources if r.total_cost >= args.cost_threshold]
        print(f"🔍 Applied cost threshold filter: ≥${args.cost_threshold:.2f} ({len(filtered_resources)} resources)")
    
    # Apply cost level filter
    if hasattr(args, 'cost_filter') and args.cost_filter:
        original_count = len(filtered_resources)
        
        if args.cost_filter == 'high':
            filtered_resources = [r for r in filtered_resources if r.total_cost >= 50]
        elif args.cost_filter == 'medium':
            filtered_resources = [r for r in filtered_resources if 10 <= r.total_cost < 50]
        elif args.cost_filter == 'low':
            filtered_resources = [r for r in filtered_resources if 0 < r.total_cost < 10]
        elif args.cost_filter == 'billable':
            filtered_resources = [r for r in filtered_resources if r.total_cost > 0]
        elif args.cost_filter == 'free':
            filtered_resources = [r for r in filtered_resources if r.total_cost == 0]
        
        print(f"🔍 Applied cost level filter '{args.cost_filter}': {len(filtered_resources)}/{original_count} resources")
    
    # Apply sorting
    if hasattr(args, 'sort_by_cost') and args.sort_by_cost:
        filtered_resources.sort(key=lambda r: r.total_cost, reverse=True)
        print(f"📊 Sorted resources by cost (highest first)")
    
    # Recalculate aggregations for filtered data
    if len(filtered_resources) != len(summary.resource_summaries):
        # Recalculate totals and breakdowns for filtered resources
        total_cost = sum(r.total_cost for r in filtered_resources)
        billable_cost = sum(r.total_cost for r in filtered_resources if r.total_cost > 0)
        billable_count = len([r for r in filtered_resources if r.total_cost > 0])
        free_count = len(filtered_resources) - billable_count
        
        # Recalculate breakdowns
        cost_by_category = {}
        cost_by_service = {}
        cost_by_priority = {}
        
        for resource in filtered_resources:
            # Category breakdown
            if resource.cost_category not in cost_by_category:
                cost_by_category[resource.cost_category] = 0
            cost_by_category[resource.cost_category] += resource.total_cost
            
            # Service breakdown
            if resource.service not in cost_by_service:
                cost_by_service[resource.service] = 0
            cost_by_service[resource.service] += resource.total_cost
            
            # Priority breakdown
            if resource.cost_priority not in cost_by_priority:
                cost_by_priority[resource.cost_priority] = 0
            cost_by_priority[resource.cost_priority] += resource.total_cost
        
        # Create filtered summary
        filtered_summary = ComprehensiveCostSummary(
            cluster_id=summary.cluster_id,
            region=summary.region,
            analysis_date=summary.analysis_date,
            period_days=summary.period_days,
            total_monthly_cost=total_cost,
            total_billable_cost=billable_cost,
            total_resources=len(filtered_resources),
            billable_resources=billable_count,
            free_resources=free_count,
            cost_by_category=cost_by_category,
            cost_by_service=cost_by_service,
            cost_by_priority=cost_by_priority,
            cost_by_region=summary.cost_by_region,  # Keep original
            resource_summaries=filtered_resources,
            highest_cost_resources=sorted(filtered_resources, key=lambda r: r.total_cost, reverse=True)[:10],
            cost_distribution_analysis=summary.cost_distribution_analysis,  # Keep original
            optimization_potential=summary.optimization_potential  # Keep original
        )
        
        return filtered_summary
    
    return summary


def _generate_validation_stats(cost_results: dict, resources: list) -> dict:
    """Generate validation statistics for cost calculation"""
    total_resources = len(resources)
    calculated_costs = len(cost_results)
    estimated_count = sum(1 for result in cost_results.values() if result.get('is_estimated', False))
    failed_count = sum(1 for result in cost_results.values() if result.get('calculation_failed', False))
    precise_count = calculated_costs - estimated_count - failed_count
    
    return {
        'Total Resources': total_resources,
        'Costs Calculated': calculated_costs,
        'Precise Pricing': f"{precise_count} ({(precise_count/calculated_costs*100):.1f}%)" if calculated_costs > 0 else "0",
        'Estimated Pricing': f"{estimated_count} ({(estimated_count/calculated_costs*100):.1f}%)" if calculated_costs > 0 else "0",
        'Failed Calculations': failed_count,
        'Data Quality Score': f"{((precise_count + estimated_count*0.7)/calculated_costs*100):.1f}%" if calculated_costs > 0 else "0%"
    }


def main():
    """Enhanced main function with optional cost estimation

    This function orchestrates the resource discovery process:
    1. Parse command-line arguments
    2. Create AWS session
    3. Filter services if specified
    4. Discover resources using the modular framework
    5. Optional cost estimation and analysis
    6. Format and display results
    """
    args = parse_args()

    # Build tag key and value
    tag_key = f"kubernetes.io/cluster/{args.cluster_uid}"
    tag_value = "owned"

    print(f"Searching for resources with tag {tag_key}:{tag_value}")

    try:
        # Create session
        session = get_session(profile=args.profile, region=args.region)

        # Get current region
        region = session.region_name or 'us-east-1'
        print(f"Using region: {region}")

        # Configure unified discovery if requested
        if args.unified_discovery:
            SERVICE_CONFIG['ResourceGroups']['enabled'] = True
            SERVICE_CONFIG['ResourceGroups']['unified_discovery'] = True
            
        if args.enrich_resources:
            SERVICE_CONFIG['ResourceGroups']['enrich_resources'] = True
        
        # Filter services if specified
        if args.services:
            global SERVICE_REGISTRY
            SERVICE_REGISTRY = {k: v for k, v in SERVICE_REGISTRY.items() if k in args.services}

        # Discover resources with optional cost integration
        discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
        all_resources = discoverer.discover_all_resources(include_costs=args.include_costs)

        # Cost analysis if requested
        if args.include_costs or args.comprehensive_costs:
            if args.comprehensive_costs:
                # Use enhanced comprehensive cost system
                cost_success = perform_comprehensive_cost_analysis(
                    session, all_resources, args.cluster_uid, region, args
                )
                if not cost_success:
                    print("⚠️  Falling back to basic cost analysis...")
                    args.include_costs = True  # Fallback to basic system
            
            if args.include_costs and not args.comprehensive_costs:
                print("\n=== Basic Cost Analysis ===")

                try:
                    # Get cost services
                    analyzer_service = COST_SERVICE_REGISTRY['analyzer']
                    reporter_service = COST_SERVICE_REGISTRY['reporter']

                    # Set cluster UID for cost analysis
                    analyzer_service.set_cluster_uid(args.cluster_uid)

                    # Generate cost summary
                    cost_summary = discoverer.generate_cost_summary(all_resources)
                    if cost_summary:
                        reporter_service.print_cost_summary(cost_summary, args.cluster_uid)

                        # Optimization suggestions if requested
                        if args.optimization:
                            suggestions = analyzer_service.identify_optimization_opportunities(
                                [r for service_resources in all_resources.values() 
                                 for resource_list in service_resources.values() 
                                 for r in resource_list]
                            )
                            reporter_service.print_optimization_suggestions(suggestions)

                        # Export if requested (only for basic cost analysis)
                        if args.export_format and args.export_file and not args.comprehensive_costs:
                            if args.export_format == 'json':
                                reporter_service.export_to_json(cost_summary, all_resources, args.export_file)
                            elif args.export_format == 'csv':
                                reporter_service.export_to_csv(cost_summary, all_resources, args.export_file)
                            elif args.export_format == 'html':
                                reporter_service.export_to_html(cost_summary, all_resources, args.export_file)
                            print(f"\nCost report exported to: {args.export_file}")
                    else:
                        print("No cost data available for the discovered resources.")
                        
                except KeyError as e:
                    print(f"Error: Cost service '{e}' not found in registry.")
                except Exception as e:
                    print(f"Error during cost analysis: {e}")
                    print("Continuing without cost analysis...")

        # Format and display results
        ResourceFormatter.print_results(all_resources, args.cluster_uid)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()