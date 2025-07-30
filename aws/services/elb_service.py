"""
ELB service implementation for AWS resource discovery.
"""

from .base import AWSService, ResourceInfo
from botocore.exceptions import ClientError
from typing import Dict, List
import boto3


class ELBService(AWSService):
    """Elastic Load Balancer service implementation"""
    
    def __init__(self):
        super().__init__("ELB", ["classic_elbs", "albs_nlbs"])
    
    def get_client(self, session: boto3.Session):
        # ELB service uses multiple clients
        return None
    
    def search_resources(self, session: boto3.Session, tag_key: str, tag_value: str) -> Dict[str, List[ResourceInfo]]:
        resources = {rt: [] for rt in self.resource_types}
        
        # Classic Load Balancers
        try:
            elb_client = session.client('elb')
            paginator = elb_client.get_paginator('describe_load_balancers')
            
            for page in paginator.paginate():
                for lb in page['LoadBalancerDescriptions']:
                    tags = elb_client.describe_tags(
                        LoadBalancerNames=[lb['LoadBalancerName']]
                    )['TagDescriptions']
                    
                    for tag_desc in tags:
                        for tag in tag_desc['Tags']:
                            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                                resources['classic_elbs'].append(ResourceInfo(
                                    id=lb['LoadBalancerName'],
                                    name=lb['LoadBalancerName'],
                                    type='Classic',
                                    state=lb.get('State', {}).get('Code', 'N/A'),
                                    additional_info={
                                        'dns': lb['DNSName'],
                                        'vpc': lb.get('VPCId', 'N/A')
                                    }
                                ))
                                break
        except ClientError as e:
            self.handle_error(e, 'classic_elbs')
        
        # Application and Network Load Balancers
        try:
            elbv2_client = session.client('elbv2')
            paginator = elbv2_client.get_paginator('describe_load_balancers')
            
            for page in paginator.paginate():
                for lb in page['LoadBalancers']:
                    tags = elbv2_client.describe_tags(
                        ResourceArns=[lb['LoadBalancerArn']]
                    )['TagDescriptions']
                    
                    for tag_desc in tags:
                        for tag in tag_desc['Tags']:
                            if tag['Key'] == tag_key and tag['Value'] == tag_value:
                                resources['albs_nlbs'].append(ResourceInfo(
                                    id=lb['LoadBalancerName'],
                                    name=lb['LoadBalancerName'],
                                    type=lb['Type'],
                                    state=lb.get('State', {}).get('Code', 'N/A'),
                                    additional_info={'arn': lb['LoadBalancerArn']}
                                ))
                                break
        except ClientError as e:
            self.handle_error(e, 'albs_nlbs')
        
        return resources 