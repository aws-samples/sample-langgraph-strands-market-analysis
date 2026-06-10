#!/usr/bin/env python3
"""
Deploy Market Surveillance Workflow to AWS AgentCore Runtime

This script creates or updates the AgentCore runtime for the workflow.
No OAuth/JWT authentication is configured (simplified deployment).
"""

import boto3
import time
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.config_manager import ConfigManager


def main():
    """Main deployment function"""
    
    # Initialize configuration manager
    config_manager = ConfigManager()
    static_config = config_manager.get_static_config()
    merged_config = config_manager.get_merged_config()
    
    # Extract configuration values
    REGION = static_config['aws']['region']
    RUNTIME_NAME = static_config['runtime']['name']
    ECR_REPO = static_config['runtime']['ecr_repo']
    
    # Get role ARN
    ROLE_NAME = static_config['runtime']['role_name']
    
    # Get AWS account ID
    sts_client = boto3.client('sts', region_name=REGION)
    account_id = sts_client.get_caller_identity()['Account']
    ROLE_ARN = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
    
    # Construct ECR URI
    ECR_URI = f"{account_id}.dkr.ecr.{REGION}.amazonaws.com/{ECR_REPO}:latest"
    
    print(f"🚀 Creating AgentCore Runtime...")
    print(f"   📝 Name: {RUNTIME_NAME}")
    print(f"   📦 Container: {ECR_URI}")
    print(f"   🔐 Role: {ROLE_ARN}")
    print(f"   🌍 Region: {REGION}")
    
    # Create bedrock-agentcore-control client
    control_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    # Check if runtime already exists
    runtime_exists = False
    existing_runtime_arn = None
    existing_runtime_id = None
    
    try:
        runtimes_response = control_client.list_agent_runtimes()
        for runtime in runtimes_response.get('agentRuntimes', []):
            if runtime.get('agentRuntimeName') == RUNTIME_NAME:
                runtime_exists = True
                existing_runtime_arn = runtime.get('agentRuntimeArn')
                existing_runtime_id = existing_runtime_arn.split('/')[-1] if existing_runtime_arn else None
                print(f"\n✅ Found existing runtime: {existing_runtime_arn}")
                break
    except Exception as e:
        print(f"⚠️  Error checking existing runtimes: {e}")
    
    try:
        if runtime_exists and existing_runtime_arn and existing_runtime_id:
            # Runtime exists — push the new container image via update_agent_runtime
            print(f"\n🔄 Updating runtime with new container image...")

            control_client.update_agent_runtime(
                agentRuntimeId=existing_runtime_id,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': ECR_URI
                    }
                },
                roleArn=ROLE_ARN,
                networkConfiguration={"networkMode": "PUBLIC"},
            )

            # Wait for runtime to return to READY after the update
            print(f"⏳ Waiting for runtime to be READY...")
            max_wait = 600
            wait_time = 0
            while wait_time < max_wait:
                status_response = control_client.get_agent_runtime(agentRuntimeId=existing_runtime_id)
                status = status_response.get('status')
                print(f"   📊 Status: {status} ({wait_time}s)")
                if status == 'READY':
                    print(f"✅ Runtime is READY!")
                    break
                if status in ['FAILED', 'DELETING']:
                    print(f"❌ Runtime update failed with status: {status}")
                    sys.exit(1)
                time.sleep(15)
                wait_time += 15

            # Get existing endpoint ARN
            existing_endpoint_arn = None
            try:
                endpoints_response = control_client.list_agent_runtime_endpoints(
                    agentRuntimeId=existing_runtime_id
                )
                for endpoint in endpoints_response.get('agentRuntimeEndpoints', []):
                    if endpoint.get('name') == 'DEFAULT':
                        existing_endpoint_arn = endpoint.get('agentRuntimeEndpointArn')
                        print(f"✅ Found existing endpoint: {existing_endpoint_arn}")
                        break
            except Exception as e:
                print(f"⚠️  Error getting endpoint ARN: {e}")

            # Update local config with ARNs
            config_manager.update_dynamic_config({
                "runtime": {
                    "arn": existing_runtime_arn,
                    "ecr_uri": ECR_URI,
                    "endpoint_arn": existing_endpoint_arn or ""
                }
            })

            print(f"\n🎉 Runtime Updated Successfully!")
            print(f"🏷️  Runtime ARN: {existing_runtime_arn}")
            print(f"💾 ECR URI: {ECR_URI}")
            print(f"🔗 Endpoint ARN: {existing_endpoint_arn or 'Not found'}")
            
        else:
            # Create new runtime - NO authorizer configuration
            print(f"\n🆕 Creating new runtime (no authentication)...")
            
            response = control_client.create_agent_runtime(
                agentRuntimeName=RUNTIME_NAME,
                agentRuntimeArtifact={
                    'containerConfiguration': {
                        'containerUri': ECR_URI
                    }
                },
                networkConfiguration={"networkMode": "PUBLIC"},
                roleArn=ROLE_ARN
                # NOTE: No authorizerConfiguration - simplified deployment
            )
            
            runtime_arn = response['agentRuntimeArn']
            runtime_id = runtime_arn.split('/')[-1]
            
            print(f"✅ AgentCore Runtime created!")
            print(f"🏷️  ARN: {runtime_arn}")
            print(f"🆔 Runtime ID: {runtime_id}")
            
            # Wait for runtime to be READY
            print(f"\n⏳ Waiting for runtime to be READY...")
            max_wait = 600  # 10 minutes
            wait_time = 0
            
            while wait_time < max_wait:
                try:
                    status_response = control_client.get_agent_runtime(agentRuntimeId=runtime_id)
                    status = status_response.get('status')
                    print(f"   📊 Status: {status} ({wait_time}s)")
                    
                    if status == 'READY':
                        print(f"✅ Runtime is READY!")
                        
                        # Create DEFAULT endpoint
                        print(f"\n🔗 Creating DEFAULT endpoint...")
                        try:
                            endpoint_response = control_client.create_agent_runtime_endpoint(
                                agentRuntimeId=runtime_id,
                                name="DEFAULT"
                            )
                            endpoint_arn = endpoint_response['agentRuntimeEndpointArn']
                            print(f"✅ DEFAULT endpoint created!")
                            print(f"🏷️  Endpoint ARN: {endpoint_arn}")
                            
                        except Exception as ep_error:
                            if "already exists" in str(ep_error):
                                print(f"ℹ️  DEFAULT endpoint already exists, getting ARN...")
                                try:
                                    endpoints_response = control_client.list_agent_runtime_endpoints(
                                        agentRuntimeId=runtime_id
                                    )
                                    endpoint_arn = None
                                    for endpoint in endpoints_response.get('agentRuntimeEndpoints', []):
                                        if endpoint.get('name') == 'DEFAULT':
                                            endpoint_arn = endpoint.get('agentRuntimeEndpointArn')
                                            print(f"🏷️  Found endpoint ARN: {endpoint_arn}")
                                            break
                                    
                                    if not endpoint_arn:
                                        endpoint_arn = f"{runtime_arn}/runtime-endpoint/DEFAULT"
                                        print(f"🔧 Constructed endpoint ARN: {endpoint_arn}")
                                        
                                except Exception as list_error:
                                    print(f"⚠️  Could not get endpoint ARN: {list_error}")
                                    endpoint_arn = f"{runtime_arn}/runtime-endpoint/DEFAULT"
                                    print(f"🔧 Using constructed endpoint ARN: {endpoint_arn}")
                            else:
                                print(f"❌ Error creating endpoint: {ep_error}")
                                endpoint_arn = ""
                        
                        # Update dynamic config with ARNs
                        config_manager.update_dynamic_config({
                            "runtime": {
                                "arn": runtime_arn,
                                "ecr_uri": ECR_URI,
                                "endpoint_arn": endpoint_arn
                            }
                        })
                        
                        print(f"\n📝 Configuration updated in config/dynamic-config.yaml")
                        break
                        
                    elif status in ['FAILED', 'DELETING']:
                        print(f"❌ Runtime creation failed with status: {status}")
                        sys.exit(1)
                    
                    time.sleep(15)
                    wait_time += 15
                    
                except Exception as e:
                    print(f"❌ Error checking status: {e}")
                    sys.exit(1)
            
            if wait_time >= max_wait:
                print(f"⚠️  Runtime creation taking longer than expected")
                sys.exit(1)
            
            print(f"\n🎉 Deployment Complete!")
            print(f"================================")
            print(f"Runtime ARN: {runtime_arn}")
            print(f"Endpoint ARN: {endpoint_arn}")
    
    except Exception as e:
        print(f"❌ Error creating/updating runtime: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()