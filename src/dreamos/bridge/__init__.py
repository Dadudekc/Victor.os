"""
Dream.OS Bridge Modules

This package contains the core bridge modules for Dream.OS:
- Module 1: Injector
- Module 2: Processor
- Module 3: Logging & Error Handling
- Module 4: External System Integration
"""

__version__ = "0.1.0"

from .module4_integration import ExternalSystemIntegration

__all__ = ['ExternalSystemIntegration'] 