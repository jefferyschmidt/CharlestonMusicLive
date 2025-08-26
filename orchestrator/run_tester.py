#!/usr/bin/env python3
"""
Tester Agent Runner

Executes tests, validates code quality, and ensures functionality works correctly.
"""
import os
import pathlib
import subprocess
import sys
import time
from typing import Dict, List, Tuple
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def run_pytest_tests() -> Tuple[bool, str]:
    """Run the full pytest test suite and return results."""
    print("🧪 Running pytest test suite...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=300  # 5 minute timeout
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
    
    except subprocess.TimeoutExpired:
        return False, "Test execution timed out after 5 minutes"
    except Exception as e:
        return False, f"Error running tests: {str(e)}"

def run_specific_test(test_path: str) -> Tuple[bool, str]:
    """Run a specific test file or test function."""
    print(f"🧪 Running specific test: {test_path}")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v"],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=120
        )
        
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, output
    
    except subprocess.TimeoutExpired:
        return False, f"Test execution timed out for {test_path}"
    except Exception as e:
        return False, f"Error running test {test_path}: {str(e)}"

def analyze_test_coverage() -> str:
    """Analyze test coverage and identify gaps."""
    print("📊 Analyzing test coverage...")
    
    # Simple coverage analysis based on file structure
    test_files = list(TESTS.rglob("test_*.py"))
    source_files = []
    
    # Find source files
    for pattern in ["*.py", "extractors/*.py", "api/*.py"]:
        source_files.extend(ROOT.rglob(pattern))
    
    # Filter out test files and __init__.py
    source_files = [f for f in source_files if "test_" not in f.name and f.name != "__init__.py"]
    
    coverage_info = []
    coverage_info.append(f"Total source files: {len(source_files)}")
    coverage_info.append(f"Total test files: {len(test_files)}")
    
    # Check for specific components
    components = {
        "collector/extractors": "Extractor implementations",
        "api": "API endpoints", 
        "collector/cli": "CLI functionality",
        "db": "Database operations"
    }
    
    for path, description in components.items():
        source_count = len([f for f in source_files if path in str(f)])
        test_count = len([f for f in test_files if path in str(f)])
        coverage_info.append(f"{description}: {source_count} source, {test_count} test files")
    
    return "\n".join(coverage_info)

def validate_code_quality() -> str:
    """Run code quality checks (linting, formatting)."""
    print("🔍 Running code quality checks...")
    
    quality_checks = []
    
    # Check if ruff is available
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "."],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=60
        )
        
        if result.returncode == 0:
            quality_checks.append("✅ Ruff linting: PASSED")
        else:
            quality_checks.append(f"❌ Ruff linting: FAILED\n{result.stdout}")
    
    except Exception as e:
        quality_checks.append(f"⚠️ Ruff linting: Not available ({str(e)})")
    
    # Check if black is available
    try:
        result = subprocess.run(
            [sys.executable, "-m", "black", "--check", "."],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=60
        )
        
        if result.returncode == 0:
            quality_checks.append("✅ Black formatting: PASSED")
        else:
            quality_checks.append(f"❌ Black formatting: FAILED\n{result.stdout}")
    
    except Exception as e:
        quality_checks.append(f"⚠️ Black formatting: Not available ({str(e)})")
    
    return "\n".join(quality_checks)

def generate_test_report(test_results: Dict[str, Tuple[bool, str]], coverage: str, quality: str) -> str:
    """Generate a comprehensive test report."""
    client, model = _anthropic_client()
    
    # Prepare context for the tester agent
    test_summary = chr(10).join([f"{name}: {'PASS' if success else 'FAIL'}" for name, (success, _) in test_results.items()])
    detailed_outputs = chr(10).join([f"=== {name} ===\n{output[:500]}..." for name, (_, output) in test_results.items()])
    
    context = f"""
Test Results Summary:
{test_summary}

Test Coverage Analysis:
{coverage}

Code Quality Checks:
{quality}

Detailed Test Outputs:
{detailed_outputs}
"""
    
    prompt = f"""You are the Tester Agent for MusicLive. Analyze the test results and provide a comprehensive report.

Context:
{context}

Please provide a detailed analysis including:
1. Overall test status and pass/fail summary
2. Test coverage assessment and recommendations
3. Code quality analysis
4. Specific issues found and suggested fixes
5. Recommendations for improving test coverage
6. Next steps for testing

Format your response clearly with sections and actionable insights."""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text if response.content else "No analysis generated"

def main():
    """Main tester agent runner."""
    print("🧪 MusicLive Tester Agent")
    print("=" * 50)
    
    # For automation, use default scope (full test suite)
    # Can be overridden via environment variable TESTER_SCOPE
    import os
    choice = os.environ.get("TESTER_SCOPE", "1")
    
    test_results = {}
    
    if choice == "1":
        # Full test suite
        print("Running full test suite...")
        success, output = run_pytest_tests()
        test_results["Full Test Suite"] = (success, output)
        
    elif choice == "2":
        # Specific test file
        test_file = os.environ.get("TESTER_FILE", "tests/test_api_endpoints.py")
        if not test_file.startswith("tests/"):
            test_file = f"tests/{test_file}"
        print(f"Running specific test file: {test_file}")
        success, output = run_specific_test(test_file)
        test_results[f"Test File: {test_file}"] = (success, output)
        
    elif choice == "3":
        # Specific test function
        test_path = os.environ.get("TESTER_FUNCTION", "tests/test_api_endpoints.py::test_admin_status_endpoint")
        print(f"Running specific test function: {test_path}")
        success, output = run_specific_test(test_path)
        test_results[f"Test Function: {test_path}"] = (success, output)
        
    elif choice == "4":
        # Quality analysis only
        print("Running quality analysis only...")
        test_results["Quality Analysis"] = (True, "Skipped test execution")
        
    else:
        print("Invalid choice, running full test suite...")
        success, output = run_pytest_tests()
        test_results["Full Test Suite"] = (success, output)
    
    # Always run coverage and quality analysis
    coverage = analyze_test_coverage()
    quality = validate_code_quality()
    
    # Generate comprehensive report
    print("\n📋 Generating test report...")
    report = generate_test_report(test_results, coverage, quality)
    
    # Display results
    print("\n" + "=" * 60)
    print("🎉 TESTING COMPLETED!")
    print("=" * 60)
    
    # Quick summary
    print("\n📊 QUICK SUMMARY:")
    for name, (success, _) in test_results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\n📈 Coverage: {coverage.split(chr(10))[0]}")
    
    # Detailed report
    print("\n📋 DETAILED REPORT:")
    print("-" * 40)
    print(report)
    
    # Save report to file
    report_file = ROOT / f"test_report_{int(time.time())}.txt"
    report_file.write_text(report, encoding='utf-8')
    print(f"\n💾 Test report saved to: {report_file}")

if __name__ == "__main__":
    main()
