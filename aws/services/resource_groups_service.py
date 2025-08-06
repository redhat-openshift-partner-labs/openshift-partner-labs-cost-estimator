"""
AWS Resource Groups Tagging API Service

This module provides unified resource discovery across all AWS services using the
Resource Groups Tagging API. This replaces the need for individual service modules
by discovering all tagged resources in a single API call.

Key features:
- Single API call to discover resources across all AWS services
- ARN-based resource identification and categorization
- Maintains compatibility with existing ResourceInfo structure
- Automatic support for new AWS services that support tagging

Usage:
    service = ResourceGroupsService()
    client = service.get_client(session)
    resources = service.search_resources(client, tag_key, tag_value)
"""

from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError
from .base import AWSService, ResourceInfo


class ARNInfo:
    """Data class for parsed ARN information"""
    def __init__(self, arn: str):
        self.arn = arn
        self.partition = None
        self.service = None
        self.region = None
        self.account_id = None
        self.resource_type = None
        self.resource_id = None
        self._parse_arn()
    
    def _parse_arn(self):
        """Parse ARN into components
        
        ARN format: arn:partition:service:region:account-id:resource-type/resource-id
        or: arn:partition:service:region:account-id:resource-type:resource-id
        """
        try:
            parts = self.arn.split(':')
            if len(parts) >= 6:
                self.partition = parts[1]
                self.service = parts[2]
                self.region = parts[3]
                self.account_id = parts[4]
                
                # Handle resource part (can be resource-type/resource-id or resource-type:resource-id)
                resource_part = ':'.join(parts[5:])
                if '/' in resource_part:
                    self.resource_type, self.resource_id = resource_part.split('/', 1)
                elif ':' in resource_part:
                    self.resource_type, self.resource_id = resource_part.split(':', 1)
                else:
                    self.resource_type = resource_part
                    self.resource_id = resource_part
        except (IndexError, ValueError):
            # Handle malformed ARNs gracefully
            pass


class ResourceGroupsService(AWSService):
    """Unified AWS resource discovery service using Resource Groups Tagging API"""
    
    def __init__(self):
        # Support all resource types that can be discovered via ARNs
        # Organized by cost impact: billable resources first, then free resources
        resource_types = [
            # EC2 Compute & Storage (billable)
            'instances', 'volumes', 'nat_gateways', 'elastic_ips', 'vpc_endpoints',
            # EC2 Networking (free)
            'security_groups', 'network_interfaces', 'vpcs', 'subnets', 'route_tables', 'internet_gateways',
            # Load Balancing (billable)
            'classic_elbs', 'albs_nlbs', 'target_groups',
            # Database Services (billable)
            'rds_instances', 'rds_clusters',
            # Storage Services (billable)
            's3_buckets',
            # Compute Services (billable)
            'lambda_functions',
            # DNS Services (billable)
            'route53_zones', 'route53_records',
            # IAM (free)
            'iam_roles', 'iam_policies',
            # Infrastructure as Code (free)
            'cloudformation_stacks',
            # Catch-all
            'other_resources'
        ]
        super().__init__("ResourceGroups", resource_types)
        
        # Service mapping for categorizing resources with cost awareness
        # Organized by service and resource type for efficient categorization
        self.service_mapping = {
            'ec2': {
                # Billable EC2 resources
                'instance': 'instances',
                'volume': 'volumes',
                'natgateway': 'nat_gateways',
                'elastic-ip': 'elastic_ips',
                'vpc-endpoint': 'vpc_endpoints',
                # Free EC2 resources
                'security-group': 'security_groups',
                'network-interface': 'network_interfaces',
                'vpc': 'vpcs',
                'subnet': 'subnets',
                'route-table': 'route_tables',
                'internet-gateway': 'internet_gateways'
            },
            'elasticloadbalancing': {
                # All load balancing resources are billable
                'loadbalancer': 'albs_nlbs',  # Catches all loadbalancer types
                'targetgroup': 'target_groups'
            },
            'rds': {
                # All RDS resources are billable
                'db': 'rds_instances',
                'cluster': 'rds_clusters'
            },
            's3': {
                # S3 buckets are billable (storage + requests)
                '': 's3_buckets'  # Empty string will match any S3 resource
            },
            'lambda': {
                # Lambda functions are billable (invocations + duration)
                'function': 'lambda_functions'
            },
            'route53': {
                # Route53 resources are billable
                'hostedzone': 'route53_zones',
                'rrset': 'route53_records'
            },
            'iam': {
                # IAM resources are free
                'role': 'iam_roles',
                'policy': 'iam_policies'
            },
            'cloudformation': {
                # CloudFormation stacks are free (underlying resources may be billable)
                'stack': 'cloudformation_stacks'
            }
        }
    
    def get_client(self, session: boto3.Session):
        """Return the Resource Groups Tagging API client"""
        return session.client('resourcegroupstaggingapi')
    
    def search_resources(self, client, tag_key: str, tag_value: str, 
                        enrich_resources: bool = True, session: Optional['boto3.Session'] = None) -> Dict[str, List[ResourceInfo]]:
        """Search for resources with the specified tag across all AWS services
        
        Args:
            client: Resource Groups Tagging API client
            tag_key: Tag key to search for
            tag_value: Tag value to search for
            enrich_resources: Whether to enrich resources with service-specific details (default: True)
            session: boto3.Session for making enrichment API calls (required if enrich_resources=True)
            
        Returns:
            Dictionary of resource type to list of ResourceInfo objects
        """
        resources = {rt: [] for rt in self.resource_types}
        
        try:
            # Create tag filter for the Resource Groups API
            tag_filters = [
                {
                    'Key': tag_key,
                    'Values': [tag_value]
                }
            ]
            
            # Use paginator to handle large result sets
            paginator = client.get_paginator('get_resources')
            
            for page in paginator.paginate(TagFilters=tag_filters):
                for resource in page.get('ResourceTagMappingList', []):
                    resource_arn = resource['ResourceARN']
                    resource_tags = {tag['Key']: tag['Value'] for tag in resource.get('Tags', [])}
                    
                    # Parse ARN to get resource information
                    arn_info = ARNInfo(resource_arn)
                    
                    # Categorize the resource
                    resource_category = self._categorize_resource(arn_info)
                    
                    # Create ResourceInfo object
                    resource_info = self._create_resource_info(arn_info, resource_tags)
                    
                    # Add to appropriate category
                    if resource_category in resources:
                        resources[resource_category].append(resource_info)
                    else:
                        # Add to 'other_resources' if we don't have a specific category
                        resources['other_resources'].append(resource_info)
                        
        except ClientError as e:
            self.handle_error(e, 'unified_discovery')
            # Return empty results on error
        
        # ✅ CRITICAL ENHANCEMENT: Enrich resources with service-specific details
        if enrich_resources and session:
            print(f"🔍 Enriching {sum(len(r) for r in resources.values())} discovered resources...")
            resources = self._enrich_all_resources(resources, session)
            
        return resources
    
    def _categorize_resource(self, arn_info: ARNInfo) -> str:
        """Categorize a resource based on its ARN information
        
        Args:
            arn_info: Parsed ARN information
            
        Returns:
            Resource category string
        """
        service = arn_info.service
        resource_type = arn_info.resource_type
        
        if service in self.service_mapping:
            service_map = self.service_mapping[service]
            
            # Special handling for S3 (ARNs are just bucket names)
            if service == 's3':
                return 's3_buckets'
            
            # Special handling for Route53 resources
            if service == 'route53':
                if resource_type and 'hostedzone' in resource_type:
                    return 'route53_zones'
                elif resource_type and 'rrset' in resource_type:
                    return 'route53_records'
                # Fall through to general mapping
            
            # Special handling for EC2 VPC endpoints (can have different formats)
            if service == 'ec2' and resource_type:
                if 'vpc-endpoint' in resource_type or 'vpce-' in resource_type:
                    return 'vpc_endpoints'
                # Handle elastic IP variations
                if 'eip-' in resource_type or resource_type == 'elastic-ip':
                    return 'elastic_ips'
                # Handle NAT gateway variations  
                if 'nat-' in resource_type or 'natgateway' in resource_type:
                    return 'nat_gateways'
            
            # Try exact match first
            if resource_type in service_map:
                return service_map[resource_type]
            
            # Try partial matches for complex resource types
            for key, category in service_map.items():
                if key and resource_type and resource_type.startswith(key):
                    return category
            
            # Handle empty key (fallback for service)
            if '' in service_map:
                return service_map['']
        
        # Default to 'other_resources' if no mapping found
        return 'other_resources'
    
    def _create_resource_info(self, arn_info: ARNInfo, tags: Dict[str, str]) -> ResourceInfo:
        """Create a ResourceInfo object from ARN information and tags
        
        Args:
            arn_info: Parsed ARN information
            tags: Resource tags dictionary
            
        Returns:
            ResourceInfo object
        """
        # Extract name from tags if available
        resource_name = tags.get('Name', arn_info.resource_id)
        
        # Create additional info with ARN details
        additional_info = {
            'arn': arn_info.arn,
            'service': arn_info.service,
            'resource_type': arn_info.resource_type,
            'account_id': arn_info.account_id,
            'tags': tags,
            'discovery_method': 'resource_groups_api'
        }
        
        return ResourceInfo(
            id=arn_info.resource_id or arn_info.arn,
            name=resource_name,
            type=arn_info.resource_type,
            region=arn_info.region,
            additional_info=additional_info
        )
    
    def get_resource_details(self, resource_info: ResourceInfo, session: boto3.Session) -> ResourceInfo:
        """Enrich resource with additional details from service-specific APIs
        
        This method can be used to fetch additional resource details that are not
        available through the Resource Groups API alone.
        
        Args:
            resource_info: Basic resource info from Resource Groups API
            session: AWS session for making additional API calls
            
        Returns:
            Enhanced ResourceInfo object
        """
        if not resource_info.additional_info:
            return resource_info
        
        service = resource_info.additional_info.get('service')
        arn = resource_info.additional_info.get('arn')
        
        try:
            if service == 'ec2':
                return self._enrich_ec2_resource(resource_info, session)
            elif service == 'elasticloadbalancing':
                return self._enrich_elb_resource(resource_info, session)
            # Add more service-specific enrichment as needed
            
        except Exception as e:
            print(f"Warning: Could not enrich resource {resource_info.id}: {e}")
        
        return resource_info
    
    def _enrich_all_resources(self, resources: Dict[str, List[ResourceInfo]], session: boto3.Session) -> Dict[str, List[ResourceInfo]]:
        """Enrich all discovered resources with service-specific details"""
        enriched_resources = {rt: [] for rt in self.resource_types}
        
        # Track enrichment statistics
        total_resources = sum(len(r) for r in resources.values())
        enriched_count = 0
        ec2_enriched = 0
        enrichment_warnings = []
        
        for resource_type, resource_list in resources.items():
            for resource in resource_list:
                try:
                    # Enrich based on service type
                    enriched_resource = self.get_resource_details(resource, session)
                    enriched_resources[resource_type].append(enriched_resource)
                    enriched_count += 1
                    
                    # Track EC2 enrichment specifically
                    if (resource.additional_info and 
                        resource.additional_info.get('service') == 'ec2' and
                        resource.additional_info.get('resource_type') == 'instance'):
                        
                        instance_type = enriched_resource.additional_info.get('instance_type')
                        if instance_type:
                            ec2_enriched += 1
                            print(f"  ✓ EC2 instance {resource.id}: {instance_type}")
                        else:
                            warning = f"  ⚠️  EC2 instance {resource.id}: instance type not available"
                            print(warning)
                            enrichment_warnings.append(warning)
                            
                except Exception as e:
                    # If enrichment fails, use the original resource
                    enriched_resources[resource_type].append(resource)
                    warning = f"  ⚠️  Failed to enrich {resource.id}: {str(e)[:50]}"
                    print(warning)
                    enrichment_warnings.append(warning)
        
        # Print enrichment summary
        print(f"✓ Enrichment complete: {enriched_count}/{total_resources} resources")
        if ec2_enriched > 0:
            print(f"  ✓ EC2 instances with type data: {ec2_enriched}")
        if enrichment_warnings:
            print(f"  ⚠️  {len(enrichment_warnings)} warnings (see above)")
            
        return enriched_resources
    
    def _enrich_ec2_resource(self, resource_info: ResourceInfo, session: boto3.Session) -> ResourceInfo:
        """Enrich EC2 resource with additional details"""
        ec2_client = session.client('ec2')
        resource_type = resource_info.additional_info.get('resource_type')
        
        try:
            if resource_type == 'instance':
                response = ec2_client.describe_instances(InstanceIds=[resource_info.id])
                if response['Reservations']:
                    instance = response['Reservations'][0]['Instances'][0]
                    resource_info.state = instance['State']['Name']
                    resource_info.type = instance.get('InstanceType', resource_info.type)
                    resource_info.additional_info.update({
                        'launch_time': instance.get('LaunchTime'),
                        'instance_type': instance.get('InstanceType'),
                        'vpc_id': instance.get('VpcId'),
                        'subnet_id': instance.get('SubnetId')
                    })
            elif resource_type == 'volume':
                response = ec2_client.describe_volumes(VolumeIds=[resource_info.id])
                if response['Volumes']:
                    volume = response['Volumes'][0]
                    resource_info.state = volume['State']
                    resource_info.type = f"{volume['Size']} GB {volume.get('VolumeType', 'gp2')}"
                    resource_info.additional_info.update({
                        'volume_type': volume.get('VolumeType'),
                        'size_gb': volume['Size'],
                        'encrypted': volume.get('Encrypted', False)
                    })
        except ClientError as e:
            print(f"Could not enrich EC2 resource {resource_info.id}: {e}")
        
        return resource_info
    
    def _enrich_elb_resource(self, resource_info: ResourceInfo, session: boto3.Session) -> ResourceInfo:
        """Enrich ELB resource with additional details"""
        # Implementation for ELB enrichment would go here
        # This is a placeholder for future enhancement
        return resource_info