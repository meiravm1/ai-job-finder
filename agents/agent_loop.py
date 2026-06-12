"""Shared tool-use loop for the Search and Matching agents.

Supports multiple LLM providers (Gemini, Groq) behind one interface. Tool
schemas are defined once, in OpenAI-style function-calling format, and
converted as needed for the selected provider.
"""

import json

MAX_ITERATIONS = 6
MAX_TOKENS = 4096

PROVIDER_MODELS = {
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
}


def run_agent(
    system_prompt: str,
    tool_schemas: list[dict],
    tool_functions: dict,
    user_message: str,
    provider: str = "gemini",
) -> dict:
    """Run a manual tool-use loop and return the agent's final answer as a dict.

    tool_schemas is a list of OpenAI-style function-calling tool definitions:
    {"type": "function", "function": {"name", "description", "parameters"}}.

    tool_functions maps tool name -> Python callable(**kwargs) -> JSON-serializable result.
    If the final response can't be parsed as JSON, returns {"jobs": [], "ranked_jobs": [], "errors": [...]}.
    """
    if provider not in PROVIDER_MODELS:
        raise ValueError(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDER_MODELS)}")

    model = PROVIDER_MODELS[provider]

    if provider == "gemini":
        return _run_gemini(system_prompt, tool_schemas, tool_functions, user_message, model)

    return _run_openai_compatible(system_prompt, tool_schemas, tool_functions, user_message, model, provider)


# --- Gemini ---------------------------------------------------------------

def _run_gemini(system_prompt, tool_schemas, tool_functions, user_message, model) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client()
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        tools=[types.Tool(function_declarations=_to_gemini_function_declarations(tool_schemas))],
        max_output_tokens=MAX_TOKENS,
    )

    contents = [types.Content(role="user", parts=[types.Part(text=user_message)])]

    for _ in range(MAX_ITERATIONS):
        response = client.models.generate_content(model=model, contents=contents, config=config)

        candidate = response.candidates[0]
        function_calls = [part.function_call for part in candidate.content.parts if part.function_call]

        if not function_calls:
            return _parse_final_text(response.text or "")

        contents.append(candidate.content)

        function_response_parts = []
        for call in function_calls:
            result = _call_tool(tool_functions, call.name, dict(call.args))
            function_response_parts.append(
                types.Part.from_function_response(name=call.name, response=result)
            )

        contents.append(types.Content(role="user", parts=function_response_parts))

    return _max_iterations_error()


def _to_gemini_function_declarations(tool_schemas: list[dict]) -> list[dict]:
    declarations = []
    for tool in tool_schemas:
        fn = tool["function"]
        declarations.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "parameters": _uppercase_schema_types(fn.get("parameters", {"type": "object", "properties": {}})),
        })
    return declarations


def _uppercase_schema_types(schema: dict) -> dict:
    converted = {}
    for key, value in schema.items():
        if key == "type" and isinstance(value, str):
            converted[key] = value.upper()
        elif key == "properties" and isinstance(value, dict):
            converted[key] = {name: _uppercase_schema_types(prop) for name, prop in value.items()}
        elif key == "items" and isinstance(value, dict):
            converted[key] = _uppercase_schema_types(value)
        else:
            converted[key] = value
    return converted


# --- OpenAI-compatible (Groq) ----------------------------------------------

def _run_openai_compatible(system_prompt, tool_schemas, tool_functions, user_message, model, provider) -> dict:
    client = _make_openai_compatible_client(provider)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_schemas,
            max_tokens=MAX_TOKENS,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            return _parse_final_text(message.content or "")

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.function.name, "arguments": call.function.arguments},
                }
                for call in message.tool_calls
            ],
        })

        for call in message.tool_calls:
            args = json.loads(call.function.arguments or "{}")
            result = _call_tool(tool_functions, call.function.name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

    return _max_iterations_error()


def _make_openai_compatible_client(provider: str):
    if provider == "groq":
        from groq import Groq
        return Groq()

    raise ValueError(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDER_MODELS)}")


# --- shared helpers ----------------------------------------------------------

def _call_tool(tool_functions: dict, name: str, args: dict) -> dict:
    func = tool_functions.get(name)
    if func is None:
        return {"error": f"Unknown tool: {name}"}
    return func(**args)


def _parse_final_text(text: str) -> dict:
    text = _strip_code_fence(text.strip())

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


def _max_iterations_error() -> dict:
    return {"jobs": [], "ranked_jobs": [], "errors": ["Agent exceeded max iterations without a final answer"]}
