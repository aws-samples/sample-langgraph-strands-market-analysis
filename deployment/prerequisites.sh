#!/bin/bash

# Prerequisites: Set up IAM role and ECR repository
echo "🔐 Setting up prerequisites for AgentCore deployment..."

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="${PROJECT_DIR}/config"
BASE_SETTINGS="${CONFIG_DIR}/static-config.yaml"

# Load configuration
if command -v yq >/dev/null 2>&1; then
    REGION=$(yq eval '.aws.region' "${BASE_SETTINGS}")
    ROLE_NAME=$(yq eval '.runtime.role_name' "${BASE_SETTINGS}")
    ECR_REPO=$(yq eval '.runtime.ecr_repo' "${BASE_SETTINGS}")
else
    echo "⚠️  yq not found, using grep/sed fallback"
    REGION=$(grep "region:" "${BASE_SETTINGS}" | head -1 | sed 's/.*region: *\([^ #]*\).*/\1/')
    ROLE_NAME=$(grep "role_name:" "${BASE_SETTINGS}" | head -1 | sed 's/.*role_name: *\([^ #]*\).*/\1/')
    ECR_REPO=$(grep "ecr_repo:" "${BASE_SETTINGS}" | head -1 | sed 's/.*ecr_repo: *\([^ #]*\).*/\1/')
fi

echo "📝 Configuration:"
echo "   Region: ${REGION}"
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

# Update policy files with account ID
echo ""
echo "📝 Updating policy files with account ID..."
sed "s/<ACCOUNT_ID>/${ACCOUNT_ID}/g" "${SCRIPT_DIR}/trust-policy.json" > "${SCRIPT_DIR}/trust-policy-final.json"
sed "s/<ACCOUNT_ID>/${ACCOUNT_ID}/g" "${SCRIPT_DIR}/permissions-policy.json" > "${SCRIPT_DIR}/permissions-policy-final.json"
echo "   ✅ Policy files updated"

# Check/Create IAM Role
echo ""
echo "🔐 Checking IAM Role..."
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
        
        # Wait for role to be available
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
    echo "   ✅ Role already exists: ${ROLE_ARN}"
fi

# Check/Create ECR Repository
echo ""
echo "📦 Checking ECR repository..."
if ! aws ecr describe-repositories --repository-names "${ECR_REPO}" --region "${REGION}" >/dev/null 2>&1; then
    echo "   Creating ECR repository: ${ECR_REPO}"
    aws ecr create-repository --repository-name "${ECR_REPO}" --region "${REGION}" >/dev/null
    echo "   ✅ ECR repository created"
else
    echo "   ✅ ECR repository exists"
fi

echo ""
echo "🎉 Prerequisites setup complete!"
echo "================================="
echo "✅ IAM Role: ${ROLE_ARN}"
echo "✅ ECR Repository: ${ECR_REPO}"
echo ""
echo "Next step: Run ./deploy.sh to build and deploy"