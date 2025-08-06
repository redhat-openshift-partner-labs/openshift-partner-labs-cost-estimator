# AWS Resource Groups Tagging API Migration Plan

## Executive Summary

This document outlines a plan to replace the current modular AWS service discovery architecture with a unified approach using the AWS Resource Groups Tagging API. This change will simplify the codebase, improve performance, and provide automatic support for new AWS services without requiring additional code changes.

## Current Architecture Analysis

### Existing Modular Approach

The current system implements a service registry pattern with individual AWS service modules:

```
aws/
├── services/
│   ├── base.py           # AWSService abstract base class
│   ├── ec2_service.py    # EC2-specific resource discovery
│   ├── elb_service.py    # ELB-specific resource discovery
│   └── registry.py       # Service registration and configuration
├── utils/
│   └── discoverer.py     # AWSResourceDiscoverer orchestration
└── main.py               # CLI interface
```

#### Current Workflow
1. **Service Registration**: Each AWS service is implemented as a separate class inheriting from `AWSService`
2. **Individual API Calls**: Each service makes paginated API calls with tag filters:
   - EC2: `describe_instances`, `describe_volumes`, `describe_security_groups`, `describe_network_interfaces`
   - ELB: `describe_load_balancers`, `describe_target_groups`
3. **Tag-based Discovery**: Resources are discovered using the tag pattern `kubernetes.io/cluster/{cluster-uid}:owned`
4. **Orchestration**: `AWSResourceDiscoverer` iterates through registered services
5. **Result Aggregation**: Results are collected and formatted for display

#### Current Challenges
- **Code Duplication**: Similar tag filtering logic across all services
- **Maintenance Overhead**: Adding new AWS services requires implementing new service classes
- **API Call Volume**: Multiple API calls across different services
- **Service Coverage**: Manual effort required to support new AWS services

## Proposed Architecture: AWS Resource Groups Tagging API

### AWS Resource Groups Tagging API Overview

The AWS Resource Groups Tagging API (`resourcegroupstaggingapi`) provides a unified interface for resource discovery across all AWS services:

- **Single API Call**: `get_resources()` discovers resources across ALL AWS services
- **Native Tag Filtering**: Built-in support for tag key/value filtering
- **Cross-service Discovery**: No need to know which services to query
- **Pagination Support**: Built-in pagination with `GetResources` paginator
- **ARN-based Results**: Returns resource ARNs that contain service and resource type information

### Proposed Architecture

```
aws/
├── services/
│   ├── base.py                    # AWSService abstract base class (maintained)
│   ├── resource_groups_service.py # NEW: Unified resource discovery
│   ├── utils/
│   │   └── arn_parser.py         # NEW: ARN parsing utilities
│   └── registry.py               # Updated service registration
├── utils/
│   └── discoverer.py             # Updated orchestration logic
└── main.py                       # CLI interface (minimal changes)
```

#### Proposed Workflow
1. **Unified Discovery**: Single `ResourceGroupsService` class uses `resourcegroupstaggingapi`
2. **Single API Call**: `get_resources()` with tag filter discovers all tagged resources
3. **ARN Processing**: Parse returned ARNs to extract service, resource type, and region information
4. **Resource Categorization**: Map ARN patterns to current service categories (EC2, ELB, etc.)
5. **Selective Enrichment**: Make targeted API calls only for resources requiring additional details
6. **Result Compatibility**: Maintain existing `ResourceInfo` structure for backward compatibility

## Implementation Plan

### Phase 1: Core Implementation

#### Task 1.1: Create ResourceGroupsService Class
```python
class ResourceGroupsService(AWSService):
    def __init__(self):
        super().__init__("ResourceGroups", ["all_resources"])
    
    def get_client(self, session):
        return session.client('resourcegroupstaggingapi')
    
    def search_resources(self, client, tag_key, tag_value):
        # Implementation using get_resources() API
        pass
```

#### Task 1.2: Create ARN Parser Utility
```python
class ARNParser:
    @staticmethod
    def parse_arn(arn: str) -> ARNInfo:
        # Extract service, resource type, region, account, resource ID
        pass
    
    @staticmethod
    def categorize_resource(arn_info: ARNInfo) -> ResourceCategory:
        # Map to current service categories (EC2, ELB, etc.)
        pass
```

#### Task 1.3: Resource Type Mapping
Create mapping from ARN patterns to current resource types:
- `arn:aws:ec2:*:*:instance/*` → EC2 instances
- `arn:aws:ec2:*:*:volume/*` → EBS volumes
- `arn:aws:elasticloadbalancing:*:*:loadbalancer/*` → Load balancers
- And so on...

### Phase 2: Integration and Compatibility

#### Task 2.1: Registry Integration
```python
# Updated SERVICE_REGISTRY
SERVICE_REGISTRY = {
    'ResourceGroups': ResourceGroupsService(),  # NEW unified service
    'EC2': EC2Service(),                        # Legacy service (optional)
    'ELB': ELBService(),                        # Legacy service (optional)
}

# Configuration flags
SERVICE_CONFIG = {
    'ResourceGroups': {
        'enabled': False,  # Start disabled for testing
        'unified_discovery': True,
        'fallback_to_individual': True
    }
}
```

#### Task 2.2: Discoverer Updates
Update `AWSResourceDiscoverer` to support both approaches:
```python
def discover_all_resources(self, use_unified: bool = False):
    if use_unified and is_service_enabled('ResourceGroups'):
        return self._unified_discovery()
    else:
        return self._modular_discovery()  # Current approach
```

#### Task 2.3: Resource Detail Enrichment
For resources requiring additional details beyond ARN information:
```python
def enrich_resource_details(self, resource_info: ResourceInfo) -> ResourceInfo:
    # Make targeted API calls based on resource type
    # Only for resources that need additional information
    pass
```

### Phase 3: Testing and Validation

#### Task 3.1: Feature Parity Testing
- Compare resource discovery results between modular and unified approaches
- Validate all resource types are discovered correctly
- Ensure resource metadata completeness
- Test error handling and edge cases

#### Task 3.2: Performance Comparison
- Measure API call count reduction
- Compare response times
- Test with large resource sets
- Validate pagination behavior

#### Task 3.3: Integration Testing
- Test with cost estimation pipeline
- Validate export functionality (JSON, CSV, HTML)
- Ensure optimization suggestions still work
- Test CLI argument compatibility

### Phase 4: Migration and Cleanup

#### Task 4.1: Gradual Migration
1. Enable unified discovery as opt-in feature
2. Run both approaches in parallel for validation
3. Gradually migrate users to unified approach
4. Deprecate individual service modules

#### Task 4.2: Documentation Updates
- Update README with new architecture
- Create migration guide for users
- Update IAM policy requirements
- Document new configuration options

#### Task 4.3: Legacy Cleanup
- Remove individual service modules
- Clean up unused imports and dependencies
- Update tests to use unified approach
- Archive legacy documentation

## Benefits Analysis

### Immediate Benefits
- **Reduced Complexity**: Single API call instead of multiple service-specific calls
- **Better Coverage**: Automatic discovery of resources from any AWS service
- **Improved Performance**: Fewer API calls and better pagination handling
- **Simplified Error Handling**: Centralized error handling instead of per-service

### Long-term Benefits
- **Reduced Maintenance**: No need to implement new service modules for new AWS services
- **Automatic Support**: New AWS services automatically supported when they support tagging
- **Cleaner Architecture**: Unified resource discovery with consistent interfaces
- **Better Testing**: Single code path to test instead of multiple service implementations

### Cost Benefits
- **Reduced API Calls**: Fewer billable API requests to AWS
- **Faster Discovery**: Reduced latency from parallel to sequential API calls
- **Lower Development Cost**: Less code to maintain and update

## Considerations and Limitations

### Technical Considerations
- **Regional Scope**: Resource Groups API works within single region (same as current approach)
- **Resource Details**: Some resources may need follow-up API calls for complete information
- **ARN Parsing**: Need robust ARN parsing to handle all AWS service patterns
- **Error Handling**: Need to handle cases where Resource Groups API is unavailable

### Migration Considerations
- **Backward Compatibility**: Ensure existing functionality continues to work
- **Configuration Migration**: Provide smooth transition for existing users
- **Fallback Strategy**: Keep individual services as backup during transition
- **Testing Period**: Allow sufficient time for validation before full migration

### IAM Permissions
New required permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "resourcegroupstaggingapi:GetResources",
                "resourcegroupstaggingapi:GetTagKeys",
                "resourcegroupstaggingapi:GetTagValues"
            ],
            "Resource": "*"
        }
    ]
}
```

## Implementation Timeline

### Week 1-2: Core Implementation
- Create `ResourceGroupsService` class
- Implement ARN parser utility
- Create resource type mapping

### Week 3-4: Integration
- Update service registry
- Modify discoverer for dual-mode operation
- Implement resource enrichment logic

### Week 5-6: Testing
- Feature parity validation
- Performance testing
- Integration testing with cost pipeline

### Week 7-8: Migration
- Documentation updates
- Gradual user migration
- Legacy cleanup

## Success Metrics

### Technical Metrics
- **API Call Reduction**: Target 70-80% reduction in AWS API calls
- **Response Time**: Maintain or improve current discovery performance
- **Resource Coverage**: 100% feature parity with current approach
- **Error Rate**: Maintain current error handling quality

### Business Metrics
- **Development Velocity**: Faster addition of new AWS service support
- **Maintenance Cost**: Reduced code maintenance overhead
- **User Experience**: Improved CLI responsiveness
- **Operational Cost**: Reduced AWS API costs

## Risk Mitigation

### Technical Risks
- **API Availability**: Fallback to individual services if Resource Groups API unavailable
- **ARN Parsing Failures**: Robust error handling and logging for unknown ARN patterns
- **Performance Regression**: Thorough performance testing before migration
- **Data Loss**: Comprehensive validation to ensure no resource discovery gaps

### Migration Risks
- **User Impact**: Gradual migration with opt-in testing period
- **Configuration Issues**: Clear migration documentation and support
- **Rollback Plan**: Keep individual services available during transition
- **Training Need**: Update documentation and provide examples

## Conclusion

The migration to AWS Resource Groups Tagging API represents a significant architectural improvement that will:

1. **Simplify the codebase** by eliminating multiple service-specific implementations
2. **Improve performance** through reduced API calls and better pagination
3. **Enhance maintainability** by removing the need to implement new service modules
4. **Provide better coverage** with automatic support for new AWS services

The phased implementation approach ensures minimal risk while providing clear benefits. The backward compatibility strategy allows for safe migration with fallback options.

This migration aligns with the project's goal of providing comprehensive, efficient, and maintainable multi-cloud cost estimation capabilities.