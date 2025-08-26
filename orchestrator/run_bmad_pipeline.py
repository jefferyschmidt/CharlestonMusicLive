#!/usr/bin/env python3
"""
Master BMAD Pipeline Orchestrator

Coordinates all BMAD agents in sequence: BA → Architect → Developer → Tester → Deployer
"""
import os
import pathlib
import time
from typing import Dict, List, Any
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
ORCHESTRATOR = ROOT / "orchestrator"

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def _run_agent(agent_name: str, agent_script: str, description: str) -> Dict[str, Any]:
    """Run a specific agent and capture its output."""
    print(f"\n{'='*60}")
    print(f"🚀 RUNNING {agent_name.upper()} AGENT")
    print(f"{'='*60}")
    print(f"📋 Description: {description}")
    print(f"⏱️ Starting at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if agent script exists
    script_path = ORCHESTRATOR / agent_script
    if not script_path.exists():
        return {
            "success": False,
            "error": f"Agent script {agent_script} not found",
            "output": "",
            "start_time": time.time(),
            "end_time": time.time()
        }
    
    # Run the agent script
    start_time = time.time()
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=ROOT,
            timeout=600  # 10 minute timeout per agent
        )
        
        end_time = time.time()
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return {
            "success": success,
            "error": None if success else f"Agent exited with code {result.returncode}",
            "output": output,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time
        }
        
    except subprocess.TimeoutExpired:
        end_time = time.time()
        return {
            "success": False,
            "error": "Agent execution timed out after 10 minutes",
            "output": "",
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time
        }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "error": f"Error running agent: {str(e)}",
            "output": "",
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time
        }

def _get_pipeline_configuration() -> Dict[str, Any]:
    """Get the pipeline configuration automatically for non-interactive operation."""
    print("🎯 BMAD Pipeline Configuration (Automated Mode)")
    print("=" * 50)
    
    config = {}
    
    # Automatically run all agents in sequence
    config["agents"] = [1, 2, 3, 4, 5]  # All agents: BA, Architect, Developer, Tester, Deployer
    print("✅ Running all agents: BA → Architect → Developer → Tester → Deployer")
    
    # Full pipeline mode (non-interactive)
    config["mode"] = 1  # Full pipeline
    print("✅ Mode: Full pipeline (non-interactive)")
    
    # Skip existing outputs to avoid duplication
    config["skip_existing"] = True
    print("✅ Skip existing outputs: Yes (avoid duplication)")
    
    return config

def _check_existing_outputs() -> Dict[str, bool]:
    """Check which agent outputs already exist."""
    existing = {}
    
    # Check for existing outputs
    docs_dir = ROOT / "docs"
    existing["ba"] = all([
        (docs_dir / "PRD.md").exists(),
        (docs_dir / "Stories.md").exists(),
        (docs_dir / "Glossary.md").exists()
    ])
    
    existing["architect"] = any([
        (ROOT / "architectural_analysis_*.md").exists(),
        (ROOT / "architectural_analysis_*.md").exists()
    ])
    
    existing["developer"] = any([
        (ROOT / "generated_implementation_*.py").exists(),
        (ROOT / "generated_tests_*.py").exists()
    ])
    
    existing["tester"] = any([
        (ROOT / "test_report_*.txt").exists()
    ])
    
    existing["deployer"] = any([
        (ROOT / "deployment_plan_*.md").exists(),
        (ROOT / "deploy" / "deployment_plan.md").exists()
    ])
    
    return existing

def _run_bmad_pipeline(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run the complete BMAD pipeline."""
    results = []
    
    # Agent definitions
    agents = {
        1: {
            "name": "BA",
            "script": "run_ba.py",
            "description": "Generate Product Requirements Document, User Stories, and Glossary"
        },
        2: {
            "name": "Architect", 
            "script": "run_architect.py",
            "description": "Design system architecture and establish coding patterns"
        },
        3: {
            "name": "Developer",
            "script": "run_developer.py", 
            "description": "Implement features from requirements following established patterns"
        },
        4: {
            "name": "Tester",
            "script": "run_tester.py",
            "description": "Run tests and validate functionality"
        },
        5: {
            "name": "Deployer",
            "script": "run_deployer.py",
            "description": "Handle deployment and infrastructure management"
        }
    }
    
    # Check existing outputs
    existing_outputs = _check_existing_outputs()
    
    # Run selected agents
    for agent_num in config["agents"]:
        if agent_num not in agents:
            print(f"⚠️ Unknown agent number: {agent_num}")
            continue
        
        agent = agents[agent_num]
        agent_key = agent["name"].lower()
        
        # Check if we should skip this agent
        if config["skip_existing"] and existing_outputs.get(agent_key, False):
            print(f"⏭️ Skipping {agent['name']} - outputs already exist")
            results.append({
                "agent": agent["name"],
                "skipped": True,
                "reason": "Outputs already exist"
            })
            continue
        
        # Run the agent
        result = _run_agent(
            agent["name"],
            agent["script"], 
            agent["description"]
        )
        result["agent"] = agent["name"]
        result["skipped"] = False
        
        results.append(result)
        
        # Display result
        if result["success"]:
            print(f"✅ {agent['name']} completed successfully in {result['duration']:.1f}s")
        else:
            print(f"❌ {agent['name']} failed: {result['error']}")
        
        # Continue automatically to next agent (non-interactive mode)
        if agent_num != config["agents"][-1]:
            print(f"⏭️ Continuing to next agent automatically...")
    
    return results

def _generate_pipeline_report(results: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
    """Generate a comprehensive pipeline report."""
    client, model = _anthropic_client()
    
    # Prepare context for the orchestrator agent
    context = f"""
BMAD Pipeline Results:
{chr(10).join([f"{r['agent']}: {'SKIPPED' if r.get('skipped') else 'SUCCESS' if r.get('success', False) else 'FAILED'} - {r.get('error', '')}" for r in results])}

Pipeline Configuration:
- Agents run: {config['agents']}
- Mode: {'Full pipeline' if config['mode'] == 1 else 'Interactive' if config['mode'] == 2 else 'Dry run'}
- Skip existing: {config['skip_existing']}

Execution Summary:
{chr(10).join([f"{r['agent']}: {r.get('duration', 0):.1f}s" for r in results if not r.get('skipped')])}
"""
    
    prompt = f"""You are the Orchestrator Agent for MusicLive. Analyze the BMAD pipeline results and provide a comprehensive report.

Context:
{context}

Please provide a detailed analysis including:
1. Overall pipeline success/failure assessment
2. Agent-by-agent performance analysis
3. Recommendations for improvement
4. Next steps for the project
5. Lessons learned and best practices

Format your response clearly with sections and actionable insights."""

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.1,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text if response.content else "No analysis generated"

def main():
    """Main BMAD pipeline orchestrator."""
    print("🎯 MusicLive BMAD Pipeline Orchestrator")
    print("=" * 60)
    print("Business Analysis → Modeling → Architecture → Development")
    print("=" * 60)
    
    # Get pipeline configuration
    config = _get_pipeline_configuration()
    
    if config["mode"] == 3:
        # Dry run mode
        print("\n🔍 DRY RUN MODE")
        print("Agents that would be run:")
        for agent_num in config["agents"]:
            if agent_num == 1:
                print("  1. BA - Generate PRD, Stories, Glossary")
            elif agent_num == 2:
                print("  2. Architect - Design system architecture")
            elif agent_num == 3:
                print("  3. Developer - Implement features")
            elif agent_num == 4:
                print("  4. Tester - Run tests and validate")
            elif agent_num == 5:
                print("  5. Deployer - Handle deployment")
        return
    
    # Run the pipeline
    print(f"\n🚀 Starting BMAD pipeline with {len(config['agents'])} agents...")
    start_time = time.time()
    
    results = _run_bmad_pipeline(config)
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Generate comprehensive report
    print("\n📋 Generating pipeline report...")
    report = _generate_pipeline_report(results, config)
    
    # Display final results
    print("\n" + "="*60)
    print("🎉 BMAD PIPELINE COMPLETED!")
    print("="*60)
    
    print(f"\n⏱️ Total pipeline duration: {total_duration:.1f}s")
    
    # Summary
    successful = len([r for r in results if r.get("success", False)])
    skipped = len([r for r in results if r.get("skipped", False)])
    failed = len([r for r in results if not r.get("success", False) and not r.get("skipped", False)])
    
    print(f"✅ Successful: {successful}")
    print(f"⏭️ Skipped: {skipped}")
    print(f"❌ Failed: {failed}")
    
    # Detailed report
    print("\n📋 PIPELINE ANALYSIS:")
    print("-" * 40)
    print(report)
    
    # Save pipeline report
    report_file = ROOT / f"bmad_pipeline_report_{int(time.time())}.md"
    
    # Format as markdown
    markdown_content = [
        "# BMAD Pipeline Report",
        "",
        f"**Pipeline completed at:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total duration:** {total_duration:.1f}s",
        f"**Agents run:** {config['agents']}",
        f"**Mode:** {'Full pipeline' if config['mode'] == 1 else 'Interactive' if config['mode'] == 2 else 'Dry run'}",
        "",
        "## Results Summary",
        f"- ✅ Successful: {successful}",
        f"- ⏭️ Skipped: {skipped}",
        f"- ❌ Failed: {failed}",
        "",
        "## Detailed Analysis",
        report,
        "",
        "## Agent Results",
    ]
    
    for result in results:
        if result.get("skipped"):
            markdown_content.append(f"### {result['agent']} - SKIPPED")
            markdown_content.append(f"**Reason:** {result['reason']}")
        else:
            markdown_content.append(f"### {result['agent']}")
            markdown_content.append(f"**Status:** {'✅ SUCCESS' if result.get('success', False) else '❌ FAILED'}")
            markdown_content.append(f"**Duration:** {result.get('duration', 0):.1f}s")
            if result.get('error'):
                markdown_content.append(f"**Error:** {result['error']}")
        markdown_content.append("")
    
    report_file.write_text('\n'.join(markdown_content), encoding='utf-8')
    print(f"\n💾 Pipeline report saved to: {report_file}")

if __name__ == "__main__":
    import sys
    main()
