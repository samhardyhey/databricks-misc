.PHONY: up-dev down-dev

# Start the cluster
up-dev:
	docker-compose up -d

# Stop the cluster
down-dev:
	docker-compose down

help:
	@echo "Usage: make <target>"
	@echo "Targets:"
	@echo "  up-dev - Start the cluster (directories auto-initialized in containers)"
	@echo "  down-dev - Stop the cluster"
	@echo "  help - Show this help message"

# default target
default: help