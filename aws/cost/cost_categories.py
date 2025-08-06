"""
Cost classification system for AWS resources.

This module provides enums and utilities for categorizing AWS resources
by their cost characteristics and billing patterns.
"""

from enum import Enum
from typing import Dict, List, Optional


class CostCategory(Enum):
    """Primary cost categories for AWS resources"""
    BILLABLE_COMPUTE = "billable_compute"      # EC2 instances, Lambda functions
    BILLABLE_STORAGE = "billable_storage"      # EBS volumes, S3 buckets
    BILLABLE_NETWORKING = "billable_networking"  # NAT gateways, VPC endpoints, EIPs
    BILLABLE_DATABASE = "billable_database"    # RDS instances and clusters
    BILLABLE_LOAD_BALANCING = "billable_load_balancing"  # ALB, NLB, CLB
    BILLABLE_DNS = "billable_dns"              # Route53 hosted zones
    FREE_NETWORKING = "free_networking"        # VPCs, subnets, route tables, IGWs
    FREE_SECURITY = "free_security"            # Security groups, NACLs
    FREE_IAM = "free_iam"                      # IAM roles, policies
    FREE_MANAGEMENT = "free_management"        # CloudFormation stacks
    UNKNOWN = "unknown"                        # Unclassified resources


class CostPriority(Enum):
    """Cost estimation priority levels"""
    HIGH = "high"        # Expensive resources that significantly impact costs
    MEDIUM = "medium"    # Moderate cost resources
    LOW = "low"          # Low cost resources
    FREE = "free"        # No cost resources
    UNKNOWN = "unknown"  # Unknown cost impact


class CostEstimationConfidence(Enum):
    """Confidence levels for cost estimates"""
    HIGH = "high"        # Direct AWS Pricing API data
    MEDIUM = "medium"    # Fallback pricing with known accuracy
    LOW = "low"          # Estimated pricing based on patterns
    VERY_LOW = "very_low"  # Rough estimates for unknown resources


class CostClassifier:
    """Utility class for classifying resources by cost characteristics"""
    
    # Mapping of resource categories to cost categories
    RESOURCE_COST_MAPPING: Dict[str, CostCategory] = {
        # Compute resources
        'instances': CostCategory.BILLABLE_COMPUTE,
        'lambda_functions': CostCategory.BILLABLE_COMPUTE,
        
        # Storage resources
        'volumes': CostCategory.BILLABLE_STORAGE,
        's3_buckets': CostCategory.BILLABLE_STORAGE,
        
        # Networking - billable
        'nat_gateways': CostCategory.BILLABLE_NETWORKING,
        'elastic_ips': CostCategory.BILLABLE_NETWORKING,
        'vpc_endpoints': CostCategory.BILLABLE_NETWORKING,
        
        # Load balancing
        'classic_elbs': CostCategory.BILLABLE_LOAD_BALANCING,
        'albs_nlbs': CostCategory.BILLABLE_LOAD_BALANCING,
        'target_groups': CostCategory.FREE_NETWORKING,  # Target groups themselves are free
        
        # Database
        'rds_instances': CostCategory.BILLABLE_DATABASE,
        'rds_clusters': CostCategory.BILLABLE_DATABASE,
        
        # DNS
        'route53_zones': CostCategory.BILLABLE_DNS,
        'route53_records': CostCategory.BILLABLE_DNS,
        
        # Free networking
        'vpcs': CostCategory.FREE_NETWORKING,
        'subnets': CostCategory.FREE_NETWORKING,
        'route_tables': CostCategory.FREE_NETWORKING,
        'internet_gateways': CostCategory.FREE_NETWORKING,
        'network_interfaces': CostCategory.FREE_NETWORKING,
        
        # Free security
        'security_groups': CostCategory.FREE_SECURITY,
        
        # Free IAM
        'iam_roles': CostCategory.FREE_IAM,
        'iam_policies': CostCategory.FREE_IAM,
        
        # Free management
        'cloudformation_stacks': CostCategory.FREE_MANAGEMENT,
        
        # Unknown
        'other_resources': CostCategory.UNKNOWN
    }
    
    # Mapping of cost categories to priority levels
    COST_PRIORITY_MAPPING: Dict[CostCategory, CostPriority] = {
        CostCategory.BILLABLE_COMPUTE: CostPriority.HIGH,
        CostCategory.BILLABLE_STORAGE: CostPriority.MEDIUM,
        CostCategory.BILLABLE_NETWORKING: CostPriority.HIGH,
        CostCategory.BILLABLE_DATABASE: CostPriority.HIGH,
        CostCategory.BILLABLE_LOAD_BALANCING: CostPriority.MEDIUM,
        CostCategory.BILLABLE_DNS: CostPriority.LOW,
        CostCategory.FREE_NETWORKING: CostPriority.FREE,
        CostCategory.FREE_SECURITY: CostPriority.FREE,
        CostCategory.FREE_IAM: CostPriority.FREE,
        CostCategory.FREE_MANAGEMENT: CostPriority.FREE,
        CostCategory.UNKNOWN: CostPriority.UNKNOWN
    }
    
    @classmethod
    def get_cost_category(cls, resource_type: str) -> CostCategory:
        """Get the cost category for a resource type"""
        return cls.RESOURCE_COST_MAPPING.get(resource_type, CostCategory.UNKNOWN)
    
    @classmethod
    def get_cost_priority(cls, resource_type: str) -> CostPriority:
        """Get the cost priority for a resource type"""
        cost_category = cls.get_cost_category(resource_type)
        return cls.COST_PRIORITY_MAPPING.get(cost_category, CostPriority.UNKNOWN)
    
    @classmethod
    def is_billable(cls, resource_type: str) -> bool:
        """Check if a resource type is billable"""
        cost_category = cls.get_cost_category(resource_type)
        return cost_category.value.startswith('billable_')
    
    @classmethod
    def is_free(cls, resource_type: str) -> bool:
        """Check if a resource type is free"""
        cost_category = cls.get_cost_category(resource_type)
        return cost_category.value.startswith('free_')
    
    @classmethod
    def get_billable_resources(cls, resource_types: List[str]) -> List[str]:
        """Filter resource types to only billable ones"""
        return [rt for rt in resource_types if cls.is_billable(rt)]
    
    @classmethod
    def get_free_resources(cls, resource_types: List[str]) -> List[str]:
        """Filter resource types to only free ones"""
        return [rt for rt in resource_types if cls.is_free(rt)]
    
    @classmethod
    def get_high_priority_resources(cls, resource_types: List[str]) -> List[str]:
        """Filter resource types to only high-priority (expensive) ones"""
        return [rt for rt in resource_types if cls.get_cost_priority(rt) == CostPriority.HIGH]


def get_cost_summary_by_category(resource_counts: Dict[str, int]) -> Dict[CostCategory, int]:
    """Summarize resource counts by cost category"""
    summary = {}
    
    for resource_type, count in resource_counts.items():
        cost_category = CostClassifier.get_cost_category(resource_type)
        if cost_category not in summary:
            summary[cost_category] = 0
        summary[cost_category] += count
    
    return summary


def get_cost_impact_analysis(resource_counts: Dict[str, int]) -> Dict[str, any]:
    """Analyze the potential cost impact of discovered resources"""
    total_resources = sum(resource_counts.values())
    billable_count = sum(count for rt, count in resource_counts.items() 
                        if CostClassifier.is_billable(rt))
    free_count = sum(count for rt, count in resource_counts.items() 
                    if CostClassifier.is_free(rt))
    high_priority_count = sum(count for rt, count in resource_counts.items() 
                             if CostClassifier.get_cost_priority(rt) == CostPriority.HIGH)
    
    return {
        'total_resources': total_resources,
        'billable_resources': billable_count,
        'free_resources': free_count,
        'high_cost_resources': high_priority_count,
        'billable_percentage': (billable_count / total_resources * 100) if total_resources > 0 else 0,
        'high_cost_percentage': (high_priority_count / total_resources * 100) if total_resources > 0 else 0,
        'cost_category_summary': get_cost_summary_by_category(resource_counts)
    }