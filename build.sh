#!/bin/bash
# Simple build script for OpenShift Cost Estimator

set -e

echo "🚀 Building OpenShift Cost Estimator..."

# Check if we're in the right directory
if [ ! -f "openshift-cost-estimator.spec" ]; then
    echo "❌ Error: openshift-cost-estimator.spec not found"
    echo "   Please run this script from the project root directory"
    exit 1
fi

# Install dependencies if needed
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/

# Build with PyInstaller
echo "🔨 Building executable..."
python -m PyInstaller openshift-cost-estimator.spec --clean --noconfirm

# Check if build succeeded
if [ -f "dist/openshift-cost-estimator" ]; then
    echo "✅ Build completed successfully!"
    echo "   Executable: $(pwd)/dist/openshift-cost-estimator"
    
    # Make executable
    chmod +x dist/openshift-cost-estimator
    
    # Test the executable
    echo "🧪 Testing executable..."
    if ./dist/openshift-cost-estimator --help > /dev/null 2>&1; then
        echo "✅ Executable test passed"
    else
        echo "⚠️  Executable test failed, but build completed"
    fi
    
    # Show size
    SIZE=$(du -h dist/openshift-cost-estimator | cut -f1)
    echo "   Size: $SIZE"
    
else
    echo "❌ Build failed - executable not found"
    exit 1
fi

echo "🎉 Done! You can now run: ./dist/openshift-cost-estimator --help"