#!/usr/bin/env python3
"""
Developer Agent Runner

Takes user stories and requirements, generates implementation code following established patterns.
"""
import os
import pathlib
import json
import time
from typing import Dict, Any, List
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
COLLECTOR = ROOT / "collector"
API = ROOT / "api"
TESTS = ROOT / "tests"

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def _read_file(path: pathlib.Path) -> str:
    """Read file content, return empty string if file doesn't exist."""
    return path.read_text(encoding="utf-8") if path.exists() else ""

def _analyze_codebase() -> str:
    """Analyze existing codebase to understand patterns and structure."""
    analysis = []
    
    # Analyze collector patterns
    if (COLLECTOR / "extractors" / "base.py").exists():
        base_extractor = _read_file(COLLECTOR / "extractors" / "base.py")
        analysis.append(f"Base Extractor Interface:\n{base_extractor}\n")
    
    if (COLLECTOR / "extractors" / "sample_venue.py").exists():
        sample_extractor = _read_file(COLLECTOR / "extractors" / "sample_venue.py")
        analysis.append(f"Sample Venue Extractor:\n{sample_extractor}\n")
    
    # Analyze API patterns
    if (API / "main.py").exists():
        api_main = _read_file(API / "main.py")
        analysis.append(f"API Main:\n{api_main}\n")
    
    # Analyze test patterns
    if (TESTS / "test_extractor_sample_venue.py").exists():
        test_file = _read_file(TESTS / "test_extractor_sample_venue.py")
        analysis.append(f"Test Pattern:\n{test_file}\n")
    
    return "\n".join(analysis)

def _get_development_task(args) -> str:
    """Get the development task to perform."""
    # For automation, use a default comprehensive task
    # Can be overridden via environment variables or command line args
    import os
    
    if args and hasattr(args, 'task') and args.task:
        return args.task
    
    choice = os.environ.get("DEVELOPER_TASK", "1")
    
    if choice == "1":
        venue_name = getattr(args, 'venue', None) or os.environ.get("DEVELOPER_VENUE", "Music Farm")
        source_url = getattr(args, 'source', None) or os.environ.get("DEVELOPER_SOURCE", "https://musicfarm.com/events")
        return f"Create a new venue extractor for '{venue_name}' that scrapes from {source_url}"
    elif choice == "2":
        endpoint = getattr(args, 'endpoint', None) or os.environ.get("DEVELOPER_ENDPOINT", "/api/v1/sites/{site}/search")
        return f"Add new API endpoint: {endpoint}"
    elif choice == "3":
        operation = getattr(args, 'operation', None) or os.environ.get("DEVELOPER_OPERATION", "database optimization")
        return f"Implement database operation: {operation}"
    elif choice == "4":
        component = getattr(args, 'component', None) or os.environ.get("DEVELOPER_COMPONENT", "extractor system")
        return f"Create comprehensive test suite for: {component}"
    elif choice == "5":
        custom_task = os.environ.get("DEVELOPER_CUSTOM", "Create a new venue extractor for 'Music Farm' that scrapes from https://musicfarm.com/events")
        return custom_task
    else:
        return "Create a new venue extractor for 'Music Farm' that scrapes from https://musicfarm.com/events"

def main():
    """Main development agent runner."""
    client, model = _anthropic_client()
    
    # Load project context
    prd = _read_file(DOCS / "PRD.md")
    stories = _read_file(DOCS / "Stories.md")
    glossary = _read_file(DOCS / "Glossary.md")
    
    if not prd or not stories:
        print("Warning: PRD.md or Stories.md not found. Proceeding with limited context.")
    
    # Analyze existing codebase
    codebase_analysis = _analyze_codebase()
    
    # Get development task
    development_task = _get_development_task(None)
    
    # Build prompt for developer agent
    system_prompt = f"""You are the Developer Agent for MusicLive. Your task is to implement: {development_task}

You MUST follow these rules:
1. Analyze the existing codebase patterns and follow them exactly
2. Generate complete, working code that can be immediately used
3. Include proper imports, error handling, and documentation
4. Follow the established Extractor interface and ExtractResult dataclass
5. Use the same testing patterns and fixtures approach
6. Ensure all code is deterministic and testable
7. Include comprehensive tests for new functionality

Output your response in this exact format:
===IMPLEMENTATION===
[Complete implementation code with proper file structure]

===TESTS===
[Complete test code following existing patterns]

===USAGE===
[How to use the new functionality]

===NOTES===
[Any important implementation details or considerations]
"""

    user_prompt = f"""Project Context:
PRD: {prd[:1000]}...
Stories: {stories[:1000]}...
Glossary: {glossary[:500]}...

Codebase Analysis:
{codebase_analysis}

Development Task: {development_task}

Please implement this following the established patterns in the codebase."""

    print(f"\n🎯 Development Task: {development_task}")
    print("🤖 Developer Agent is working...")
    
    # Call the developer agent
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0.1,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ]
    )
    
    # Extract response content
    content = response.content[0].text if response.content else "No response generated"
    
    # Parse the response sections
    sections = {}
    current_section = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('===') and line.endswith('==='):
            if current_section:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line.strip('=')
            current_content = []
        elif current_section:
            current_content.append(line)
    
    # Add the last section
    if current_section and current_content:
        sections[current_section] = '\n'.join(current_content).strip()
    
    # Display results
    print("\n" + "="*60)
    print("🎉 DEVELOPMENT AGENT COMPLETED!")
    print("="*60)
    
    for section_name, section_content in sections.items():
        print(f"\n📋 {section_name.upper()}")
        print("-" * 40)
        print(section_content)
    
    # Save implementation to file
    if 'IMPLEMENTATION' in sections:
        output_file = ROOT / f"generated_implementation_{int(time.time())}.py"
        output_file.write_text(sections['IMPLEMENTATION'], encoding='utf-8')
        print(f"\n💾 Implementation saved to: {output_file}")
    
    if 'TESTS' in sections:
        test_file = ROOT / f"generated_tests_{int(time.time())}.py"
        test_file.write_text(sections['TESTS'], encoding='utf-8')
        print(f"🧪 Tests saved to: {test_file}")

if __name__ == "__main__":
    main()
