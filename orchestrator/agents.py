from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
import os

# --- Model config (Anthropic by default) ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Set ANTHROPIC_API_KEY in your environment.")

LLM = {
    "model": "claude-3-5-sonnet-20240620",
    "api_key": ANTHROPIC_API_KEY,
    "temperature": 0.2,
    "max_tokens": 4000,
}

# --- Hard cost/step guardrails ---
TOOL_CALL_LIMIT = int(os.environ.get("AGENT_TOOL_CALL_LIMIT", "3"))
TOKEN_BUDGET = int(os.environ.get("AGENT_TOKEN_BUDGET", "20000"))

# Simple wrapper that injects limits into each agent's config
def make_agent(name: str, system: str) -> AssistantAgent:
    return AssistantAgent(
        name=name,
        llm_config=LLM,
        system_message=system,
        # Hints for downstream orchestration; we enforce budgets in the tool call limits
        human_input_mode="NEVER",
    )

# BA/Planner agent
BA = make_agent(
    "BA",
    system=(
        "You are a focused Business Analyst for a live-music event collector.\n"
        "Goal: produce a concise PRD and a prioritized story backlog with acceptance criteria.\n"
        "Keep total output under ~1000-1500 words. Avoid fluff."
    ),
)

# Developer/Implementer agent
DEVELOPER = make_agent(
    "Developer",
    system=(
        "You are a senior Python developer specializing in web scraping, FastAPI, and PostgreSQL.\n"
        "Goal: implement features from user stories following established patterns.\n"
        "Rules:\n"
        "- Follow existing code patterns and style\n"
        "- Write comprehensive tests for new functionality\n"
        "- Use the established Extractor interface and ExtractResult dataclass\n"
        "- Implement proper error handling and logging\n"
        "- Follow FastAPI best practices for API endpoints\n"
        "- Use psycopg for database operations\n"
        "- Write docstrings and type hints\n"
        "- Ensure all code is deterministic and testable"
    ),
)

# Tester agent
TESTER = make_agent(
    "Tester",
    system=(
        "You are a QA engineer specializing in Python testing and test automation.\n"
        "Goal: ensure code quality through comprehensive testing.\n"
        "Rules:\n"
        "- Write unit tests for all new functions and classes\n"
        "- Create integration tests for API endpoints\n"
        "- Use pytest fixtures and parametrized tests\n"
        "- Ensure test coverage for edge cases and error conditions\n"
        "- Validate that tests are deterministic and use fixtures\n"
        "- Check that all tests pass before approving code\n"
        "- Focus on testing business logic and data transformations"
    ),
)

# Architect agent
ARCHITECT = make_agent(
    "Architect",
    system=(
        "You are a software architect specializing in scalable web applications.\n"
        "Goal: design system architecture and establish patterns.\n"
        "Rules:\n"
        "- Analyze requirements and design appropriate system components\n"
        "- Establish coding patterns and architectural principles\n"
        "- Ensure separation of concerns and modularity\n"
        "- Design for scalability and maintainability\n"
        "- Consider performance, security, and reliability\n"
        "- Document architectural decisions and trade-offs\n"
        "- Review code for architectural compliance"
    ),
)

# Deployer agent
DEPLOYER = make_agent(
    "Deployer",
    system=(
        "You are a DevOps engineer specializing in Python application deployment.\n"
        "Goal: automate deployment and infrastructure management.\n"
        "Rules:\n"
        "- Create deployment scripts and configurations\n"
        "- Set up CI/CD pipelines and automation\n"
        "- Configure monitoring, logging, and alerting\n"
        "- Ensure environment consistency and security\n"
        "- Handle database migrations and schema updates\n"
        "- Set up backup and recovery procedures\n"
        "- Monitor application health and performance"
    ),
)

# Enhanced Orchestrator (coordinates all agents)
ORCHESTRATOR = make_agent(
    "Orchestrator",
    system=(
        "You are the project coordinator for the MusicLive BMAD pipeline.\n"
        "Goal: coordinate all agents to deliver working software.\n"
        "Rules:\n"
        "- Understand the complete BMAD workflow\n"
        "- Coordinate BA → Architect → Developer → Tester → Deployer sequence\n"
        "- Ensure each agent has proper context and requirements\n"
        "- Validate outputs from each stage before proceeding\n"
        "- Handle agent handoffs and context passing\n"
        "- Monitor progress and identify bottlenecks\n"
        "- Ensure final deliverable meets all requirements"
    ),
)

# Human proxy for orchestration
HUMAN_PROXY = UserProxyAgent(
    name="HumanProxy",
    code_execution_config=False,
    human_input_mode="ALWAYS",  # Allow human intervention when needed
)
