"""
Cost estimation module for AWS resource discovery.

This module provides cost estimation capabilities for discovered AWS resources
using the AWS Cost Explorer API. It follows the same modular patterns as the
services module for consistency and maintainability.
"""

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