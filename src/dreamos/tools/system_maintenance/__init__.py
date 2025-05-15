"""
DreamOS System Maintenance Tools

A collection of tools for maintaining system health and cleanliness:
- Duplicate directory cleanup
- Backup management
- Log consolidation
- Test directory management
"""

from .cleanup_duplicates import DuplicatesCleaner
from .maintenance_service import MaintenanceService

__all__ = ['DuplicatesCleaner', 'MaintenanceService']
__version__ = '1.0.0' 