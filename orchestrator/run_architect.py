#!/usr/bin/env python3
"""
Architect Agent Runner

Designs system architecture, establishes patterns, and reviews code for architectural compliance.
"""
import os
import pathlib
import json
import time
from typing import Dict, List, Any
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
COLLECTOR = ROOT / "collector"
API = ROOT / "api"
DB = ROOT / "db"

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def _read_file(path: pathlib.Path) -> str:
    """Read file content, return empty string if file doesn't exist."""
    return path.read_text(encoding='utf-8') if path.exists() else ""

def _analyze_current_architecture() -> str:
    """Analyze the current system architecture and patterns."""
    analysis = []
    
    # Analyze project structure
    analysis.append("=== PROJECT STRUCTURE ANALYSIS ===")
    
    # Collector architecture
    if (COLLECTOR / "extractors" / "base.py").exists():
        base_extractor = _read_file(COLLECTOR / "extractors" / "base.py")
        analysis.append(f"Extractor Interface Pattern:\n{base_extractor}\n")
    
    # API architecture
    if (API / "main.py").exists():
        api_main = _read_file(API / "main.py")
        analysis.append(f"API Architecture:\n{api_main}\n")
    
    # Database architecture
    if (DB / "migrations" / "V002__core_entities.sql").exists():
        db_schema = _read_file(DB / "migrations" / "V002__core_entities.sql")
        analysis.append(f"Database Schema:\n{db_schema[:1000]}...\n")
    
    # Configuration and dependencies
    if (ROOT / "pyproject.toml").exists():
        pyproject = _read_file(ROOT / "pyproject.toml")
        analysis.append(f"Project Configuration:\n{pyproject}\n")
    
    return "\n".join(analysis)

def _get_architectural_task() -> str:
    """Get the architectural task to perform."""
    # For automation, use a default comprehensive task
    # Can be overridden via environment variable ARCHITECT_TASK
    import os
    task = os.environ.get("ARCHITECT_TASK", "1")
    
    if task == "1":
        return "Review the current MusicLive architecture and provide recommendations for improvement"
    elif task == "2":
        return "Design database schema improvements and optimization strategies"
    elif task == "3":
        area = os.environ.get("ARCHITECT_AREA", "API design")
        return f"Establish coding patterns for: {area}"
    elif task == "4":
        file_path = os.environ.get("ARCHITECT_FILE", "api/main.py")
        return f"Review {file_path} for architectural compliance and suggest improvements"
    elif task == "5":
        return "Design scalability improvements for the MusicLive system"
    elif task == "6":
        return os.environ.get("ARCHITECT_CUSTOM", "Review the current MusicLive architecture and provide recommendations for improvement")
    else:
        return "Review the current MusicLive architecture and provide recommendations for improvement"

def _analyze_specific_file(file_path: str) -> str:
    """Analyze a specific file for architectural review."""
    full_path = ROOT / file_path
    if not full_path.exists():
        return f"File {file_path} not found"
    
    content = _read_file(full_path)
    return f"File: {file_path}\nContent:\n{content}"

def main():
    """Main architect agent runner."""
    client, model = _anthropic_client()
    
    # Load project context
    prd = _read_file(DOCS / "PRD.md")
    stories = _read_file(DOCS / "Stories.md")
    glossary = _read_file(DOCS / "Glossary.md")
    
    if not prd or not stories:
        print("Warning: PRD.md or Stories.md not found. Proceeding with limited context.")
    
    # Analyze current architecture
    current_arch = _analyze_current_architecture()
    
    # Get architectural task
    architectural_task = _get_architectural_task()
    
    # If reviewing a specific file, analyze it
    file_analysis = ""
    if "review" in architectural_task.lower() and "file" in architectural_task.lower():
        file_path = os.environ.get("ARCHITECT_FILE", "api/main.py") # Use default if not set
        file_analysis = _analyze_specific_file(file_path)
    
    # Build prompt for architect agent
    system_prompt = f"""You are the Architect Agent for MusicLive. Your task is to: {architectural_task}

You MUST provide:
1. Architectural analysis and recommendations
2. Design patterns and principles to follow
3. Specific implementation guidance
4. Scalability and maintainability considerations
5. Code review feedback (if applicable)
6. Next steps for architectural improvements

Output your response in this exact format:
===ARCHITECTURAL_ANALYSIS===
[Analysis of current architecture and recommendations]

===DESIGN_PATTERNS===
[Established patterns and principles to follow]

===IMPLEMENTATION_GUIDANCE===
[Specific guidance for implementation]

===SCALABILITY_CONSIDERATIONS===
[Scalability and maintainability recommendations]

===CODE_REVIEW===
[Code review feedback if applicable]

===NEXT_STEPS===
[Actionable next steps for architectural improvements]
"""

    file_analysis_part = f"File Analysis:\n{file_analysis}" if file_analysis else ""
    user_prompt = f"""Project Context:
PRD: {prd[:1000]}...
Stories: {stories[:1000]}...
Glossary: {glossary[:500]}...

Current Architecture Analysis:
{current_arch}

{file_analysis_part}

Architectural Task: {architectural_task}

Please provide comprehensive architectural guidance following the established patterns in the codebase."""

    print(f"\n🏗️ Architectural Task: {architectural_task}")
    print("🤖 Architect Agent is working...")
    
    # Call the architect agent
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        temperature=0.1,
        messages=[
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": system_prompt.strip()}
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
    print("🎉 ARCHITECT AGENT COMPLETED!")
    print("="*60)
    
    for section_name, section_content in sections.items():
        print(f"\n📋 {section_name.upper()}")
        print("-" * 40)
        print(section_content)
    
    # Save architectural analysis to file
    if sections:
        output_file = ROOT / f"architectural_analysis_{int(time.time())}.md"
        
        # Format as markdown
        markdown_content = []
        for section_name, section_content in sections.items():
            markdown_content.append(f"# {section_name.replace('_', ' ').title()}")
            markdown_content.append("")
            markdown_content.append(section_content)
            markdown_content.append("")
        
        output_file.write_text('\n'.join(markdown_content), encoding='utf-8')
        print(f"\n💾 Architectural analysis saved to: {output_file}")

if __name__ == "__main__":
    main()
