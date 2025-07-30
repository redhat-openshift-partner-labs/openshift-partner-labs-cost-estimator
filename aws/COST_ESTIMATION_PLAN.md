# AWS Cost Explorer Integration Plan

## Overview

This document outlines a comprehensive plan for integrating AWS Cost Explorer API into the existing modular framework to provide cost estimation capabilities for discovered Kubernetes cluster resources.

## Goals

1. **Cost Discovery**: Retrieve actual costs for discovered resources
2. **Cost Forecasting**: Provide cost projections for future periods
3. **Cost Breakdown**: Show costs by service, resource type, and time period
4. **Cost Optimization**: Identify potential cost savings opportunities
5. **Reporting**: Generate detailed cost reports and summaries
6. **Modular Design**: Maintain separation of concerns and optional integration

## Architecture Design

### 1. Modular Architecture

```
aws/
├── services/                    # Existing resource discovery services
│   ├── __init__.py
│   ├── base.py
│   ├── ec2_service.py
│   ├── elb_service.py
│   └── registry.py
├── cost/                       # NEW: Cost estimation module
│   ├── __init__.py
│   ├── base.py                 # Cost service base classes
│   ├── explorer_service.py     # AWS Cost Explorer integration
│   ├── analyzer_service.py     # Cost analysis and insights
│   ├── reporter_service.py     # Cost reporting and export
│   └── registry.py             # Cost service registry
└── utils/
    ├── discoverer.py           # Enhanced with cost integration
    └── formatter.py            # Enhanced with cost display
```

### 2. Cost Module Structure

```
cost/
├── __init__.py                 # Package exports
├── base.py                     # Cost service base classes
├── explorer_service.py         # AWS Cost Explorer API integration
├── analyzer_service.py         # Cost analysis and optimization
├── reporter_service.py         # Cost reporting and export
└── registry.py                 # Cost service registry
```

### 3. Enhanced Data Structures

```python
# In cost/base.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Any, Optional

@dataclass
class CostRecord:
    """Represents a cost record for a specific time period"""
    start_date: datetime
    end_date: datetime
    amount: float
    currency: str = "USD"
    unit: str = "Hrs"  # or "GB-Mo", "Requests", etc.
    service: str
    usage_type: Optional[str] = None
    operation: Optional[str] = None
    region: Optional[str] = None

@dataclass
class CostSummary:
    """Summary of costs for a resource or group of resources"""
    total_cost: float
    currency: str = "USD"
    period_start: datetime
    period_end: datetime
    cost_breakdown: Dict[str, float]  # Service -> Cost
    resource_count: int
    average_cost_per_resource: float
    cost_trend: str  # "increasing", "decreasing", "stable"
    forecast_30_days: float
    forecast_90_days: float

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

# Enhanced ResourceInfo (backward compatible)
@dataclass
class ResourceInfo:
    """Enhanced resource information with optional cost data"""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    # Optional cost-related fields (None by default for backward compatibility)
    cost_data: Optional[Dict[str, Any]] = None
    cost_history: Optional[List['CostRecord']] = None
    cost_forecast: Optional[List['CostRecord']] = None
    optimization_suggestions: Optional[List['OptimizationSuggestion']] = None
```

## Implementation Plan

### Phase 1: Cost Module Foundation

#### 1.1 Create Cost Module Structure

```python
# cost/__init__.py
from .explorer_service import CostExplorerService
from .analyzer_service import CostAnalyzerService
from .reporter_service import CostReporterService
from .base import CostRecord, CostSummary, OptimizationSuggestion

__all__ = [
    'CostExplorerService',
    'CostAnalyzerService', 
    'CostReporterService',
    'CostRecord',
    'CostSummary',
    'OptimizationSuggestion'
]
```

#### 1.2 Cost Service Base Classes

```python
# cost/base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import boto3

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
```

#### 1.3 Cost Explorer Service

```python
# cost/explorer_service.py
from .base import CostService
from .base import CostRecord
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3

class CostExplorerService(CostService):
    """Service for interacting with AWS Cost Explorer API"""
    
    def __init__(self):
        super().__init__("CostExplorer")
    
    def get_client(self, session: boto3.Session):
        return session.client('ce')
    
    def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = 'MONTHLY',
        metrics: List[str] = None,
        group_by: List[Dict] = None,
        filter_expression: Dict = None
    ) -> Dict[str, Any]:
        """Get cost and usage data from Cost Explorer"""
        if metrics is None:
            metrics = ['UnblendedCost']
        
        try:
            response = self.client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity,
                Metrics=metrics,
                GroupBy=group_by or [],
                Filter=filter_expression
            )
            return response
        except Exception as e:
            self.handle_error(e, 'get_cost_and_usage')
            return {}
    
    def get_cost_forecast(
        self,
        start_date: datetime,
        end_date: datetime,
        metric: str = 'UNBLENDED_COST',
        granularity: str = 'MONTHLY'
    ) -> Dict[str, Any]:
        """Get cost forecast from Cost Explorer"""
        try:
            response = self.client.get_cost_forecast(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Metric=metric,
                Granularity=granularity
            )
            return response
        except Exception as e:
            self.handle_error(e, 'get_cost_forecast')
            return {}
    
    def get_reservation_coverage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = 'MONTHLY'
    ) -> Dict[str, Any]:
        """Get reservation coverage data"""
        try:
            response = self.client.get_reservation_coverage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity=granularity
            )
            return response
        except Exception as e:
            self.handle_error(e, 'get_reservation_coverage')
            return {}
```

#### 1.4 Cost Analyzer Service

```python
# cost/analyzer_service.py
from .base import CostService, CostRecord, CostSummary, OptimizationSuggestion
from .explorer_service import CostExplorerService
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class CostAnalyzerService(CostService):
    """Analyzes cost data and provides insights"""
    
    def __init__(self):
        super().__init__("CostAnalyzer")
        self.explorer_service: Optional[CostExplorerService] = None
    
    def set_explorer_service(self, explorer_service: CostExplorerService):
        """Set the cost explorer service"""
        self.explorer_service = explorer_service
    
    def get_client(self, session: boto3.Session):
        # Cost analyzer doesn't need a direct client
        return None
    
    def analyze_resource_costs(
        self,
        resources: List['ResourceInfo'],
        start_date: datetime,
        end_date: datetime
    ) -> List['ResourceInfo']:
        """Analyze costs for a list of resources"""
        if not self.explorer_service:
            return resources
        
        for resource in resources:
            # Get cost data for this resource
            cost_data = self._get_resource_cost_data(resource, start_date, end_date)
            if cost_data:
                resource.cost_data = cost_data
                resource.cost_history = self._create_cost_records(cost_data)
                resource.cost_forecast = self._get_cost_forecast(resource, end_date)
                resource.optimization_suggestions = self._get_optimization_suggestions(resource)
        
        return resources
    
    def generate_cost_summary(
        self,
        resources: List['ResourceInfo'],
        period_start: datetime,
        period_end: datetime
    ) -> CostSummary:
        """Generate cost summary for resources"""
        total_cost = 0.0
        cost_breakdown = {}
        resource_count = len(resources)
        
        for resource in resources:
            if resource.cost_data:
                cost = resource.cost_data.get('total_cost', 0.0)
                total_cost += cost
                service = resource.cost_data.get('service', 'Unknown')
                cost_breakdown[service] = cost_breakdown.get(service, 0.0) + cost
        
        average_cost = total_cost / resource_count if resource_count > 0 else 0.0
        
        # Calculate cost trend (simplified)
        cost_trend = self._calculate_cost_trend(resources)
        
        # Get forecasts
        forecast_30 = self._calculate_forecast(resources, 30)
        forecast_90 = self._calculate_forecast(resources, 90)
        
        return CostSummary(
            total_cost=total_cost,
            period_start=period_start,
            period_end=period_end,
            cost_breakdown=cost_breakdown,
            resource_count=resource_count,
            average_cost_per_resource=average_cost,
            cost_trend=cost_trend,
            forecast_30_days=forecast_30,
            forecast_90_days=forecast_90
        )
    
    def identify_optimization_opportunities(
        self,
        resources: List['ResourceInfo']
    ) -> List[OptimizationSuggestion]:
        """Identify cost optimization opportunities"""
        suggestions = []
        
        for resource in resources:
            if not resource.cost_data:
                continue
            
            # Analyze for optimization opportunities
            resource_suggestions = self._analyze_resource_optimization(resource)
            suggestions.extend(resource_suggestions)
        
        return suggestions
    
    def _get_resource_cost_data(
        self,
        resource: 'ResourceInfo',
        start_date: datetime,
        end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        """Get cost data for a specific resource"""
        if not self.explorer_service:
            return None
        
        # Create filter for this specific resource
        filter_expression = {
            'Tags': {
                'Key': 'kubernetes.io/cluster/resource-id',
                'Values': [resource.id]
            }
        }
        
        response = self.explorer_service.get_cost_and_usage(
            start_date, end_date, filter_expression=filter_expression
        )
        
        # Process response and extract cost data
        return self._process_cost_response(response)
    
    def _process_cost_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process Cost Explorer response into standardized format"""
        # Implementation to process AWS Cost Explorer response
        # and extract relevant cost information
        pass
    
    def _create_cost_records(self, cost_data: Dict[str, Any]) -> List[CostRecord]:
        """Create CostRecord objects from cost data"""
        # Implementation to create CostRecord objects
        pass
    
    def _get_cost_forecast(
        self,
        resource: 'ResourceInfo',
        end_date: datetime
    ) -> List[CostRecord]:
        """Get cost forecast for a resource"""
        # Implementation for cost forecasting
        pass
    
    def _get_optimization_suggestions(
        self,
        resource: 'ResourceInfo'
    ) -> List[OptimizationSuggestion]:
        """Get optimization suggestions for a resource"""
        # Implementation for optimization analysis
        pass
    
    def _calculate_cost_trend(self, resources: List['ResourceInfo']) -> str:
        """Calculate cost trend (increasing, decreasing, stable)"""
        # Implementation for trend calculation
        pass
    
    def _calculate_forecast(self, resources: List['ResourceInfo'], days: int) -> float:
        """Calculate cost forecast for specified number of days"""
        # Implementation for cost forecasting
        pass
    
    def _analyze_resource_optimization(self, resource: 'ResourceInfo') -> List[OptimizationSuggestion]:
        """Analyze a resource for optimization opportunities"""
        # Implementation for optimization analysis
        pass
```

#### 1.5 Cost Reporter Service

```python
# cost/reporter_service.py
from .base import CostService, CostSummary, OptimizationSuggestion
from typing import Dict, List, Any
import json
import csv
from datetime import datetime

class CostReporterService(CostService):
    """Service for generating cost reports and exports"""
    
    def __init__(self):
        super().__init__("CostReporter")
    
    def get_client(self, session):
        # Reporter doesn't need a direct client
        return None
    
    def print_cost_summary(self, cost_summary: CostSummary, cluster_uid: str):
        """Print detailed cost summary"""
        print(f"\n=== Cost Summary for Cluster: {cluster_uid} ===")
        print(f"Period: {cost_summary.period_start.date()} to {cost_summary.period_end.date()}")
        print(f"Total Cost: ${cost_summary.total_cost:.2f} {cost_summary.currency}")
        print(f"Resources: {cost_summary.resource_count}")
        print(f"Average Cost per Resource: ${cost_summary.average_cost_per_resource:.2f}")
        print(f"Cost Trend: {cost_summary.cost_trend}")
        print(f"30-day Forecast: ${cost_summary.forecast_30_days:.2f}")
        print(f"90-day Forecast: ${cost_summary.forecast_90_days:.2f}")
        
        print("\nCost Breakdown by Service:")
        for service, cost in cost_summary.cost_breakdown.items():
            print(f"  {service}: ${cost:.2f}")
    
    def print_optimization_suggestions(self, suggestions: List[OptimizationSuggestion]):
        """Print cost optimization suggestions"""
        if not suggestions:
            print("\nNo optimization suggestions found.")
            return
        
        print(f"\n=== Cost Optimization Suggestions ({len(suggestions)}) ===")
        total_savings = sum(s.potential_savings for s in suggestions)
        print(f"Total Potential Savings: ${total_savings:.2f}")
        
        for suggestion in suggestions:
            print(f"\nResource: {suggestion.resource_id}")
            print(f"Type: {suggestion.suggestion_type}")
            print(f"Current Cost: ${suggestion.current_cost:.2f}")
            print(f"Potential Savings: ${suggestion.potential_savings:.2f}")
            print(f"Risk Level: {suggestion.risk_level}")
            print(f"Description: {suggestion.description}")
    
    def export_to_json(
        self,
        cost_summary: CostSummary,
        resources: Dict[str, List['ResourceInfo']],
        filename: str
    ):
        """Export cost report to JSON format"""
        report_data = {
            'cost_summary': {
                'total_cost': cost_summary.total_cost,
                'currency': cost_summary.currency,
                'period_start': cost_summary.period_start.isoformat(),
                'period_end': cost_summary.period_end.isoformat(),
                'resource_count': cost_summary.resource_count,
                'average_cost_per_resource': cost_summary.average_cost_per_resource,
                'cost_trend': cost_summary.cost_trend,
                'forecast_30_days': cost_summary.forecast_30_days,
                'forecast_90_days': cost_summary.forecast_90_days,
                'cost_breakdown': cost_summary.cost_breakdown
            },
            'resources': self._serialize_resources(resources),
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(report_data, f, indent=2)
    
    def export_to_csv(
        self,
        cost_summary: CostSummary,
        resources: Dict[str, List['ResourceInfo']],
        filename: str
    ):
        """Export cost report to CSV format"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Write cost summary
            writer.writerow(['Cost Summary'])
            writer.writerow(['Total Cost', cost_summary.total_cost])
            writer.writerow(['Currency', cost_summary.currency])
            writer.writerow(['Resource Count', cost_summary.resource_count])
            writer.writerow(['Average Cost per Resource', cost_summary.average_cost_per_resource])
            writer.writerow(['Cost Trend', cost_summary.cost_trend])
            writer.writerow(['30-day Forecast', cost_summary.forecast_30_days])
            writer.writerow(['90-day Forecast', cost_summary.forecast_90_days])
            writer.writerow([])
            
            # Write cost breakdown
            writer.writerow(['Cost Breakdown by Service'])
            for service, cost in cost_summary.cost_breakdown.items():
                writer.writerow([service, cost])
            writer.writerow([])
            
            # Write resource details
            writer.writerow(['Resource Details'])
            writer.writerow(['Service', 'Resource Type', 'ID', 'Name', 'State', 'Cost'])
            for service_name, resource_list in resources.items():
                for resource in resource_list:
                    cost = resource.cost_data.get('total_cost', 0.0) if resource.cost_data else 0.0
                    writer.writerow([
                        service_name,
                        resource.type or 'Unknown',
                        resource.id,
                        resource.name or resource.id,
                        resource.state or 'Unknown',
                        cost
                    ])
    
    def _serialize_resources(self, resources: Dict[str, List['ResourceInfo']]) -> Dict[str, List[Dict]]:
        """Serialize resources for JSON export"""
        serialized = {}
        for service_name, resource_list in resources.items():
            serialized[service_name] = []
            for resource in resource_list:
                resource_data = {
                    'id': resource.id,
                    'name': resource.name,
                    'type': resource.type,
                    'state': resource.state,
                    'region': resource.region,
                    'cost_data': resource.cost_data
                }
                serialized[service_name].append(resource_data)
        return serialized
```

#### 1.6 Cost Registry

```python
# cost/registry.py
from .explorer_service import CostExplorerService
from .analyzer_service import CostAnalyzerService
from .reporter_service import CostReporterService

# Cost Service Registry
COST_SERVICE_REGISTRY = {
    'explorer': CostExplorerService(),
    'analyzer': CostAnalyzerService(),
    'reporter': CostReporterService(),
}

# Cost Service Configuration
COST_SERVICE_CONFIG = {
    'explorer': {'enabled': True},
    'analyzer': {'enabled': True},
    'reporter': {'enabled': True},
}

def get_available_cost_services():
    """Get list of available cost service names"""
    return list(COST_SERVICE_REGISTRY.keys())

def get_cost_service_config(service_name: str):
    """Get configuration for a specific cost service"""
    return COST_SERVICE_CONFIG.get(service_name, {})

def is_cost_service_enabled(service_name: str) -> bool:
    """Check if a cost service is enabled"""
    return COST_SERVICE_CONFIG.get(service_name, {}).get('enabled', True)
```

### Phase 2: Enhanced Service Integration

#### 2.1 Enhanced AWSService Base Class

```python
# services/base.py (updated)
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import boto3
from botocore.exceptions import ClientError

@dataclass
class ResourceInfo:
    """Enhanced resource information with optional cost data"""
    id: str
    name: Optional[str] = None
    type: Optional[str] = None
    state: Optional[str] = None
    region: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None
    # Optional cost-related fields (None by default for backward compatibility)
    cost_data: Optional[Dict[str, Any]] = None
    cost_history: Optional[List['CostRecord']] = None
    cost_forecast: Optional[List['CostRecord']] = None
    optimization_suggestions: Optional[List['OptimizationSuggestion']] = None

class AWSService(ABC):
    """Enhanced abstract base class with optional cost estimation support"""
    
    def __init__(self, service_name: str, resource_types: List[str]):
        self.service_name = service_name
        self.resource_types = resource_types
        self.cost_analyzer: Optional['CostAnalyzerService'] = None
    
    @abstractmethod
    def get_client(self, session: boto3.Session):
        """Return the appropriate AWS client for this service"""
        pass
    
    @abstractmethod
    def search_resources(self, client, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        """Search for resources with the specified tag"""
        pass
    
    def handle_error(self, error: ClientError, resource_type: str):
        """Standardized error handling"""
        print(f"Error searching {self.service_name} {resource_type}: {error}")
    
    # Optional cost integration methods
    def set_cost_analyzer(self, cost_analyzer: 'CostAnalyzerService'):
        """Set the cost analyzer for this service (optional)"""
        self.cost_analyzer = cost_analyzer
    
    def enrich_resources_with_costs(
        self,
        resources: Dict[str, List[ResourceInfo]],
        start_date: 'datetime',
        end_date: 'datetime'
    ) -> Dict[str, List[ResourceInfo]]:
        """Enrich discovered resources with cost information (optional)"""
        if not self.cost_analyzer:
            return resources
        
        for resource_type, resource_list in resources.items():
            enriched_resources = self.cost_analyzer.analyze_resource_costs(
                resource_list, start_date, end_date
            )
            resources[resource_type] = enriched_resources
        
        return resources
```

#### 2.2 Enhanced Resource Discoverer

```python
# utils/discoverer.py (updated)
from services import SERVICE_REGISTRY
from cost import CostExplorerService, CostAnalyzerService, CostReporterService
from cost.registry import COST_SERVICE_REGISTRY
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import boto3

class AWSResourceDiscoverer:
    """Enhanced resource discoverer with optional cost integration"""
    
    def __init__(self, session: boto3.Session, tag_key: str, tag_value: str):
        self.session = session
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.cost_services: Optional[Dict[str, Any]] = None
    
    def discover_all_resources(self, include_costs: bool = False) -> Dict[str, Dict[str, List['ResourceInfo']]]:
        """Discover all resources with optional cost integration"""
        all_resources = {}
        
        for service_name, service in SERVICE_REGISTRY.items():
            print(f"Searching {service_name} resources...")
            client = service.get_client(self.session)
            resources = service.search_resources(client, self.tag_key, self.tag_value)
            all_resources[service_name] = resources
        
        # Optional cost enrichment
        if include_costs:
            all_resources = self._enrich_with_costs(all_resources)
        
        return all_resources
    
    def _enrich_with_costs(
        self,
        all_resources: Dict[str, Dict[str, List['ResourceInfo']]]
    ) -> Dict[str, Dict[str, List['ResourceInfo']]]:
        """Enrich resources with cost information"""
        # Initialize cost services
        explorer_service = COST_SERVICE_REGISTRY['explorer']
        analyzer_service = COST_SERVICE_REGISTRY['analyzer']
        
        # Set up cost analyzer
        explorer_service.client = explorer_service.get_client(self.session)
        analyzer_service.set_explorer_service(explorer_service)
        
        # Calculate date range for cost analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)  # Default 30 days
        
        # Enrich each service's resources with costs
        for service_name, service in SERVICE_REGISTRY.items():
            if service_name in all_resources:
                service.set_cost_analyzer(analyzer_service)
                all_resources[service_name] = service.enrich_resources_with_costs(
                    all_resources[service_name], start_date, end_date
                )
        
        return all_resources
    
    def generate_cost_summary(
        self,
        all_resources: Dict[str, Dict[str, List['ResourceInfo']]]
    ) -> Optional['CostSummary']:
        """Generate cost summary for all resources"""
        if not self.cost_services:
            return None
        
        analyzer_service = self.cost_services['analyzer']
        
        # Flatten all resources into a single list
        all_resource_list = []
        for service_resources in all_resources.values():
            for resource_list in service_resources.values():
                all_resource_list.extend(resource_list)
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        return analyzer_service.generate_cost_summary(
            all_resource_list, start_date, end_date
        )
```

### Phase 3: Enhanced Formatter

#### 3.1 Enhanced Resource Formatter

```python
# utils/formatter.py (updated)
from services.base import ResourceInfo
from cost.base import CostSummary, OptimizationSuggestion
from typing import Dict, List

class ResourceFormatter:
    """Enhanced formatter with cost information display"""
    
    @staticmethod
    def format_resource_info(resource: ResourceInfo) -> str:
        """Format basic resource information"""
        info_parts = [f"ID: {resource.id}"]
        
        if resource.name and resource.name != resource.id:
            info_parts.append(f"Name: {resource.name}")
        
        if resource.type:
            info_parts.append(f"Type: {resource.type}")
        
        if resource.state:
            info_parts.append(f"State: {resource.state}")
        
        if resource.region:
            info_parts.append(f"Region: {resource.region}")
        
        return " | ".join(info_parts)
    
    @staticmethod
    def format_resource_with_costs(resource: ResourceInfo) -> str:
        """Format a resource with cost information"""
        base_info = ResourceFormatter.format_resource_info(resource)
        
        if resource.cost_data:
            cost_info = f" | Cost: ${resource.cost_data.get('total_cost', 0):.2f}"
            if resource.cost_forecast:
                forecast = resource.cost_forecast[0].amount if resource.cost_forecast else 0
                cost_info += f" | 30-day forecast: ${forecast:.2f}"
            base_info += cost_info
        
        return base_info
    
    @staticmethod
    def print_results(all_resources: Dict[str, Dict[str, List[ResourceInfo]]], cluster_uid: str):
        """Print all discovered resources with optional cost information"""
        print(f"\n=== Discovered Resources for Cluster: {cluster_uid} ===")
        
        total_resources = 0
        for service_name, service_resources in all_resources.items():
            service_total = sum(len(resources) for resources in service_resources.values())
            total_resources += service_total
            
            if service_total > 0:
                print(f"\n{service_name} Resources ({service_total}):")
                for resource_type, resources in service_resources.items():
                    if resources:
                        print(f"  {resource_type.title()} ({len(resources)}):")
                        for resource in resources:
                            formatted = ResourceFormatter.format_resource_with_costs(resource)
                            print(f"    {formatted}")
        
        print(f"\nTotal Resources Found: {total_resources}")
    
    @staticmethod
    def print_cost_summary(cost_summary: CostSummary, cluster_uid: str):
        """Print detailed cost summary"""
        print(f"\n=== Cost Summary for Cluster: {cluster_uid} ===")
        print(f"Period: {cost_summary.period_start.date()} to {cost_summary.period_end.date()}")
        print(f"Total Cost: ${cost_summary.total_cost:.2f} {cost_summary.currency}")
        print(f"Resources: {cost_summary.resource_count}")
        print(f"Average Cost per Resource: ${cost_summary.average_cost_per_resource:.2f}")
        print(f"Cost Trend: {cost_summary.cost_trend}")
        print(f"30-day Forecast: ${cost_summary.forecast_30_days:.2f}")
        print(f"90-day Forecast: ${cost_summary.forecast_90_days:.2f}")
        
        print("\nCost Breakdown by Service:")
        for service, cost in cost_summary.cost_breakdown.items():
            print(f"  {service}: ${cost:.2f}")
    
    @staticmethod
    def print_optimization_suggestions(suggestions: List[OptimizationSuggestion]):
        """Print cost optimization suggestions"""
        if not suggestions:
            print("\nNo optimization suggestions found.")
            return
        
        print(f"\n=== Cost Optimization Suggestions ({len(suggestions)}) ===")
        total_savings = sum(s.potential_savings for s in suggestions)
        print(f"Total Potential Savings: ${total_savings:.2f}")
        
        for suggestion in suggestions:
            print(f"\nResource: {suggestion.resource_id}")
            print(f"Type: {suggestion.suggestion_type}")
            print(f"Current Cost: ${suggestion.current_cost:.2f}")
            print(f"Potential Savings: ${suggestion.potential_savings:.2f}")
            print(f"Risk Level: {suggestion.risk_level}")
            print(f"Description: {suggestion.description}")
```

### Phase 4: Command Line Integration

#### 4.1 Enhanced Command Line Arguments

```python
# main.py (updated)
import argparse
import sys
from datetime import datetime, timedelta
from utils.discoverer import AWSResourceDiscoverer
from utils.formatter import ResourceFormatter
from cost import CostAnalyzerService, CostReporterService
from cost.registry import COST_SERVICE_REGISTRY

def parse_args():
    """Enhanced argument parser with cost estimation options"""
    parser = argparse.ArgumentParser(
        description='Find AWS resources tagged for a specific Kubernetes cluster with optional cost estimation'
    )
    
    # Existing arguments
    parser.add_argument('--cluster-uid', required=True, help='Kubernetes cluster UID')
    parser.add_argument('--region', default=None, help='AWS region')
    parser.add_argument('--profile', default=None, help='AWS profile to use')
    parser.add_argument('--services', nargs='+', help='Specific AWS services to search')
    
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

def main():
    """Enhanced main function with optional cost estimation"""
    args = parse_args()
    
    # Build tag key and value
    tag_key = f"kubernetes.io/cluster/{args.cluster_uid}"
    tag_value = "owned"
    
    print(f"Searching for resources with tag {tag_key}:{tag_value}")
    
    try:
        # Create session
        session = get_session(profile=args.profile, region=args.region)
        region = session.region_name or 'default'
        print(f"Using region: {region}")
        
        # Filter services if specified
        if args.services:
            from services import SERVICE_REGISTRY
            global SERVICE_REGISTRY
            SERVICE_REGISTRY = {k: v for k, v in SERVICE_REGISTRY.items() if k in args.services}
        
        # Discover resources with optional cost integration
        discoverer = AWSResourceDiscoverer(session, tag_key, tag_value)
        all_resources = discoverer.discover_all_resources(include_costs=args.include_costs)
        
        # Cost analysis if requested
        if args.include_costs:
            print("\n=== Cost Analysis ===")
            
            # Get cost services
            analyzer_service = COST_SERVICE_REGISTRY['analyzer']
            reporter_service = COST_SERVICE_REGISTRY['reporter']
            
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
                    print(f"\nCost report exported to: {args.export_file}")
        
        # Print results
        ResourceFormatter.print_results(all_resources, args.cluster_uid)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Implementation Timeline

### Week 1: Cost Module Foundation
- [ ] Create `cost/` module structure
- [ ] Implement `CostExplorerService` with AWS Cost Explorer API integration
- [ ] Create cost data structures (`CostRecord`, `CostSummary`, `OptimizationSuggestion`)
- [ ] Add unit tests for cost services

### Week 2: Cost Analysis and Integration
- [ ] Implement `CostAnalyzerService` with cost analysis logic
- [ ] Implement `CostReporterService` with reporting capabilities
- [ ] Create cost service registry and configuration
- [ ] Enhance `ResourceInfo` with optional cost fields (backward compatible)

### Week 3: Service Integration
- [ ] Update `AWSService` base class with optional cost integration
- [ ] Enhance `AWSResourceDiscoverer` with cost enrichment capabilities
- [ ] Update `ResourceFormatter` with cost display functionality
- [ ] Ensure backward compatibility with existing services

### Week 4: Command Line Integration and Testing
- [ ] Update command line interface with cost estimation options
- [ ] Integrate cost estimation into main workflow
- [ ] Comprehensive testing with real AWS data
- [ ] Performance optimization and error handling
- [ ] Documentation updates

## Key Changes from Original Plan

### 1. **Modular Architecture**
- **Separate Cost Module**: Cost services are now in their own `cost/` module
- **Optional Integration**: Existing services work with or without cost estimation
- **Backward Compatibility**: Enhanced `ResourceInfo` maintains compatibility

### 2. **Service Registry Pattern**
- **Cost Service Registry**: Follows same pattern as existing service registry
- **Configuration Management**: Centralized cost service configuration
- **Dynamic Discovery**: Easy to add new cost services

### 3. **Enhanced Base Classes**
- **CostService Base Class**: Abstract base for all cost-related services
- **CostEnrichmentMixin**: Optional mixin for existing services
- **Enhanced AWSService**: Optional cost integration methods

### 4. **Improved Separation of Concerns**
- **Cost Explorer**: Handles AWS Cost Explorer API interactions
- **Cost Analyzer**: Handles cost analysis and optimization
- **Cost Reporter**: Handles reporting and export functionality

### 5. **Flexible Integration**
- **Optional Cost Analysis**: Can be enabled/disabled via command line
- **Service-Specific Cost Logic**: Each service can implement custom cost logic
- **Configurable Cost Periods**: Flexible date ranges for cost analysis

## Benefits of Updated Architecture

1. **Modularity**: Clear separation between resource discovery and cost estimation
2. **Extensibility**: Easy to add new cost services or modify existing ones
3. **Backward Compatibility**: Existing code continues to work without changes
4. **Optional Integration**: Cost estimation can be enabled/disabled as needed
5. **Consistent Patterns**: Follows same architectural patterns as existing services
6. **Testability**: Each cost service can be tested independently
7. **Configuration**: Centralized configuration management for cost services

## Usage Examples

### Basic Resource Discovery (No Changes)
```bash
python main.py --cluster-uid my-cluster-123
```

### Resource Discovery with Cost Estimation
```bash
python main.py --cluster-uid my-cluster-123 --include-costs
```

### Detailed Cost Analysis with Optimization
```bash
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --cost-period 60 \
    --forecast-days 180 \
    --optimization
```

### Export Cost Report
```bash
python main.py --cluster-uid my-cluster-123 \
    --include-costs \
    --export-format json \
    --export-file cost_report.json
```

This updated plan maintains the modular architecture while providing comprehensive cost estimation capabilities that integrate seamlessly with the existing resource discovery framework. 