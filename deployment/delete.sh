#!/bin/bash

# Delete Market Surveillance AgentCore deployment
echo "🗑️  Deleting Market Surveillance AgentCore deployment..."

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${PROJECT_DIR}/config"
BASE_SETTINGS="${CONFIG_DIR}/static-config.yaml"
DYNAMIC_SETTINGS="${CONFIG_DIR}/dynamic-config.yaml"

# Load configuration
if command -v yq >/dev/null 2>&1; then
    REGION=$(yq eval '.aws.region' "${BASE_SETTINGS}")
    RUNTIME_NAME=$(yq eval '.runtime.name' "${BASE_SETTINGS}")
    ROLE_NAME=$(yq eval '.runtime.role_name' "${BASE_SETTINGS}")
    ECR_REPO=$(yq eval '.runtime.ecr_repo' "${BASE_SETTINGS}")
    RUNTIME_ARN=$(yq eval '.runtime.arn' "${DYNAMIC_SETTINGS}")
else
    echo "⚠️  yq not found, using grep/sed fallback"
    REGION=$(grep "region:" "${BASE_SETTINGS}" | head -1 | sed 's/.*region: *\([^ #]*\).*/\1/')
    RUNTIME_NAME=$(grep "name:" "${BASE_SETTINGS}" | head -1 | sed 's/.*name: *\([^ #]*\).*/\1/')
    ROLE_NAME=$(grep "role_name:" "${BASE_SETTINGS}" | head -1 | sed 's/.*role_name: *\([^ #]*\).*/\1/')
    ECR_REPO=$(grep "ecr_repo:" "${BASE_SETTINGS}" | head -1 | sed 's/.*ecr_repo: *\([^ #]*\).*/\1/')
    RUNTIME_ARN=$(grep -E "^[[:space:]]*arn:" "${DYNAMIC_SETTINGS}" | head -1 | sed -E 's/^[[:space:]]*arn:[[:space:]]*"?([^"[:space:]]+)"?.*/\1/')
fi

echo "📝 Configuration:"
echo "   Region: ${REGION}"
echo "   Runtime Name: ${RUNTIME_NAME}"
echo "   Role Name: ${ROLE_NAME}"
echo "   ECR Repository: ${ECR_REPO}"

# Delete AgentCore Runtime
if [ -n "$RUNTIME_ARN" ]; then
    RUNTIME_ID=$(echo "$RUNTIME_ARN" | awk -F'/' '{print $NF}')
    echo ""
    echo "🗑️  Deleting AgentCore runtime..."
    echo "   Runtime ID: ${RUNTIME_ID}"
    
    # The AgentCore control plane is not available in the AWS CLI on all
    # versions, so delete via boto3 (same SDK path used by deploy-runtime.py).
    python3 - "${RUNTIME_ID}" "${REGION}" <<'PYEOF'
import sys
import boto3

runtime_id, region = sys.argv[1], sys.argv[2]
client = boto3.client("bedrock-agentcore-control", region_name=region)
try:
    client.delete_agent_runtime(agentRuntimeId=runtime_id)
    print("   ✅ Runtime deletion initiated")
except client.exceptions.ResourceNotFoundException:
    print("   ⚠️  Runtime may not exist or already deleted")
except Exception as e:  # noqa: BLE001 - surface any other error to the user
    print(f"   ❌ Runtime deletion failed: {type(e).__name__}: {e}")
    sys.exit(1)
PYEOF

    if [ $? -eq 0 ]; then
        echo "   ⏳ Waiting for runtime to be deleted..."
        sleep 5
    fi
    
    # Clear runtime ARN from config
    if command -v yq >/dev/null 2>&1; then
        yq eval ".runtime.arn = \"\"" -i "${DYNAMIC_SETTINGS}"
        yq eval ".runtime.endpoint_arn = \"\"" -i "${DYNAMIC_SETTINGS}"
        echo "   ✅ Runtime ARN cleared from config"
    fi
else
    echo ""
    echo "ℹ️  No runtime ARN found in config - skipping runtime deletion"
fi

# Delete ECR Repository
echo ""
read -p "Delete ECR repository '${ECR_REPO}'? (y/N): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "🗑️  Deleting ECR repository..."
    aws ecr delete-repository \
        --repository-name "${ECR_REPO}" \
        --force \
        --region "${REGION}" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "   ✅ ECR repository deleted"
    else
        echo "   ⚠️  ECR repository may not exist or already deleted"
    fi
else
    echo "   ⏭️  Skipping ECR repository deletion"
fi

# Delete IAM Role
echo ""
read -p "Delete IAM role '${ROLE_NAME}'? (y/N): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    echo "🗑️  Deleting IAM role..."
    
    # Remove inline policy first
    echo "   Removing inline policy..."
    aws iam delete-role-policy \
        --role-name "${ROLE_NAME}" \
        --policy-name "${ROLE_NAME}-permissions" \
        --region "${REGION}" 2>/dev/null
    
    # Delete role
    aws iam delete-role \
        --role-name "${ROLE_NAME}" \
        --region "${REGION}" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "   ✅ IAM role deleted"
    else
        echo "   ⚠️  IAM role may not exist or already deleted"
    fi
else
    echo "   ⏭️  Skipping IAM role deletion"
fi

# Cleanup temporary files
rm -f "${SCRIPT_DIR}/trust-policy-final.json"
rm -f "${SCRIPT_DIR}/permissions-policy-final.json"

echo ""
echo "🎉 Cleanup complete!"