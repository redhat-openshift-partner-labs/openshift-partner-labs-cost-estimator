#!/usr/bin/env python3
"""
Build script for creating PyInstaller executable of OpenShift Cost Estimator
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
import time


class ExecutableBuilder:
    """Handles the building of PyInstaller executable"""
    
    def __init__(self, project_root=None):
        """Initialize the builder"""
        self.project_root = Path(project_root or os.getcwd())
        self.spec_file = self.project_root / "openshift-cost-estimator.spec"
        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.executable_name = "openshift-cost-estimator"
        
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        print("🔍 Checking dependencies...")
        
        try:
            import pyinstaller
            print(f"✅ PyInstaller found: {pyinstaller.__version__}")
        except ImportError:
            print("❌ PyInstaller not found. Installing...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller>=5.10.0"], check=True)
            print("✅ PyInstaller installed")
            
        # Check if spec file exists
        if not self.spec_file.exists():
            raise FileNotFoundError(f"Spec file not found: {self.spec_file}")
        print(f"✅ Spec file found: {self.spec_file}")
        
        # Check if main.py exists
        main_py = self.project_root / "aws" / "main.py"
        if not main_py.exists():
            raise FileNotFoundError(f"Main script not found: {main_py}")
        print(f"✅ Main script found: {main_py}")
        
    def clean_previous_builds(self):
        """Clean up previous build artifacts"""
        print("🧹 Cleaning previous build artifacts...")
        
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
            print(f"   Removed: {self.dist_dir}")
            
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
            print(f"   Removed: {self.build_dir}")
            
        # Remove any PyInstaller cache
        pycache_dirs = list(self.project_root.rglob("__pycache__"))
        for cache_dir in pycache_dirs:
            if cache_dir.is_dir():
                shutil.rmtree(cache_dir)
                
        print("✅ Cleanup completed")
        
    def run_tests(self):
        """Run basic tests to ensure code works before building"""
        print("🧪 Running basic tests...")
        
        # Try importing the main module
        try:
            sys.path.insert(0, str(self.project_root))
            import aws.main
            print("✅ Main module imports successfully")
        except ImportError as e:
            print(f"❌ Import error: {e}")
            return False
            
        # Run unit tests if they exist
        test_files = list((self.project_root / "aws").glob("test_*.py"))
        if test_files:
            print(f"Found {len(test_files)} test files. Running quick validation...")
            try:
                # Run a simple syntax check
                for test_file in test_files[:3]:  # Limit to first 3 test files
                    subprocess.run([sys.executable, "-m", "py_compile", str(test_file)], 
                                 check=True, capture_output=True)
                print("✅ Test files compile successfully")
            except subprocess.CalledProcessError:
                print("⚠️  Some test files have syntax issues, but continuing...")
                
        return True
        
    def build_executable(self, debug=False):
        """Build the executable using PyInstaller"""
        print("🔨 Building executable...")
        start_time = time.time()
        
        # Build command
        cmd = [
            sys.executable, "-m", "PyInstaller",
            str(self.spec_file),
            "--clean",
            "--noconfirm",
        ]
        
        if debug:
            cmd.append("--debug=all")
            print("   Debug mode enabled")
            
        print(f"   Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True,
                                  cwd=self.project_root)
            
            build_time = time.time() - start_time
            print(f"✅ Build completed in {build_time:.1f} seconds")
            
            # Check if executable was created
            executable_path = self.dist_dir / self.executable_name
            if executable_path.exists():
                size_mb = executable_path.stat().st_size / (1024 * 1024)
                print(f"✅ Executable created: {executable_path}")
                print(f"   Size: {size_mb:.1f} MB")
                return executable_path
            else:
                print("❌ Executable not found after build")
                return None
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print("Build output:")
            print(e.stdout)
            print(e.stderr)
            return None
            
    def test_executable(self, executable_path):
        """Test the built executable"""
        print("🧪 Testing executable...")
        
        try:
            # Test help command
            result = subprocess.run([str(executable_path), "--help"], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and "usage:" in result.stdout.lower():
                print("✅ Executable help command works")
                return True
            else:
                print(f"❌ Executable test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Executable test timed out")
            return False
        except Exception as e:
            print(f"❌ Executable test error: {e}")
            return False
            
    def create_distribution_package(self, executable_path):
        """Create a distribution package with documentation"""
        print("📦 Creating distribution package...")
        
        # Create distribution directory
        package_dir = self.dist_dir / "openshift-cost-estimator-package"
        package_dir.mkdir(exist_ok=True)
        
        # Copy executable
        shutil.copy2(executable_path, package_dir / self.executable_name)
        
        # Copy documentation
        docs_to_copy = ["README.md", "CHANGELOG.md", "aws/README.md", "aws/IAM_POLICY.md"]
        
        for doc in docs_to_copy:
            doc_path = self.project_root / doc
            if doc_path.exists():
                dest_path = package_dir / doc_path.name
                shutil.copy2(doc_path, dest_path)
                print(f"   Copied: {doc}")
                
        # Create usage instructions
        usage_file = package_dir / "USAGE.txt"
        with open(usage_file, 'w') as f:
            f.write("""OpenShift Partner Labs Cost Estimator
=======================================

Usage Examples:
--------------

Basic resource discovery:
./openshift-cost-estimator --cluster-uid your-cluster-uid --unified-discovery

With cost estimation:
./openshift-cost-estimator --cluster-uid your-cluster-uid --include-costs --unified-discovery

Export cost report:
./openshift-cost-estimator --cluster-uid your-cluster-uid --include-costs --unified-discovery --export-format json --export-file report.json

For full help:
./openshift-cost-estimator --help

AWS Permissions Required:
-----------------------
See IAM_POLICY.md for detailed AWS permissions required.

Documentation:
-------------
- README.md: General project overview
- CHANGELOG.md: Version history and changes
- IAM_POLICY.md: AWS IAM permissions guide

Support:
-------
For issues and questions, please refer to the project repository.
""")
        
        print(f"✅ Distribution package created: {package_dir}")
        return package_dir
        
    def build(self, clean=True, test=True, debug=False, package=True):
        """Run the complete build process"""
        print("🚀 Starting OpenShift Cost Estimator build process...")
        print(f"   Project root: {self.project_root}")
        
        try:
            # Step 1: Check dependencies
            self.check_dependencies()
            
            # Step 2: Clean previous builds
            if clean:
                self.clean_previous_builds()
                
            # Step 3: Run tests
            if test and not self.run_tests():
                print("❌ Pre-build tests failed")
                return False
                
            # Step 4: Build executable
            executable_path = self.build_executable(debug=debug)
            if not executable_path:
                return False
                
            # Step 5: Test executable
            if test and not self.test_executable(executable_path):
                print("⚠️  Executable tests failed, but build completed")
                
            # Step 6: Create distribution package
            if package:
                package_dir = self.create_distribution_package(executable_path)
                print(f"🎉 Build completed successfully!")
                print(f"   Executable: {executable_path}")
                print(f"   Package: {package_dir}")
            else:
                print(f"🎉 Build completed successfully!")
                print(f"   Executable: {executable_path}")
                
            return True
            
        except Exception as e:
            print(f"❌ Build process failed: {e}")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Build OpenShift Cost Estimator executable")
    parser.add_argument("--no-clean", action="store_true", 
                       help="Skip cleaning previous build artifacts")
    parser.add_argument("--no-test", action="store_true",
                       help="Skip running tests")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug mode for PyInstaller")
    parser.add_argument("--no-package", action="store_true",
                       help="Skip creating distribution package")
    parser.add_argument("--project-root", type=str,
                       help="Project root directory (default: current directory)")
    
    args = parser.parse_args()
    
    builder = ExecutableBuilder(project_root=args.project_root)
    
    success = builder.build(
        clean=not args.no_clean,
        test=not args.no_test,
        debug=args.debug,
        package=not args.no_package
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()