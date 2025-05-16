#!/usr/bin/env python3
"""
Analyzes and reports on potentially orphaned or archived files.
Helps identify files that can be safely removed or archived.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set, Tuple

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class OrphanedFileAnalyzer:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.runtime_dir = workspace_root / 'runtime'
        
        # Directories that might contain orphaned files
        self.potential_orphan_dirs = {
            'jarvis_test': 'Deprecated test files',
            'jarvis_memory': 'Deprecated memory files',
            'corrupted': 'Corrupted or invalid files',
            'backups': 'Old backup files',
            'task_migration_backups': 'Old task migration backups',
            'cleanup_backups': 'Cleanup operation backups',
            'ui_failures': 'UI failure logs and screenshots',
            'parallel_logs': 'Parallel execution logs',
            'temp': 'Temporary files'
        }
        
        # File patterns that are safe to clean up
        self.cleanup_patterns = {
            '.tmp', '.bak', '.old', '.backup',
            'temp_', 'backup_', 'test_', 'debug_'
        }
        
    def is_recently_modified(self, path: Path, days: int = 30) -> bool:
        """Check if a file was modified within the specified number of days."""
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            return (datetime.now() - mtime) <= timedelta(days=days)
        except Exception:
            return False
            
    def is_referenced(self, file_path: Path) -> bool:
        """Check if a file is referenced in any .json or .py files."""
        file_name = file_path.name
        
        # Search in Python and JSON files
        for ext in ['.py', '.json']:
            for f in self.workspace_root.rglob(f'*{ext}'):
                if f == file_path:
                    continue
                try:
                    content = f.read_text(encoding='utf-8')
                    if file_name in content:
                        return True
                except Exception:
                    continue
        return False
        
    def analyze_directory(self, dir_path: Path) -> Dict:
        """Analyze a directory for potentially orphaned files."""
        if not dir_path.exists():
            return {
                'status': 'missing',
                'files': [],
                'total_size': 0
            }
            
        results = {
            'status': 'active' if self.is_recently_modified(dir_path) else 'inactive',
            'files': [],
            'total_size': 0
        }
        
        for item in dir_path.rglob('*'):
            if not item.is_file():
                continue
                
            file_info = {
                'path': str(item.relative_to(self.workspace_root)),
                'size': item.stat().st_size,
                'last_modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat(),
                'is_recent': self.is_recently_modified(item),
                'is_referenced': self.is_referenced(item),
                'is_temp_pattern': any(pattern in item.name.lower() for pattern in self.cleanup_patterns)
            }
            
            results['files'].append(file_info)
            results['total_size'] += file_info['size']
            
        return results
        
    def generate_report(self) -> Dict:
        """Generate a comprehensive report of potentially orphaned files."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'workspace_root': str(self.workspace_root),
            'directories': {}
        }
        
        for dir_name, description in self.potential_orphan_dirs.items():
            dir_path = self.runtime_dir / dir_name
            report['directories'][dir_name] = {
                'description': description,
                'analysis': self.analyze_directory(dir_path)
            }
            
        return report
        
    def save_report(self, report: Dict):
        """Save the analysis report to a file."""
        report_file = self.workspace_root / 'runtime' / 'reports' / 'orphaned_files_report.json'
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
        with report_file.open('w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Report saved to: {report_file}")
        
    def suggest_cleanup_actions(self, report: Dict) -> List[str]:
        """Generate cleanup suggestions based on the analysis."""
        suggestions = []
        
        for dir_name, dir_info in report['directories'].items():
            analysis = dir_info['analysis']
            
            if analysis['status'] == 'missing':
                continue
                
            if analysis['status'] == 'inactive':
                suggestions.append(f"Consider archiving inactive directory: {dir_name}")
                
            safe_to_delete = []
            needs_review = []
            
            for file_info in analysis['files']:
                path = file_info['path']
                
                if file_info['is_temp_pattern'] and not file_info['is_recent']:
                    safe_to_delete.append(path)
                elif not file_info['is_recent'] and not file_info['is_referenced']:
                    needs_review.append(path)
                    
            if safe_to_delete:
                suggestions.append(f"\nSafe to delete in {dir_name}:")
                suggestions.extend(f"  - {path}" for path in safe_to_delete)
                
            if needs_review:
                suggestions.append(f"\nNeeds review in {dir_name}:")
                suggestions.extend(f"  - {path}" for path in needs_review)
                
        return suggestions

def main():
    workspace_root = Path(__file__).resolve().parent.parent
    analyzer = OrphanedFileAnalyzer(workspace_root)
    
    # Generate and save report
    report = analyzer.generate_report()
    analyzer.save_report(report)
    
    # Print cleanup suggestions
    suggestions = analyzer.suggest_cleanup_actions(report)
    print("\nCleanup Suggestions:")
    print("\n".join(suggestions))

if __name__ == '__main__':
    main() 