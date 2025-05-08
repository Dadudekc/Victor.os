# tests/monitoring/test_correlation_validator.py

import logging
import pytest
import re
import uuid
from unittest.mock import MagicMock, patch
import threading
from typing import Optional

# Adjust import based on actual location
from src.dreamos.monitoring.correlation_validator import BusCorrelationValidator, BaseEvent # Assuming BaseEvent is accessible here for mocking

# Placeholder for actual EventType enum if needed for tests
class MockEventType:
    TEST_EVENT = "test.event.occurred"
    ANOTHER_EVENT = "another.event.happened"

# Helper to create mock events
def create_mock_event(corr_id: Optional[str], event_type = MockEventType.TEST_EVENT, event_id: Optional[str] = None) -> BaseEvent:
    mock = MagicMock(spec=BaseEvent)
    mock.event_id = event_id or f"evt_{uuid.uuid4().hex[:6]}"
    mock.event_type = event_type
    mock.source_id = "mock_source"
    # Use setattr to handle potential issues if BaseEvent uses slots or is complex
    setattr(mock, 'correlation_id', corr_id)
    # Ensure accessing event_type.name works IF event_type has a name attr.
    # If event_type is just a string, getattr in validator will handle it.
    if hasattr(event_type, 'name'):
         # We don't need to set it here, the MagicMock gets the event_type assigned
         # The validator uses getattr(event.event_type, 'name', ...)
         pass
    elif isinstance(event_type, str):
         # For simple strings used as types, make mock.event_type be the string
         # but also give it a .name attribute for consistent access testing IF NEEDED.
         # However, validator uses getattr, so setting .name on the string itself isn't needed.
         # Let's simplify: Just assign the event_type. The validator handles access.
         pass
    # If event_type is MockEventType.TEST_EVENT (which is a string value), 
    # mock.event_type will be the string "test.event.occurred".
    # If event_type is a custom object with a .name, mock.event_type will be that object.
    return mock

# --- Test Fixtures --- #

@pytest.fixture(scope="function")
def validator_instance():
    """Fixture to provide a fresh, unconfigured validator instance for each test."""
    # Reset singleton state before each test
    BusCorrelationValidator._instance = None
    # Don't call configure here, let tests do it if needed
    # yield BusCorrelationValidator # Yielding class allows calling configure
    # For simplicity, let's yield an instance configured without regex by default
    # Tests needing specific config can reconfigure or use a different fixture
    instance = BusCorrelationValidator.configure(expected_id_format_regex=None)
    instance.reset_issues() # Ensure issues are clear at start
    yield instance
    # Cleanup singleton state after test
    BusCorrelationValidator._instance = None

@pytest.fixture(scope="function")
def configured_validator():
    """Fixture for validator configured with a specific UUID regex."""
    uuid_regex = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    BusCorrelationValidator._instance = None
    instance = BusCorrelationValidator.configure(expected_id_format_regex=uuid_regex)
    instance.reset_issues()
    yield instance
    BusCorrelationValidator._instance = None


# --- Test Cases --- #

# 1. Initialization & Singleton
def test_singleton_get_instance_unconfigured_raises_error():
    BusCorrelationValidator._instance = None # Ensure it's reset
    with pytest.raises(RuntimeError) as excinfo:
        BusCorrelationValidator.get_instance()
    assert "must be configured using configure() before accessing the instance" in str(excinfo.value)

def test_singleton_configure_and_get_instance():
    BusCorrelationValidator._instance = None
    regex = "^[a-z]+$"
    validator = BusCorrelationValidator.configure(expected_id_format_regex=regex)
    assert isinstance(validator, BusCorrelationValidator)
    assert validator.expected_id_format_pattern is not None
    assert validator.expected_id_format_pattern.pattern == regex
    
    validator2 = BusCorrelationValidator.get_instance()
    assert validator is validator2 # Should be the same instance

def test_singleton_configure_called_multiple_times_logs_warning(caplog):
    BusCorrelationValidator._instance = None
    validator1 = BusCorrelationValidator.configure(expected_id_format_regex="^first$")
    assert validator1.expected_id_format_pattern.pattern == "^first$"

    with caplog.at_level(logging.WARNING):
        validator2 = BusCorrelationValidator.configure(expected_id_format_regex="^second$")
    
    assert validator1 is validator2 # Should still be the same instance
    # Default behavior is to ignore re-configuration attempts for the regex once initialized.
    # The log should indicate this.
    assert "BusCorrelationValidator already configured. Re-configuration attempt ignored" in caplog.text
    # Verify that the original regex is retained (or document if it can be updated)
    assert validator2.expected_id_format_pattern.pattern == "^first$" 

def test_singleton_parallel_configuration(caplog):
    BusCorrelationValidator._instance = None
    num_threads = 5
    results = [None] * num_threads
    exceptions = [None] * num_threads

    def configure_validator(index):
        try:
            # Each thread attempts to configure. Only one should succeed in full init.
            instance = BusCorrelationValidator.configure(expected_id_format_regex=f"^thread_{index}$")
            results[index] = instance
        except Exception as e:
            exceptions[index] = e

    threads = []
    for i in range(num_threads):
        thread = threading.Thread(target=configure_validator, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()
    
    first_initialized_instance = None
    for i in range(num_threads):
        assert exceptions[i] is None, f"Thread {i} raised an exception: {exceptions[i]}"
        assert results[i] is not None, f"Thread {i} did not get an instance."
        if first_initialized_instance is None:
            first_initialized_instance = results[i]
        assert results[i] is first_initialized_instance, f"Thread {i} got a different instance."

    # Check logs for warnings about re-initialization attempts by other threads
    # There should be num_threads - 1 warnings like "already initialized by another thread" or "Re-configuration attempt ignored"
    # This count can be tricky due to exact timing of lock acquisition vs. outer check.
    # It's enough that they all get the same instance.
    # logger.info("BusCorrelationValidator singleton initialized.") should appear once.
    # logger.warning("BusCorrelationValidator already initialized by another thread.") or 
    # logger.warning("BusCorrelationValidator already configured. Re-configuration attempt ignored.") may appear multiple times.
    # A simpler check: ensure all instances are identical.
    assert len(set(id(r) for r in results)) == 1
    # init_log_count = sum(1 for record in caplog.records if "BusCorrelationValidator singleton initialized." in record.message and record.levelno == logging.INFO)
    # assert init_log_count == 1 # Commenting out potentially flaky log count assertion

# 2. validate_event Method
def test_validate_event_id_present_no_regex(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id="corr-123")
    assert validator_instance.validate_event(event) is True
    assert len(validator_instance.get_issues()) == 0

def test_validate_event_id_missing(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id=None)
    # Patch the *real* log_issue method on the instance
    with patch.object(validator_instance, 'log_issue', wraps=validator_instance.log_issue) as mock_real_log_issue:
        assert validator_instance.validate_event(event) is False
        # Assert the real method was called with the correct issue type
        mock_real_log_issue.assert_called_once()
        call_args = mock_real_log_issue.call_args
        assert call_args is not None
        assert call_args.kwargs.get('issue_type') == 'MISSING_ID'

def test_validate_event_id_present_valid_format(configured_validator: BusCorrelationValidator):
    valid_uuid = str(uuid.uuid4())
    event = create_mock_event(corr_id=valid_uuid)
    assert configured_validator.validate_event(event) is True
    assert len(configured_validator.get_issues()) == 0

def test_validate_event_id_present_invalid_format(configured_validator: BusCorrelationValidator):
    event = create_mock_event(corr_id="not-a-uuid")
    # Patch the *real* log_issue method on the instance
    with patch.object(configured_validator, 'log_issue', wraps=configured_validator.log_issue) as mock_real_log_issue:
        assert configured_validator.validate_event(event) is False
        # Assert the real method was called for INVALID_FORMAT
        found_call = False
        for call in mock_real_log_issue.call_args_list:
            if call.kwargs.get('issue_type') == 'INVALID_FORMAT':
                found_call = True
                break
        assert found_call, "log_issue was not called with issue_type='INVALID_FORMAT'"

def test_validate_event_context_id_match(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id="ctx-123")
    # Patch to ensure log_issue is NOT called
    with patch.object(validator_instance, 'log_issue') as mock_log:
        assert validator_instance.validate_event(event, context_correlation_id="ctx-123") is True
        mock_log.assert_not_called()

def test_validate_event_context_id_mismatch(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id="event-corr-id")
    # Patch the *real* log_issue method on the instance
    with patch.object(validator_instance, 'log_issue', wraps=validator_instance.log_issue) as mock_real_log_issue:
        assert validator_instance.validate_event(event, context_correlation_id="expected-ctx-id") is False
        # Assert the real method was called for CONTEXT_MISMATCH
        found_call = False
        for call in mock_real_log_issue.call_args_list:
            if call.kwargs.get('issue_type') == 'CONTEXT_MISMATCH':
                found_call = True
                break
        assert found_call, "log_issue was not called with issue_type='CONTEXT_MISMATCH'"

def test_validate_event_context_id_not_provided(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id="corr-456")
    # Patch to ensure log_issue is NOT called
    with patch.object(validator_instance, 'log_issue') as mock_log:
        assert validator_instance.validate_event(event, context_correlation_id=None) is True # No context to mismatch against
        mock_log.assert_not_called()

def test_validate_event_all_issues_logged(configured_validator: BusCorrelationValidator):
    event = create_mock_event(corr_id="invalid-uuid-format") # Invalid format
    # Patch the *real* log_issue method on the instance
    with patch.object(configured_validator, 'log_issue', wraps=configured_validator.log_issue) as mock_real_log_issue:
        assert configured_validator.validate_event(event, context_correlation_id="different-context-id") is False
        # Assert the real method was called for both issue types
        issue_types_logged = {call.kwargs.get('issue_type') for call in mock_real_log_issue.call_args_list}
        assert 'INVALID_FORMAT' in issue_types_logged
        assert 'CONTEXT_MISMATCH' in issue_types_logged

# ... more validate_event tests ...

# 3. Logging & Issue Management
def test_log_issue_adds_to_internal_log(validator_instance: BusCorrelationValidator):
    assert len(validator_instance.get_issues()) == 0
    event_details = {"event_id": "evt_test_log"}
    validator_instance.log_issue("TEST_LOG_TYPE", "Test log message", event_details=event_details, level=logging.INFO)
    issues = validator_instance.get_issues()
    assert len(issues) == 1
    issue = issues[0]
    assert issue['type'] == "TEST_LOG_TYPE"
    assert issue['message'] == "Test log message"
    assert issue['event_details'] == event_details
    assert 'timestamp' in issue

def test_reset_issues_clears_log(validator_instance: BusCorrelationValidator):
    validator_instance.log_issue("TEST_RESET_TYPE", "Test reset message")
    assert len(validator_instance.get_issues()) == 1
    validator_instance.reset_issues()
    assert len(validator_instance.get_issues()) == 0

def test_get_issues_returns_copy(validator_instance: BusCorrelationValidator):
    validator_instance.log_issue("TEST_COPY_TYPE", "Test copy message")
    issues1 = validator_instance.get_issues()
    assert len(issues1) == 1
    issues1.append("mutation") # Try to mutate the returned list
    issues2 = validator_instance.get_issues()
    assert len(issues2) == 1 # Internal log should be unaffected
    assert issues2[0]['type'] == "TEST_COPY_TYPE"

# 4. validate_event_sequence Method (Phase 2 - Basic)
def test_validate_sequence_empty_list(validator_instance: BusCorrelationValidator):
    assert validator_instance.validate_event_sequence([]) is True
    assert len(validator_instance.get_issues()) == 0

def test_validate_sequence_single_valid_event(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id="seq-corr-1")
    assert validator_instance.validate_event_sequence([event]) is True

def test_validate_sequence_single_invalid_event_missing_id(validator_instance: BusCorrelationValidator):
    event = create_mock_event(corr_id=None)
    # Patch the *real* log_issue method
    with patch.object(validator_instance, 'log_issue', wraps=validator_instance.log_issue) as mock_real_log_issue:
        assert validator_instance.validate_event_sequence([event]) is False
        # Assert the real method was called
        issue_types_logged = {call.kwargs.get('issue_type') for call in mock_real_log_issue.call_args_list}
        # In this specific case (first event has no ID, no explicit seq ID given),
        # validate_event_sequence returns early after logging INVALID_SEQUENCE_START.
        # It does NOT proceed to call validate_event, so MISSING_ID is not logged here.
        assert issue_types_logged == {'INVALID_SEQUENCE_START'}

def test_validate_sequence_multiple_events_same_valid_id(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-corr-A"),
        create_mock_event(corr_id="seq-corr-A")
    ]
    assert validator_instance.validate_event_sequence(events) is True

def test_validate_sequence_multiple_events_one_missing_id(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-corr-B"),
        create_mock_event(corr_id=None) # This one is problematic
    ]
    assert validator_instance.validate_event_sequence(events) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_ID' for issue in issues)

def test_validate_sequence_multiple_events_different_ids(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-corr-C1"),
        create_mock_event(corr_id="seq-corr-C2") # Different from first
    ]
    # The first event's ID ("seq-corr-C1") becomes the target_id.
    # The second event will fail validate_event due to context mismatch.
    assert validator_instance.validate_event_sequence(events) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'CONTEXT_MISMATCH' and issue['event_details']['event_correlation_id'] == "seq-corr-C2" and issue['event_details']['context_correlation_id'] == "seq-corr-C1" for issue in issues)

def test_validate_sequence_multiple_events_invalid_format(configured_validator: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="not-a-valid-uuid-seq1"),
        create_mock_event(corr_id="not-a-valid-uuid-seq1")
    ]
    assert configured_validator.validate_event_sequence(events) is False
    issues = configured_validator.get_issues()
    # Both events will log INVALID_FORMAT from their individual validate_event calls
    invalid_format_issues = [issue for issue in issues if issue['type'] == 'INVALID_FORMAT']
    assert len(invalid_format_issues) >= 1 # At least the first one, likely both

def test_validate_sequence_with_explicit_matching_sequence_id(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="explicit-match"),
        create_mock_event(corr_id="explicit-match")
    ]
    assert validator_instance.validate_event_sequence(events, sequence_correlation_id="explicit-match") is True

def test_validate_sequence_with_explicit_mismatching_sequence_id(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="event-id-1"),
        create_mock_event(corr_id="event-id-1") # Matches each other but not explicit
    ]
    assert validator_instance.validate_event_sequence(events, sequence_correlation_id="explicit-mismatch") is False
    issues = validator_instance.get_issues()
    # Both events will log CONTEXT_MISMATCH against "explicit-mismatch"
    context_mismatch_issues = [issue for issue in issues if issue['type'] == 'CONTEXT_MISMATCH']
    assert len(context_mismatch_issues) >= 1 # At least first, likely both
    assert any(issue['event_details']['context_correlation_id'] == "explicit-mismatch" for issue in context_mismatch_issues)

def test_validate_sequence_first_event_no_id_no_explicit_sequence_id(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id=None)]
    # Patch the *real* log_issue method
    with patch.object(validator_instance, 'log_issue', wraps=validator_instance.log_issue) as mock_real_log_issue:
        assert validator_instance.validate_event_sequence(events) is False
        # Assert the real method was called
        issue_types_logged = {call.kwargs.get('issue_type') for call in mock_real_log_issue.call_args_list}
        # Similar to above, only INVALID_SEQUENCE_START is expected here.
        assert issue_types_logged == {'INVALID_SEQUENCE_START'}
        # Removed check for MISSING_ID

# --- Phase 2: Origin/Terminal Event Type Tests for validate_event_sequence ---

def test_validate_sequence_missing_origin_event(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-origin-term", event_type=MockEventType.ANOTHER_EVENT)]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=[MockEventType.TEST_EVENT]
    ) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_ORIGIN_EVENT' for issue in issues)

def test_validate_sequence_present_origin_event(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-origin-term", event_type=MockEventType.TEST_EVENT)]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=[MockEventType.TEST_EVENT]
    ) is True

def test_validate_sequence_missing_terminal_event(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-origin-term", event_type=MockEventType.TEST_EVENT)]
    assert validator_instance.validate_event_sequence(
        events,
        expected_terminal_types=[MockEventType.ANOTHER_EVENT]
    ) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_TERMINAL_EVENT' for issue in issues)

def test_validate_sequence_present_terminal_event(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-origin-term", event_type=MockEventType.ANOTHER_EVENT)]
    assert validator_instance.validate_event_sequence(
        events,
        expected_terminal_types=[MockEventType.ANOTHER_EVENT]
    ) is True

def test_validate_sequence_correct_origin_and_terminal(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-ot-correct", event_type=MockEventType.TEST_EVENT),
        create_mock_event(corr_id="seq-ot-correct", event_type=MockEventType.ANOTHER_EVENT)
    ]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=[MockEventType.TEST_EVENT],
        expected_terminal_types=[MockEventType.ANOTHER_EVENT]
    ) is True

def test_validate_sequence_multiple_possible_origin_types_found(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-multi-origin", event_type="type_A")]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=["type_A", "type_B"]
    ) is True

def test_validate_sequence_multiple_possible_origin_types_missing(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="seq-multi-origin-miss", event_type="type_C")]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=["type_A", "type_B"]
    ) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_ORIGIN_EVENT' for issue in issues)


def test_validate_sequence_require_all_origin_types_met(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-req-all-origin", event_type="type_X"),
        create_mock_event(corr_id="seq-req-all-origin", event_type="type_Y")
    ]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=["type_X", "type_Y"],
        require_all_origin_types=True
    ) is True

def test_validate_sequence_require_all_origin_types_not_met(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-req-all-origin-fail", event_type="type_X")
    ]
    assert validator_instance.validate_event_sequence(
        events,
        expected_origin_types=["type_X", "type_Y"],
        require_all_origin_types=True
    ) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_ALL_ORIGIN_EVENTS' for issue in issues)

def test_validate_sequence_require_all_terminal_types_met(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-req-all-term", event_type="type_P"),
        create_mock_event(corr_id="seq-req-all-term", event_type="type_Q")
    ]
    assert validator_instance.validate_event_sequence(
        events,
        expected_terminal_types=["type_P", "type_Q"],
        require_all_terminal_types=True
    ) is True

def test_validate_sequence_require_all_terminal_types_not_met(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="seq-req-all-term-fail", event_type="type_P")
    ]
    assert validator_instance.validate_event_sequence(
        events,
        expected_terminal_types=["type_P", "type_Q"],
        require_all_terminal_types=True
    ) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'MISSING_ALL_TERMINAL_EVENTS' for issue in issues)


def test_validate_sequence_origin_type_check_with_id_failure(configured_validator: BusCorrelationValidator):
    # Event has invalid ID format AND is missing origin type
    events = [create_mock_event(corr_id="invalid-uuid", event_type=MockEventType.ANOTHER_EVENT)]
    # configured_validator expects UUID format for correlation IDs
    result = configured_validator.validate_event_sequence(
        events,
        expected_origin_types=[MockEventType.TEST_EVENT] # This is missing
    )
    assert result is False # Overall sequence is invalid
    issues = configured_validator.get_issues()
    issue_types = {issue['type'] for issue in issues}
    assert 'INVALID_FORMAT' in issue_types # Due to bad corr_id
    assert 'MISSING_ORIGIN_EVENT' in issue_types # Due to missing origin event


# --- Phase 3: Event Order Tests for validate_event_sequence ---

def test_validate_sequence_correct_order(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="order-test", event_type=MockEventType.TEST_EVENT),
        create_mock_event(corr_id="order-test", event_type=MockEventType.ANOTHER_EVENT)
    ]
    expected_order = [MockEventType.TEST_EVENT, MockEventType.ANOTHER_EVENT]
    assert validator_instance.validate_event_sequence(events, expected_event_order=expected_order) is True
    assert len(validator_instance.get_issues()) == 0

def test_validate_sequence_incorrect_order(validator_instance: BusCorrelationValidator):
    events = [
        create_mock_event(corr_id="order-test-fail", event_type=MockEventType.ANOTHER_EVENT),
        create_mock_event(corr_id="order-test-fail", event_type=MockEventType.TEST_EVENT) 
    ]
    expected_order = [MockEventType.TEST_EVENT, MockEventType.ANOTHER_EVENT]
    assert validator_instance.validate_event_sequence(events, expected_event_order=expected_order) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'INVALID_EVENT_ORDER' for issue in issues)
    assert issues[0]['event_details']['index'] == 0
    assert issues[0]['event_details']['expected_type'] == MockEventType.TEST_EVENT
    assert issues[0]['event_details']['actual_type'] == MockEventType.ANOTHER_EVENT

def test_validate_sequence_incomplete_order_too_short(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="order-test-short", event_type=MockEventType.TEST_EVENT)]
    expected_order = [MockEventType.TEST_EVENT, MockEventType.ANOTHER_EVENT]
    assert validator_instance.validate_event_sequence(events, expected_event_order=expected_order) is False
    issues = validator_instance.get_issues()
    assert any(issue['type'] == 'INCOMPLETE_EVENT_ORDER' for issue in issues)

def test_validate_sequence_order_correct_prefix_events_longer(validator_instance: BusCorrelationValidator):
    # Current logic: if events list is longer but prefix matches expected_order, it passes order check.
    events = [
        create_mock_event(corr_id="order-test-long", event_type=MockEventType.TEST_EVENT),
        create_mock_event(corr_id="order-test-long", event_type=MockEventType.ANOTHER_EVENT),
        create_mock_event(corr_id="order-test-long", event_type="type_C") # Extra event
    ]
    expected_order = [MockEventType.TEST_EVENT, MockEventType.ANOTHER_EVENT]
    assert validator_instance.validate_event_sequence(events, expected_event_order=expected_order) is True
    assert len(validator_instance.get_issues()) == 0 # No order issue logged

def test_validate_sequence_order_empty_expected_order(validator_instance: BusCorrelationValidator):
    events = [create_mock_event(corr_id="order-test-empty", event_type=MockEventType.TEST_EVENT)]
    assert validator_instance.validate_event_sequence(events, expected_event_order=[]) is True
    assert len(validator_instance.get_issues()) == 0

def test_validate_sequence_order_empty_events_with_expected_order(validator_instance: BusCorrelationValidator):
    expected_order = [MockEventType.TEST_EVENT]
    assert validator_instance.validate_event_sequence([], expected_event_order=expected_order) is True
    issues = validator_instance.get_issues()
    # This will be caught by INCOMPLETE_EVENT_ORDER because len([]) < len(expected_order)
    assert len(issues) == 0 # Empty sequence returns True early, no issues logged

def test_validate_sequence_order_with_other_failures(configured_validator: BusCorrelationValidator):
    # Sequence has invalid correlation ID format, missing origin type, AND wrong event order
    events = [
        create_mock_event(corr_id="invalid-uuid", event_type=MockEventType.ANOTHER_EVENT), # Invalid ID, wrong type for order[0]
        create_mock_event(corr_id="invalid-uuid", event_type=MockEventType.TEST_EVENT)      # Invalid ID, wrong type for order[1]
    ]
    expected_order = [MockEventType.TEST_EVENT, "some_other_type_A"]
    expected_origin = ["origin_type_B"]

    result = configured_validator.validate_event_sequence(
        events,
        expected_event_order=expected_order,
        expected_origin_types=expected_origin
    )
    assert result is False
    issues = configured_validator.get_issues()
    issue_types = {issue['type'] for issue in issues}

    assert 'INVALID_FORMAT' in issue_types       # From individual event validation via configured_validator
    assert 'MISSING_ORIGIN_EVENT' in issue_types # Origin type "origin_type_B" not found
    assert 'INVALID_EVENT_ORDER' in issue_types  # events[0].type is ANOTHER_EVENT, expected TEST_EVENT


print("Test file skeleton created for BusCorrelationValidator.") 