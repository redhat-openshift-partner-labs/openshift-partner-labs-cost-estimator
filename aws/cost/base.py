"""
Base classes and shared types for cost estimation services.
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime
import boto3


@dataclass
class CostRecord:
    """Represents a cost record for a specific time period"""
    start_date: datetime
    end_date: datetime
    amount: float
    service: str
    currency: str = "USD"
    unit: str = "Hrs"  # or "GB-Mo", "Requests", etc.
    usage_type: Optional[str] = None
    operation: Optional[str] = None
    region: Optional[str] = None


@dataclass
class CostSummary:
    """Summary of costs for a resource or group of resources"""
    total_cost: float
    period_start: datetime
    period_end: datetime
    cost_breakdown: Dict[str, float]  # Service -> Cost
    resource_count: int
    average_cost_per_resource: float
    cost_trend: str  # "increasing", "decreasing", "stable"
    forecast_30_days: float
    forecast_90_days: float
    currency: str = "USD"


@dataclass
class OptimizationSuggestion:
    """Cost optimization suggestion"""
    resource_id: str
    resource_type: str
    current_cost: float
    potential_savings: float
    suggestion_type: str  # "resize", "reserved_instance", "delete", "schedule"
    description: str
    implementation_steps: List[str]
    risk_level: str  # "low", "medium", "high"


class CostService(ABC):
    """Abstract base class for cost-related services"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
    
    @abstractmethod
    def get_client(self, session: boto3.Session):
        """Return the appropriate AWS client for this service"""
        pass
    
    def handle_error(self, error: Exception, operation: str):
        """Standardized error handling for cost services"""
        print(f"Error in {self.service_name} {operation}: {error}")


class CostEnrichmentMixin:
    """Mixin to add cost enrichment capabilities to existing services"""
    
    def __init__(self):
        self.cost_analyzer: Optional['CostAnalyzerService'] = None
    
    def set_cost_analyzer(self, cost_analyzer: 'CostAnalyzerService'):
        """Set the cost analyzer for this service"""
        self.cost_analyzer = cost_analyzer
    
    def enrich_resources_with_costs(
        self,
        resources: List['ResourceInfo'],
        start_date: datetime,
        end_date: datetime
    ) -> List['ResourceInfo']:
        """Enrich discovered resources with cost information"""
        if not self.cost_analyzer:
            return resources
        
        return self.cost_analyzer.analyze_resource_costs(
            resources, start_date, end_date
        ) 