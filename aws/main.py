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
from services import SERVICE_REGISTRY, get_available_services
from utils.formatter import ResourceFormatter
from utils.discoverer import AWSResourceDiscoverer
from cost.analyzer_service import CostAnalyzerService
from cost.reporter_service import CostReporterService
from cost.registry import COST_SERVICE_REGISTRY


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

    return parser.parse_args()


def get_session(profile: str = None, region: str = None) -> boto3.Session:
    """Create boto3 session with optional profile and region"""
    session_args = {}
    if profile:
        session_args['profile_name'] = profile
    if region:
        session_args['region_name'] = region
    return boto3.Session(**session_args)


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

        # Filter services if specified
        if args.services:
            global SERVICE_REGISTRY
            SERVICE_REGISTRY = {k: v for k, v in SERVICE_REGISTRY.items() if k in args.services}

        # Discover resources with optional cost integration
        discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
        all_resources = discoverer.discover_all_resources(include_costs=args.include_costs)

        # Cost analysis if requested
        if args.include_costs:
            print("\n=== Cost Analysis ===")

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

                    # Export if requested
                    if args.export_format and args.export_file:
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