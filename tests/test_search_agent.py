"""Tests for the Search Agent's Gemini tool-use loop (agents/search_agent.py)."""

import json
from types import SimpleNamespace
from unittest.mock import patch

from agents.search_agent import run_search_agent

FAKE_JOBS_RESULT = {
    "jobs": [
        {
            "title": "Junior Python Developer",
            "company": "Acme",
            "location": "Tel Aviv",
            "remote_type": "remote",
            "seniority": "junior",
            "salary": None,
            "skills": ["python", "sql"],
            "employment_type": None,
            "url": "https://example.com/job/1",
        }
    ],
    "error": None,
}


def _tool_call_response(name: str, args: dict):
    """Build a fake Gemini response that requests a tool call."""
    part = SimpleNamespace(function_call=SimpleNamespace(name=name, args=args), text=None)
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[part]))
    return SimpleNamespace(candidates=[candidate], text=None)


def _final_response(payload: dict):
    """Build a fake Gemini response with a final text answer and no tool calls."""
    candidate = SimpleNamespace(content=SimpleNamespace(parts=[]))
    return SimpleNamespace(candidates=[candidate], text=json.dumps(payload))


@patch("tools.search_tools.get_jobs", return_value=FAKE_JOBS_RESULT)
@patch("google.genai.Client")
def test_run_search_agent_calls_jobdatalake_tool_via_gemini(mock_client_cls, mock_get_jobs):
    final_payload = {
        "search_terms_used": {"query": "python developer", "location": "Tel Aviv"},
        "jobs": FAKE_JOBS_RESULT["jobs"],
        "errors": [],
    }

    mock_client = mock_client_cls.return_value
    mock_client.models.generate_content.side_effect = [
        _tool_call_response("search_jobs", {"query": "python developer", "location": "Tel Aviv"}),
        _final_response(final_payload),
    ]

    result = run_search_agent("junior python developer in Tel Aviv")

    # Final JSON returned by the agent matches the Gemini response.
    assert result == final_payload

    # Gemini was called twice: once to request the tool, once for the final answer.
    assert mock_client.models.generate_content.call_count == 2

    # The JobDataLake-backed tool was actually invoked with the model's arguments.
    mock_get_jobs.assert_called_once()


@patch("google.genai.Client")
def test_run_search_agent_handles_unparseable_final_response(mock_client_cls):
    not_json_response = SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=[]))], text="not json")

    mock_client = mock_client_cls.return_value
    # The agent retries on unparseable JSON up to MAX_JSON_RETRIES times.
    mock_client.models.generate_content.side_effect = [not_json_response] * 3

    result = run_search_agent("junior python developer in Tel Aviv")

    assert result["jobs"] == []
    assert result["errors"]
    assert "not json" in result["errors"][0]
