# Makefile for OpenShift Partner Labs Cost Estimator

.PHONY: help install build build-debug clean test package dist-clean lint format check-deps

# Default target
help:
	@echo "OpenShift Partner Labs Cost Estimator - Build Commands"
	@echo "=================================================="
	@echo ""
	@echo "Available targets:"
	@echo "  help        - Show this help message"
	@echo "  install     - Install dependencies"
	@echo "  build       - Build executable (default)"
	@echo "  build-debug - Build executable with debug info"
	@echo "  test        - Run tests"
	@echo "  package     - Create distribution package"
	@echo "  clean       - Clean build artifacts"
	@echo "  dist-clean  - Clean all generated files"
	@echo "  lint        - Run code linting (if available)"
	@echo "  format      - Format code (if available)"
	@echo "  check-deps  - Check if build dependencies are installed"
	@echo ""
	@echo "Examples:"
	@echo "  make install build    # Install deps and build"
	@echo "  make build-debug      # Build with debug information"
	@echo "  make clean build      # Clean and rebuild"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

# Check build dependencies
check-deps:
	@echo "🔍 Checking build dependencies..."
	@python -c "import pyinstaller; print(f'✅ PyInstaller {pyinstaller.__version__} found')" || \
		(echo "❌ PyInstaller not found. Run 'make install' first" && exit 1)
	@python -c "import boto3; print(f'✅ boto3 {boto3.__version__} found')" || \
		(echo "❌ boto3 not found. Run 'make install' first" && exit 1)

# Build executable
build: check-deps
	@echo "🔨 Building executable..."
	python build_executable.py

# Build with debug information
build-debug: check-deps
	@echo "🔨 Building executable with debug info..."
	python build_executable.py --debug

# Run tests
test:
	@echo "🧪 Running tests..."
	@if [ -d "aws" ] && [ -n "$$(find aws -name 'test_*.py' -print -quit)" ]; then \
		cd aws && python -m unittest discover -s . -p "test_*.py" -v; \
	else \
		echo "No tests found in aws/ directory"; \
	fi

# Create distribution package
package: build
	@echo "📦 Creating distribution package..."
	@if [ -f "dist/openshift-cost-estimator" ]; then \
		echo "✅ Executable found, package should be ready in dist/"; \
	else \
		echo "❌ Executable not found. Run 'make build' first"; \
		exit 1; \
	fi

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf dist/ build/ __pycache__ */__pycache__ */*/__pycache__
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Clean all generated files
dist-clean: clean
	@echo "🧹 Deep cleaning all generated files..."
	rm -rf *.egg-info/
	find . -name ".DS_Store" -delete

# Lint code (if tools available)
lint:
	@echo "🔍 Running code linting..."
	@command -v flake8 >/dev/null 2>&1 && flake8 aws/ || echo "flake8 not found, skipping"
	@command -v pylint >/dev/null 2>&1 && pylint aws/ || echo "pylint not found, skipping"

# Format code (if tools available)
format:
	@echo "🎨 Formatting code..."
	@command -v black >/dev/null 2>&1 && black aws/ || echo "black not found, skipping"
	@command -v isort >/dev/null 2>&1 && isort aws/ || echo "isort not found, skipping"

# Build and test workflow
all: install test build

# Quick build without tests
quick: check-deps
	@echo "⚡ Quick build (no tests)..."
	python build_executable.py --no-test

# Development build
dev: check-deps
	@echo "👩‍💻 Development build..."
	python build_executable.py --no-clean --no-test --debug

# Release build
release: clean install test build
	@echo "🚀 Release build complete!"
	@if [ -f "dist/openshift-cost-estimator" ]; then \
		echo "✅ Executable ready: $$(pwd)/dist/openshift-cost-estimator"; \
		du -h dist/openshift-cost-estimator; \
	fi