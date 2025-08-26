import os, pathlib
from anthropic import Anthropic


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DOCS.mkdir(exist_ok=True, parents=True)

QUESTIONS_PROMPT = """You are the BA for the MusicLive collector.
Given the project context supplied earlier, produce up to 8 clarifying questions you need answered BEFORE writing the PRD and Stories.

Rules:
- Be specific and implementation-focused.
- Focus on scope, data fields, sources, geography limits, rate limits, admin needs, success metrics, and legal/politeness constraints.
- Output ONLY a numbered list of questions, nothing else."""

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-3-7-sonnet-latest",
        max_tokens=800,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": QUESTIONS_PROMPT}
                ],
            }
        ],
    )


    # Extract text
    content_blocks = resp.content or []
    text = "\n".join(
        block.text for block in content_blocks if getattr(block, "type", "") == "text"
    ).strip()

    # Save & print
    (DOCS / "BA_Questions.md").write_text(text + "\n", encoding="utf-8")
    print("\n=== Clarifying Questions ===\n")
    print(text)

if __name__ == "__main__":
    main()

