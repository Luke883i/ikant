from ikant.engine_exit_diagnostics import (
    MAX_STDERR_TAIL_BYTES,
    EngineExitDiagnostic,
    bounded_stderr_tail,
)


def test_exit_status_is_observed_without_semantic_guessing():
    diagnostic = EngineExitDiagnostic.capture(127, b"loader failed")
    assert diagnostic.kind == "EXIT_STATUS"
    assert diagnostic.returncode == 127
    assert diagnostic.signal is None
    assert diagnostic.stderr_tail == "loader failed"


def test_signal_is_derived_only_from_negative_returncode():
    diagnostic = EngineExitDiagnostic.capture(-9, b"killed")
    assert diagnostic.kind == "SIGNAL"
    assert diagnostic.returncode == -9
    assert diagnostic.signal == 9


def test_unknown_does_not_invent_process_state():
    diagnostic = EngineExitDiagnostic.capture(None, b"")
    assert diagnostic.kind == "UNKNOWN"
    assert diagnostic.returncode is None
    assert diagnostic.signal is None


def test_stderr_tail_is_redacted_and_byte_bounded_even_for_invalid_utf8():
    raw = (b"X" * 8192) + b" token=abc123 " + (bytes([0xFF, 0xFE, 0x80]) * 2000)
    value = bounded_stderr_tail(raw)
    assert len(value.encode("utf-8")) <= MAX_STDERR_TAIL_BYTES
    assert "abc123" not in value
