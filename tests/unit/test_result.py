"""Testes do Result Pattern."""
from src.domain.result import ok, fail, Ok, Fail


class TestResult:
    def test_ok_result(self):
        result = ok("hello")
        assert result.ok is True
        assert result.value == "hello"

    def test_fail_result(self):
        result = fail("something went wrong")
        assert result.ok is False
        assert result.error == "something went wrong"

    def test_ok_is_instance(self):
        result = ok(42)
        assert isinstance(result, Ok)

    def test_fail_is_instance(self):
        result = fail("error")
        assert isinstance(result, Fail)
