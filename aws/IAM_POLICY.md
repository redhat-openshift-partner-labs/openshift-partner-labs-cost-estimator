## IAM Permissions

The only permissions required are for describe_* and get_* actions, which are read-only.
The Cost Explorer permissions (ce:GetCostAndUsage, etc.) are also read-only.

Here is the **minimal IAM policy** required for your codebase to function. This policy grants only the necessary read-only permissions for the AWS services and Cost Explorer APIs used by your code.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        // EC2 read-only
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeNetworkInterfaces",

        // ELB Classic read-only
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTags",

        // ELBv2 (ALB/NLB) read-only
        "elasticloadbalancing:DescribeLoadBalancers",
        "elasticloadbalancing:DescribeTags",

        // Cost Explorer read-only
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetReservationCoverage",
        "ce:GetReservationUtilization",
        "ce:GetDimensionValues",
        "ce:GetTags"
      ],
      "Resource": "*"
    }
  ]
}
```

### **Notes:**
- This policy is **read-only** and does not allow any destructive or write actions.
- The `"Resource": "*"` is required because these APIs do not support resource-level restrictions.
- If you add more AWS services in the future, you may need to add their corresponding `Describe*` or `List*` actions.

---

**You can safely attach this policy to any IAM user or role that will run your code.**  
If you need a version with comments removed for direct use in AWS, let me know!


## Adding More Services

1. Using AWS CLI with help

```shell
# Get all available commands for a service
aws ec2 help

# Get help for a specific command
aws ec2 describe-instances help

# List all available commands
aws ec2 help | grep "describe\|list"
```

## **1. Using AWS CLI with `help`**

```bash
# Get all available commands for a service
aws ec2 help

# Get help for a specific command
aws ec2 describe-instances help

# List all available commands
aws ec2 help | grep "describe\|list"
```

## **2. Using boto3 to Introspect Available Methods**

```python
import boto3
from botocore.model import ServiceModel

def get_service_actions(service_name):
    """Get all available actions for a service with their details"""
    client = boto3.client(service_name)
    
    # Get the service model
    service_model = client._service_model
    
    # Get all operations
    operations = service_model.operation_names
    
    # Get operation details
    operation_details = {}
    for operation in operations:
        op_model = service_model.operation_model(operation)
        operation_details[operation] = {
            'http_method': op_model.http['method'],
            'input_shape': op_model.input_shape.name if op_model.input_shape else None,
            'output_shape': op_model.output_shape.name if op_model.output_shape else None,
            'documentation': op_model.documentation
        }
    
    return operation_details

# Example usage
ec2_actions = get_service_actions('ec2')
for action, details in ec2_actions.items():
    if 'describe' in action or 'list' in action:
        print(f"{action}: {details['http_method']}")
```

## **3. Using AWS SDK Documentation Programmatically**

```python
import boto3
from botocore.model import ServiceModel

def get_service_actions(service_name):
    """Get all available actions for a service with their details"""
    client = boto3.client(service_name)
    
    # Get the service model
    service_model = client._service_model
    
    # Get all operations
    operations = service_model.operation_names
    
    # Get operation details
    operation_details = {}
    for operation in operations:
        op_model = service_model.operation_model(operation)
        operation_details[operation] = {
            'http_method': op_model.http['method'],
            'input_shape': op_model.input_shape.name if op_model.input_shape else None,
            'output_shape': op_model.output_shape.name if op_model.output_shape else None,
            'documentation': op_model.documentation
        }
    
    return operation_details

# Example usage
ec2_actions = get_service_actions('ec2')
for action, details in ec2_actions.items():
    if 'describe' in action or 'list' in action:
        print(f"{action}: {details['http_method']}")
```

## **4. Using AWS IAM Policy Simulator**

You can use the AWS IAM Policy Simulator to test which actions are allowed:

```python
import boto3

def test_iam_permissions(service_name, actions):
    """Test which IAM permissions are granted for specific actions"""
    iam = boto3.client('iam')
    
    # Create a test policy
    test_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": actions,
                "Resource": "*"
            }
        ]
    }
    
    # Note: This would require IAM permissions to use the policy simulator
    # In practice, you'd use the AWS Console or AWS CLI for this
    return test_policy
```

## **5. Using AWS Documentation API (if available)**

```python
import requests

def get_aws_documentation_actions(service_name):
    """Get actions from AWS documentation (if API is available)"""
    # This is a conceptual example - AWS doesn't provide a public API for this
    # But you could scrape the documentation if needed
    
    url = f"https://docs.aws.amazon.com/service-authorization/latest/reference/list_{service_name}.html"
    # Implementation would depend on the documentation structure
    pass
```

## **6. Complete Example: Generate IAM Policy for a Service**

```python
import boto3
import json

def generate_read_only_policy(service_name):
    """Generate a read-only IAM policy for a specific service"""
    client = boto3.client(service_name)
    
    # Get all methods
    methods = [method for method in dir(client) if not method.startswith('_')]
    
    # Filter for read-only actions
    read_only_actions = []
    for method in methods:
        if any(pattern in method for pattern in ['describe_', 'list_', 'get_']):
            # Convert to AWS action format
            action = f"{service_name}:{method.replace('_', '')}"
            read_only_actions.append(action)
    
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": read_only_actions,
                "Resource": "*"
            }
        ]
    }
    
    return policy

# Example usage
ec2_policy = generate_read_only_policy('ec2')
print(json.dumps(ec2_policy, indent=2))
```

## **7. Practical Script for Your Use Case**

Here's a script that would help you determine the required permissions for adding new services to your framework:

```python
#!/usr/bin/env python3
"""
AWS Service Permission Analyzer
Helps determine the minimal IAM permissions needed for read-only operations
"""

import boto3
import json
from typing import List, Dict

def analyze_service_permissions(service_name: str) -> Dict:
    """Analyze a service to determine read-only permissions needed"""
    
    try:
        client = boto3.client(service_name)
        
        # Get all available methods
        methods = [method for method in dir(client) if not method.startswith('_')]
        
        # Categorize methods
        read_only_methods = []
        write_methods = []
        other_methods = []
        
        for method in methods:
            if any(pattern in method for pattern in ['describe_', 'list_', 'get_', 'show_']):
                read_only_methods.append(method)
            elif any(pattern in method for pattern in ['create_', 'delete_', 'update_', 'modify_', 'put_', 'post_']):
                write_methods.append(method)
            else:
                other_methods.append(method)
        
        return {
            'service': service_name,
            'read_only_methods': sorted(read_only_methods),
            'write_methods': sorted(write_methods),
            'other_methods': sorted(other_methods),
            'total_methods': len(methods)
        }
    
    except Exception as e:
        return {
            'service': service_name,
            'error': str(e)
        }

def generate_minimal_policy(service_analyses: List[Dict]) -> Dict:
    """Generate minimal IAM policy from service analyses"""
    
    actions = []
    
    for analysis in service_analyses:
        if 'error' not in analysis:
            service_name = analysis['service']
            for method in analysis['read_only_methods']:
                # Convert method name to AWS action format
                action = f"{service_name}:{method.replace('_', '')}"
                actions.append(action)
    
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": sorted(actions),
                "Resource": "*"
            }
        ]
    }

# Example usage
if __name__ == "__main__":
    services_to_analyze = ['ec2', 'elasticloadbalancing', 'rds', 's3']
    
    print("Analyzing AWS services for read-only permissions...\n")
    
    analyses = []
    for service in services_to_analyze:
        print(f"Analyzing {service}...")
        analysis = analyze_service_permissions(service)
        analyses.append(analysis)
        
        if 'error' not in analysis:
            print(f"  Found {len(analysis['read_only_methods'])} read-only methods")
            print(f"  Found {len(analysis['write_methods'])} write methods")
        else:
            print(f"  Error: {analysis['error']}")
        print()
    
    # Generate minimal policy
    policy = generate_minimal_policy(analyses)
    
    print("Generated minimal IAM policy:")
    print(json.dumps(policy, indent=2))
```

## **Key Points:**

1. **boto3 introspection** is the most reliable method for discovering available actions
2. **AWS CLI help** is great for quick exploration
3. **Service models** provide detailed information about operations
4. **Always test permissions** in a safe environment before using in production
5. **Consider using AWS Organizations** to test policies in isolated accounts

This approach will help you systematically determine the minimal permissions needed when adding new AWS services to your framework!

import boto3

def get_read_only_actions(service_name):
    """Get all read-only actions for an AWS service"""
    client = boto3.client(service_name)
    
    # Get all available methods
    methods = [method for method in dir(client) if not method.startswith('_')]
    
    # Filter for read-only actions
    read_only_patterns = [
        'describe_', 'list_', 'get_', 'show_', 'view_',
        'search_', 'query_', 'find_', 'check_', 'verify_'
    ]
    
    read_only_actions = []
    for method in methods:
        if any(pattern in method for pattern in read_only_patterns):
            read_only_actions.append(method)
    
    return sorted(read_only_actions)

# Example usage
print("EC2 read-only actions:")
print(get_read_only_actions('ec2'))

print("\nRDS read-only actions:")
print(get_read_only_actions('rds'))

