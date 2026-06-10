#!/bin/bash

# Deploy Market Surveillance Workflow to AWS AgentCore
echo "🚀 Deploying Market Surveillance Workflow to AWS AgentCore..."

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${PROJECT_DIR}/config"
BASE_SETTINGS="${CONFIG_DIR}/static-config.yaml"

# Load configuration
if command -v yq >/dev/null 2>&1; then
    REGION=$(yq eval '.aws.region' "${BASE_SETTINGS}")
    RUNTIME_NAME=$(yq eval '.runtime.name' "${BASE_SETTINGS}")
    ROLE_NAME=$(yq eval '.runtime.role_name' "${BASE_SETTINGS}")
    ECR_REPO=$(yq eval '.runtime.ecr_repo' "${BASE_SETTINGS}")
else
    echo "⚠️  yq not found, using grep/sed fallback"
    REGION=$(grep "region:" "${BASE_SETTINGS}" | head -1 | sed 's/.*region: *\([^ #]*\).*/\1/')
    RUNTIME_NAME=$(grep "name:" "${BASE_SETTINGS}" | head -1 | sed 's/.*name: *\([^ #]*\).*/\1/')
    ROLE_NAME=$(grep "role_name:" "${BASE_SETTINGS}" | head -1 | sed 's/.*role_name: *\([^ #]*\).*/\1/')
    ECR_REPO=$(grep "ecr_repo:" "${BASE_SETTINGS}" | head -1 | sed 's/.*ecr_repo: *\([^ #]*\).*/\1/')
fi

echo "📝 Configuration:"
echo "   Region: ${REGION}"
echo "   Runtime Name: ${RUNTIME_NAME}"
echo "   Role Name: ${ROLE_NAME}"
echo "   ECR Repository: ${ECR_REPO}"

# Get AWS Account ID
echo ""
echo "🔍 Detecting AWS Account ID..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

if [ -z "$ACCOUNT_ID" ]; then
    echo "❌ Failed to get AWS Account ID. Please ensure AWS credentials are configured."
    exit 1
fi

echo "   Account ID: ${ACCOUNT_ID}"
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO}"

# Check if dynamic config exists, create from example if not
DYNAMIC_CONFIG="${CONFIG_DIR}/dynamic-config.yaml"
if [ ! -f "$DYNAMIC_CONFIG" ]; then
    echo ""
    echo "📝 Creating dynamic-config.yaml from example..."
    if [ -f "${CONFIG_DIR}/dynamic-config.yaml.example" ]; then
        cp "${CONFIG_DIR}/dynamic-config.yaml.example" "$DYNAMIC_CONFIG"
        echo "   ✅ dynamic-config.yaml created"
    else
        echo "   ❌ dynamic-config.yaml.example not found"
        exit 1
    fi
fi

# === PREREQUISITES ===
echo ""
echo "🔐 Checking Prerequisites..."

# Update policy files with account ID
sed "s/<ACCOUNT_ID>/${ACCOUNT_ID}/g" "${SCRIPT_DIR}/trust-policy.json" > "${SCRIPT_DIR}/trust-policy-final.json"
sed "s/<ACCOUNT_ID>/${ACCOUNT_ID}/g" "${SCRIPT_DIR}/permissions-policy.json" > "${SCRIPT_DIR}/permissions-policy-final.json"

# Check/Create IAM Role
ROLE_EXISTS=$(aws iam get-role --role-name "${ROLE_NAME}" --region "${REGION}" 2>&1)

if echo "$ROLE_EXISTS" | grep -q "NoSuchEntity"; then
    echo "   Creating IAM role: ${ROLE_NAME}"
    
    ROLE_ARN=$(aws iam create-role \
        --role-name "${ROLE_NAME}" \
        --assume-role-policy-document "file://${SCRIPT_DIR}/trust-policy-final.json" \
        --description "Execution role for Market Surveillance AgentCore Runtime" \
        --region "${REGION}" \
        --query 'Role.Arn' \
        --output text)
    
    if [ $? -eq 0 ]; then
        echo "   ✅ Role created: ${ROLE_ARN}"
        
        # Attach permissions policy
        echo "   Attaching permissions policy..."
        aws iam put-role-policy \
            --role-name "${ROLE_NAME}" \
            --policy-name "${ROLE_NAME}-permissions" \
            --policy-document "file://${SCRIPT_DIR}/permissions-policy-final.json" \
            --region "${REGION}"
        
        if [ $? -eq 0 ]; then
            echo "   ✅ Permissions policy attached"
        else
            echo "   ❌ Failed to attach permissions policy"
            exit 1
        fi
        
        # Wait for role to propagate
        echo "   ⏳ Waiting for role to propagate (10 seconds)..."
        sleep 10
    else
        echo "   ❌ Failed to create role"
        exit 1
    fi
else
    ROLE_ARN=$(echo "$ROLE_EXISTS" | grep -o 'arn:aws:iam::[0-9]*:role/[^"]*' | head -1)
    if [ -z "$ROLE_ARN" ]; then
        ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
    fi
    echo "   ✅ Role exists: ${ROLE_ARN}"
fi

# Check/Create ECR Repository
if ! aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${REGION}" >/dev/null 2>&1; then
    echo "   Creating ECR repository: ${ECR_REPO}"
    aws ecr create-repository --repository-name "${ECR_REPO}" --region "${REGION}" >/dev/null
    echo "   ✅ ECR repository created"
else
    echo "   ✅ ECR repository exists"
fi

# === BUILD AND DEPLOY ===

# Login to ECR
echo ""
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ECR_URI}" >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✅ ECR login successful"
else
    echo "   ❌ ECR login failed"
    exit 1
fi

# Build Docker image
echo ""
echo "🔨 Building Docker image (ARM64)..."
cd "${PROJECT_DIR}"
docker build --no-cache --platform linux/arm64 -t "${ECR_REPO}:latest" .

if [ $? -eq 0 ]; then
    echo "   ✅ Docker image built successfully"
else
    echo "   ❌ Docker build failed"
    exit 1
fi

# Tag for ECR
echo ""
echo "🏷️  Tagging image..."
docker tag "${ECR_REPO}:latest" "${ECR_URI}:latest"
echo "   ✅ Image tagged"

# Push to ECR
echo ""
echo "📤 Pushing to ECR..."
docker push "${ECR_URI}:latest"

if [ $? -eq 0 ]; then
    echo "   ✅ Image pushed to ECR"
else
    echo "   ❌ Failed to push image"
    exit 1
fi

# Update dynamic config with ECR URI
echo ""
echo "📝 Updating dynamic config with ECR URI..."
if command -v yq >/dev/null 2>&1; then
    yq eval ".runtime.ecr_uri = \"${ECR_URI}:latest\"" -i "${CONFIG_DIR}/dynamic-config.yaml"
    echo "   ✅ Dynamic config updated"
else
    echo "   ℹ️  yq not found. ECR URI will be updated by Python deployment script"
fi

# Run Python deployment script
echo ""
echo "🚀 Deploying to AgentCore runtime..."
cd "${SCRIPT_DIR}"

python3 deploy-runtime.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment Complete!"
    echo "================================="
    echo "✅ Docker image: ${ECR_URI}:latest"
    echo "✅ AgentCore runtime deployed"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Check config/dynamic-config.yaml for runtime ARN"
    echo "   2. Run: streamlit run app.py"
    echo "   3. Test your workflow!"
    echo ""
    echo "📊 View logs:"
    echo "   aws logs tail /aws/bedrock-agentcore/runtimes/market_surveillance_workflow --follow"
    
    # Cleanup temporary files
    rm -f "${SCRIPT_DIR}/trust-policy-final.json"
    rm -f "${SCRIPT_DIR}/permissions-policy-final.json"
else
    echo ""
    echo "❌ Runtime deployment failed"
    echo "Please check the error messages above"
    
    # Cleanup temporary files even on failure
    rm -f "${SCRIPT_DIR}/trust-policy-final.json"
    rm -f "${SCRIPT_DIR}/permissions-policy-final.json"
    exit 1
fi
