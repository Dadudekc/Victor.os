from enum import Enum

class ValidationStatus(Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"

class ValidationResult:
    def __init__(self, status=ValidationStatus.PASSED, message="", details=None):
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = None

class ImprovementValidator:
    def __init__(self, state_dir):
        self.state_dir = state_dir

    def validate(self, *args, **kwargs):
        return True
    def validate_improvement(self, *args, **kwargs):
        return ValidationResult()

def validate_all_files(logger, config, is_onboarding=False):
    return ValidationResult() 