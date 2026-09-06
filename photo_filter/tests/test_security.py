from photo_filter.services.security import (
    detect_blacklisted_processes,
    is_debugger_present,
    verify_security_environment,
)


def test_security_environment_runs_cleanly() -> None:
    # Under standard automated test run, no blacklisted debuggers should be attached
    assert isinstance(is_debugger_present(), bool)
    assert isinstance(detect_blacklisted_processes(), list)
    assert verify_security_environment() is True
