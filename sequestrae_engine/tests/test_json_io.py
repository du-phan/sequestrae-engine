import json

import pytest

from sequestrae_engine.core.utilities import read_json, write_json


def test_read_json_valid(tmp_path):
    valid_json_str = '{"key": "value"}'
    file_path = tmp_path / "valid.json"
    file_path.write_text(valid_json_str)

    data = read_json(file_path)
    assert data == {"key": "value"}


def test_read_json_invalid(tmp_path):
    invalid_json_str = '{"key": "value"'
    file_path = tmp_path / "invalid.json"
    file_path.write_text(invalid_json_str)

    with pytest.raises(json.JSONDecodeError) as exc_info:
        read_json(file_path)

    assert "Expecting" in str(exc_info.value)  # Common error message for unclosed JSON objects


def test_write_json(tmp_path):
    data = {"key": "value"}
    file_path = tmp_path / "output.json"

    write_json(file_path, data)
    written_data = json.loads(file_path.read_text())
    assert written_data == data


def test_write_json_invalid(tmp_path):
    invalid_data = {"key": set([1, 2, 3])}  # Sets are not JSON serializable
    file_path = tmp_path / "invalid_output.json"

    with pytest.raises(TypeError) as exc_info:
        write_json(file_path, invalid_data)

    assert "is not JSON serializable" in str(exc_info.value)
