#!/bin/bash

# Script to build Forge LLM custom release
# This script builds the Forge application with LLM integration features

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Forge LLM Build Script"
echo "======================"
echo "Building Forge with LLM integration features..."
echo ""

# Check if Maven is available
if ! command -v mvn &> /dev/null; then
    echo "Error: Maven not found. Please install Maven"
    exit 1
fi

# Check if Java is available
if ! command -v java &> /dev/null; then
    echo "Error: Java not found. Please install Java 8 or later"
    exit 1
fi

echo "Java version:"
java -version
echo ""

echo "Maven version:"
mvn -version
echo ""

# Clean previous builds
echo "Cleaning previous builds..."
mvn clean

# Build the project
echo "Building Forge with LLM integration..."
mvn package -DskipTests

# Check if build was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Build completed successfully!"
    echo ""
    
    # Find the built desktop JAR with dependencies
    desktop_jar=$(find . -name "*gui*desktop*dependencies*.jar" | head -1)
    if [ -n "$desktop_jar" ]; then
        echo "Desktop JAR with dependencies: $desktop_jar"
        
        # Copy to a standard location
        mkdir -p build/
        cp "$desktop_jar" build/forge-gui-desktop-llm-$(date +%Y%m%d-%H%M%S).jar
        
        # Create a symlink for easy access
        ln -sf "$(basename build/forge-gui-desktop-llm-*.jar)" build/forge-gui-desktop-llm-latest.jar
        
        echo "Build artifacts available in: build/"
        ls -la build/
    else
        echo "Warning: Could not find desktop JAR with dependencies"
    fi
    
    # Show the size of key artifacts
    echo ""
    echo "Build artifacts:"
    find . -name "*.jar" -path "*/target/*" -type f -exec ls -lh {} \; | head -10
    
else
    echo ""
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "Build completed. You can now use the built JAR for your simulation system."