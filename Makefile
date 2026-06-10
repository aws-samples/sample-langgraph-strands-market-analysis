.PHONY: help deploy destroy start-client prerequisites clean logs status

# Default target
help:
	@echo "Market Surveillance AgentCore Deployment"
	@echo "========================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make deploy        - Full deployment (handles prerequisites + build + deploy)"
	@echo "  make prerequisites - Set up IAM role and ECR only (for restricted environments)"
	@echo "  make destroy       - Delete all AgentCore resources"
	@echo "  make start-client  - Start Streamlit UI"
	@echo "  make logs          - Tail AgentCore runtime logs"
	@echo "  make status        - Check deployment status"
	@echo "  make clean         - Clean up temporary files"

deploy:
	@echo "🚀 Running full deployment..."
	@cd deployment && ./deploy.sh

prerequisites:
	@echo "🔐 Setting up prerequisites only..."
	@cd deployment && ./prerequisites.sh

destroy:
	@echo "🗑️  Destroying AgentCore deployment..."
	@cd deployment && ./delete.sh

start-client:
	@echo "🎨 Starting Streamlit UI..."
	@streamlit run app.py

logs:
	@echo "📊 Finding and tailing AgentCore runtime logs..."
	@LOG_GROUP=$$(aws logs describe-log-groups \
		--log-group-name-prefix "/aws/bedrock-agentcore/runtimes/market_surveillance_workflow" \
		--region us-east-1 \
		--query 'logGroups[0].logGroupName' \
		--output text 2>/dev/null) && \
	if [ -z "$$LOG_GROUP" ] || [ "$$LOG_GROUP" = "None" ]; then \
		echo "❌ No log group found. Has the runtime been invoked yet?"; \
	else \
		echo "   Log group: $$LOG_GROUP"; \
		aws logs tail "$$LOG_GROUP" --follow --region us-east-1; \
	fi

status:
	@echo "📋 Checking deployment status..."
	@echo ""
	@echo "Configuration:"
	@cat config/dynamic-config.yaml
	@echo ""
	@echo "AgentCore Runtimes:"
	@aws bedrock-agentcore-control list-agent-runtimes --region us-east-1 --query 'agentRuntimes[?agentRuntimeName==`market_surveillance_workflow`]' --output table

clean:
	@echo "🧹 Cleaning temporary files..."
	@rm -f deployment/trust-policy-final.json
	@rm -f deployment/permissions-policy-final.json
	@echo "✅ Cleanup complete"
