#!/usr/bin/env python3
"""
Deployer Agent Runner

Handles deployment, CI/CD, and infrastructure management for MusicLive.
Optimized for: Neon Postgres + Fly.io + Cloudflare R2 + GitHub Actions
"""
import os
import pathlib
import subprocess
import sys
from typing import Dict, List, Tuple
from anthropic import Anthropic

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
GITHUB = ROOT / ".github"

def _anthropic_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key), os.environ.get("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")

def _analyze_current_deployment() -> str:
    """Analyze the current deployment configuration and infrastructure."""
    analysis = []
    
    # Check for deployment configurations
    if DEPLOY.exists():
        deploy_files = list(DEPLOY.glob("*"))
        analysis.append(f"Deployment directory contains: {[f.name for f in deploy_files]}")
        
        if (DEPLOY / "README.md").exists():
            deploy_readme = (DEPLOY / "README.md").read_text(encoding='utf-8')
            analysis.append(f"Deployment README:\n{deploy_readme}\n")
    
    # Check for GitHub Actions
    if GITHUB.exists():
        workflow_files = list(GITHUB.rglob("*.yml"))
        analysis.append(f"GitHub Actions workflows: {[f.name for f in workflow_files]}")
        
        for workflow in workflow_files:
            workflow_content = workflow.read_text(encoding='utf-8')
            analysis.append(f"Workflow {workflow.name}:\n{workflow_content[:500]}...\n")
    
    # Check for environment configuration
    env_file = ROOT / ".env"
    if env_file.exists():
        env_content = env_file.read_text(encoding='utf-8')
        # Mask sensitive information
        masked_env = env_content.replace("npg_wopeP92YbXft", "***MASKED***")
        analysis.append(f"Environment configuration:\n{masked_env}\n")
    
    # Check for Docker configuration
    dockerfile = ROOT / "Dockerfile"
    if dockerfile.exists():
        docker_content = dockerfile.read_text(encoding='utf-8')
        analysis.append(f"Dockerfile:\n{docker_content}\n")
    
    docker_compose = ROOT / "docker-compose.yml"
    if docker_compose.exists():
        compose_content = docker_compose.read_text(encoding='utf-8')
        analysis.append(f"docker-compose.yml:\n{compose_content}\n")
    
    # Check for Fly.io configuration
    fly_toml = ROOT / "fly.toml"
    if fly_toml.exists():
        fly_content = fly_toml.read_text(encoding='utf-8')
        analysis.append(f"fly.toml:\n{fly_content}\n")
    
    return "\n".join(analysis)

def _get_deployment_task() -> str:
    """Get the deployment task to perform."""
    # For automation, use a default comprehensive task
    # Can be overridden via environment variable DEPLOYER_TASK
    import os
    task = os.environ.get("DEPLOYER_TASK", "1")
    
    if task == "1":
        return "Review the current MusicLive deployment setup and provide recommendations for the Neon + Fly.io + R2 stack"
    elif task == "2":
        return "Create a comprehensive CI/CD pipeline for MusicLive using GitHub Actions with Neon branching and Fly.io deployment"
    elif task == "3":
        return "Set up Fly.io deployment configuration for containerized FastAPI app deployment"
    elif task == "4":
        return "Set up automated Neon database deployment with Flyway migrations and branching strategy"
    elif task == "5":
        return "Configure Cloudflare R2 object storage for raw artifacts with lifecycle policies"
    elif task == "6":
        return "Create Docker configuration for containerized deployment to Fly.io"
    elif task == "7":
        return "Set up monitoring, logging, and observability for the MusicLive system on Fly.io"
    elif task == "8":
        return "Create deployment scripts for staging and production environments"
    elif task == "9":
        custom_task = os.environ.get("DEPLOYER_CUSTOM", "Review the current MusicLive deployment setup and provide recommendations for the Neon + Fly.io + R2 stack")
        return custom_task
    else:
        return "Review the current MusicLive deployment setup and provide recommendations for the Neon + Fly.io + R2 stack"

def _check_system_requirements() -> str:
    """Check if the system meets deployment requirements."""
    checks = []
    
    # Check Python version
    python_version = sys.version_info
    checks.append(f"Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check for Poetry
    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✅ Poetry: Available")
        else:
            checks.append("❌ Poetry: Not available")
    except FileNotFoundError:
        checks.append("❌ Poetry: Not installed")
    
    # Check for Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✅ Docker: Available")
        else:
            checks.append("❌ Docker: Not available")
    except FileNotFoundError:
        checks.append("❌ Docker: Not installed")
    
    # Check for Fly CLI
    try:
        result = subprocess.run(["fly", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✅ Fly CLI: Available")
        else:
            checks.append("❌ Fly CLI: Not available")
    except FileNotFoundError:
        checks.append("❌ Fly CLI: Not installed")
    
    # Check for git
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✅ Git: Available")
        else:
            checks.append("❌ Git: Not available")
    except FileNotFoundError:
        checks.append("❌ Git: Not installed")
    
    # Check for GitHub CLI
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✅ GitHub CLI: Available")
        else:
            checks.append("❌ GitHub CLI: Not available")
    except FileNotFoundError:
        checks.append("❌ GitHub CLI: Not installed")
    
    return "\n".join(checks)

def _get_hosting_preferences() -> str:
    """Get hosting and deployment preferences."""
    # For automation, use default preferences
    # Can be overridden via environment variables
    import os
    
    preferences = []
    
    # Database preferences
    db_choice = os.environ.get("DEPLOYER_DB", "1")
    if db_choice == "1":
        preferences.append("Use existing Neon Postgres setup with branching strategy")
    elif db_choice == "2":
        preferences.append("Create new Neon Postgres project with dev/test/prod branches")
    else:
        custom_db = os.environ.get("DEPLOYER_DB_CUSTOM", "Use existing Neon Postgres setup with branching strategy")
        preferences.append(f"Custom database: {custom_db}")
    
    # App hosting preferences
    hosting_choice = os.environ.get("DEPLOYER_HOSTING", "1")
    if hosting_choice == "1":
        preferences.append("Deploy to Fly.io for lightweight, cost-effective hosting")
    elif hosting_choice == "2":
        preferences.append("Deploy to VPS for full control and customization")
    else:
        custom_hosting = os.environ.get("DEPLOYER_HOSTING_CUSTOM", "Deploy to Fly.io for lightweight, cost-effective hosting")
        preferences.append(f"Custom hosting: {custom_hosting}")
    
    # Storage preferences
    storage_choice = os.environ.get("DEPLOYER_STORAGE", "1")
    if storage_choice == "1":
        preferences.append("Use Cloudflare R2 for raw artifact storage with lifecycle policies")
    elif storage_choice == "2":
        preferences.append("Use AWS S3 for raw artifact storage")
    else:
        custom_storage = os.environ.get("DEPLOYER_STORAGE_CUSTOM", "Use Cloudflare R2 for raw artifact storage with lifecycle policies")
        preferences.append(f"Custom storage: {custom_storage}")
    
    # CI/CD preferences
    cicd_choice = os.environ.get("DEPLOYER_CICD", "1")
    if cicd_choice == "1":
        preferences.append("Use GitHub Actions for CI/CD with automated testing and deployment")
    elif cicd_choice == "2":
        preferences.append("Use GitLab CI/CD for automated testing and deployment")
    else:
        custom_cicd = os.environ.get("DEPLOYER_CICD_CUSTOM", "Use GitHub Actions for CI/CD with automated testing and deployment")
        preferences.append(f"Custom CI/CD: {custom_cicd}")
    
    return "\n".join(preferences)

def main():
    """Main deployer agent runner."""
    client, model = _anthropic_client()
    
    # Load project context
    prd_file = ROOT / "docs" / "PRD.md"
    prd = prd_file.read_text(encoding='utf-8') if prd_file.exists() else ""
    
    # Analyze current deployment
    current_deployment = _analyze_current_deployment()
    
    # Check system requirements
    system_requirements = _check_system_requirements()
    
    # Get hosting preferences
    hosting_preferences = _get_hosting_preferences()
    
    # Get deployment task
    deployment_task = _get_deployment_task()
    
    # Build prompt for deployer agent
    system_prompt = f"""You are the Deployer Agent for MusicLive. Your task is to: {deployment_task}

You MUST provide:
1. Deployment strategy and architecture for the specified stack
2. CI/CD pipeline configuration with GitHub Actions
3. Infrastructure requirements and setup instructions
4. Monitoring and logging configuration
5. Security considerations and best practices
6. Deployment scripts and automation
7. Next steps for implementation

Focus on the MusicLive stack:
- Database: Neon Postgres with Flyway migrations and branching
- App Hosting: Fly.io for FastAPI deployment (with VPS fallback)
- Storage: Cloudflare R2 for raw artifacts with lifecycle policies
- CI/CD: GitHub Actions for automated testing and deployment
- Geocoding: Geoapify API with local caching

Output your response in this exact format:
===DEPLOYMENT_STRATEGY===
[Overall deployment strategy and architecture for the Neon + Fly.io + R2 stack]

===CI_CD_PIPELINE===
[GitHub Actions CI/CD pipeline configuration and workflows]

===INFRASTRUCTURE_SETUP===
[Infrastructure requirements and setup instructions for Neon, Fly.io, and R2]

===MONITORING_LOGGING===
[Monitoring, logging, and observability configuration for Fly.io deployment]

===SECURITY_CONSIDERATIONS===
[Security best practices and considerations for the deployment stack]

===DEPLOYMENT_SCRIPTS===
[Deployment scripts and automation for staging/production]

===NEXT_STEPS===
[Actionable next steps for deployment implementation]
"""

    user_prompt = f"""Project Context:
PRD: {prd[:1000]}...

Current Deployment Analysis:
{current_deployment}

System Requirements:
{system_requirements}

Hosting Preferences:
{hosting_preferences}

Deployment Task: {deployment_task}

Please provide comprehensive deployment guidance for the MusicLive system using the Neon + Fly.io + R2 + GitHub Actions stack."""

    print(f"\n🚀 Deployment Task: {deployment_task}")
    print("🤖 Deployer Agent is working...")
    
    print(f"\n🔍 System prompt length: {len(system_prompt)}")
    print(f"🔍 User prompt length: {len(user_prompt)}")
    
    try:
        # Call the deployer agent
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.1,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        print(f"\n🔍 API call successful, response type: {type(response)}")
        print(f"🔍 Response content: {response.content}")
        print(f"🔍 Response usage: {getattr(response, 'usage', 'No usage info')}")
        
        # Extract response content
        content = response.content[0].text if response.content else "No response generated"
        
    except Exception as e:
        print(f"\n❌ API call failed: {e}")
        content = f"API call failed: {e}"
    
    print(f"\n🔍 Response content length: {len(content)}")
    print(f"🔍 Response preview: {content[:200]}...")
    
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
    
    print(f"\n🔍 Found {len(sections)} sections: {list(sections.keys())}")
    
    # Display results
    print("\n" + "="*60)
    print("🎉 DEPLOYER AGENT COMPLETED!")
    print("="*60)
    
    if sections:
        for section_name, section_content in sections.items():
            print(f"\n📋 {section_name.upper()}")
            print("-" * 40)
            print(section_content)
    else:
        print("\n⚠️ No sections found in response. Raw content:")
        print("-" * 40)
        print(content)
    
    # Save deployment plan to file
    if sections:
        output_file = ROOT / f"deployment_plan_{int(time.time())}.md"
        
        # Format as markdown
        markdown_content = []
        for section_name, section_content in sections.items():
            markdown_content.append(f"# {section_name.replace('_', ' ').title()}")
            markdown_content.append("")
            markdown_content.append(section_content)
            markdown_content.append("")
        
        output_file.write_text('\n'.join(markdown_content), encoding='utf-8')
        print(f"\n💾 Deployment plan saved to: {output_file}")
        
        # Also save to deploy directory
        deploy_dir = ROOT / "deploy"
        deploy_dir.mkdir(exist_ok=True)
        deploy_file = deploy_dir / "deployment_plan.md"
        deploy_file.write_text('\n'.join(markdown_content), encoding='utf-8')
        print(f"💾 Deployment plan also saved to: {deploy_file}")

if __name__ == "__main__":
    import time
    main()
