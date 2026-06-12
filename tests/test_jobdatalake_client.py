"""Tests for the JobDataLake API call (tools/jobdatalake_client.py)."""

from unittest.mock import MagicMock, patch

import requests

from tools.jobdatalake_client import get_jobs


@patch.dict("os.environ", {"JOBDATALAKE_API_KEY": "test-key"})
@patch("tools.jobdatalake_client.requests.get")
def test_get_jobs_success(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"jobs": [{"title": "Python Developer"}]}
    mock_get.return_value = mock_response

    result = get_jobs({"q": "python developer", "per_page": 3})

    assert result == {"jobs": [{"title": "Python Developer"}], "error": None}

    mock_get.assert_called_once()
    _, kwargs = mock_get.call_args
    assert kwargs["headers"] == {"X-API-Key": "test-key"}
    assert kwargs["params"] == {"q": "python developer", "per_page": 3}


@patch.dict("os.environ", {}, clear=True)
def test_get_jobs_missing_api_key():
    result = get_jobs({"q": "python developer"})

    assert result["jobs"] == []
    assert "JOBDATALAKE_API_KEY" in result["error"]


@patch.dict("os.environ", {"JOBDATALAKE_API_KEY": "test-key"})
@patch("tools.jobdatalake_client.requests.get")
def test_get_jobs_request_error(mock_get):
    mock_get.side_effect = requests.RequestException("connection failed")

    result = get_jobs({"q": "python developer"})

    assert result["jobs"] == []
    assert "connection failed" in result["error"]


@patch.dict("os.environ", {"JOBDATALAKE_API_KEY": "test-key"})
@patch("tools.jobdatalake_client.requests.get")
def test_get_jobs_unexpected_shape_falls_back_to_empty_list(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"something_else": "no jobs key"}
    mock_get.return_value = mock_response

    result = get_jobs({"q": "python developer"})

    assert result == {"jobs": [], "error": None}
