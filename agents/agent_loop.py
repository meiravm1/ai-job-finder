"""Shared tool-use loop for the Search and Matching agents."""

import json

from anthropic import Anthropic

MODEL = "claude-haiku-4-5"
MAX_ITERATIONS = 6


def run_agent(system_prompt: str, tool_schemas: list[dict], tool_functions: dict, user_message: str) -> dict:
    """Run a manual tool-use loop and return the agent's final answer as a dict.

    tool_functions maps tool name -> Python callable(**kwargs) -> JSON-serializable result.
    If the final response can't be parsed as JSON, returns {"jobs": [], "errors": [...]}.
    """
    client = Anthropic()
    messages = [{"role": "user", "content": user_message}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return _parse_final_response(response)

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            func = tool_functions.get(block.name)
            if func is None:
                result = {"error": f"Unknown tool: {block.name}"}
            else:
                result = func(**block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
            })

        messages.append({"role": "user", "content": tool_results})

    return {"jobs": [], "ranked_jobs": [], "errors": ["Agent exceeded max iterations without a final answer"]}


def _parse_final_response(response) -> dict:
    text_parts = [block.text for block in response.content if block.type == "text"]
    text = "\n".join(text_parts).strip()

    text = _strip_code_fence(text)

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {"jobs": [], "ranked_jobs": [], "errors": [f"Could not parse agent response as JSON: {text[:200]}"]}


def _strip_code_fence(text: str) -> str:
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return text
