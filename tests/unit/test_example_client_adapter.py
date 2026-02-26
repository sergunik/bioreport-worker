"""Tests for ExampleClientAdapter (template/reference adapter)."""

import json

from app.normalization.example_client_adapter import ExampleClientAdapter


class TestExampleClientAdapter:
    def test_implements_base_contract(self) -> None:
        adapter = ExampleClientAdapter()
        result = adapter.create_chat_completion(
            model="any",
            temperature=0.0,
            system_prompt="sys",
            user_prompt="user",
            json_schema={"type": "object"},
        )
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "person" in parsed
        assert "diagnostic_date" in parsed
        assert "markers" in parsed

    def test_returns_valid_normalization_structure(self) -> None:
        adapter = ExampleClientAdapter()
        result = adapter.create_chat_completion(
            model="x",
            temperature=0.1,
            system_prompt="",
            user_prompt="",
            json_schema={},
        )
        data = json.loads(result)
        assert data["person"]["name"] == "PERSON_1"
        assert data["person"]["dob"] is None
        assert data["diagnostic_date"] is None
        assert data["markers"] == []

    def test_ignores_input_parameters(self) -> None:
        adapter = ExampleClientAdapter()
        r1 = adapter.create_chat_completion(
            model="a",
            temperature=0.0,
            system_prompt="s1",
            user_prompt="u1",
            json_schema={"k": "v"},
        )
        r2 = adapter.create_chat_completion(
            model="b",
            temperature=1.0,
            system_prompt="s2",
            user_prompt="u2",
            json_schema={},
        )
        assert r1 == r2
