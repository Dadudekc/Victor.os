"""Report generation modules for different output formats."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from jinja2 import Environment, FileSystemLoader

from .analyzers import SizeAnalyzer
from .constants import DEFAULT_REPORT_FORMATS, DEFAULT_REPORT_TEMPLATE, REPORT_DIR

logger = logging.getLogger(__name__)


class BaseReporter:
    """Base class for report generators."""

    def __init__(self, output_dir: Path = REPORT_DIR):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_timestamp(self) -> str:
        """Get current timestamp for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")


class MarkdownReporter(BaseReporter):
    """Generates markdown reports."""

    def generate(self, stats: Dict, imports: Dict, large_files: List[tuple]) -> Path:
        """Generate a markdown report."""
        output_file = self.output_dir / f"project_scan_{self._get_timestamp()}.md"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write("# Project Scan Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # File Statistics
            f.write("## File Statistics\n\n")
            f.write("### Directory Sizes\n\n")
            for dir_path, size in stats["dir_sizes"].items():
                f.write(f"- {dir_path}: {SizeAnalyzer.format_size(size)}\n")

            f.write("\n### File Counts by Type\n\n")
            for ext, count in stats["file_counts"].items():
                f.write(f"- {ext}: {count} files\n")

            # Import Analysis
            f.write("\n## Import Analysis\n\n")
            f.write("### Most Used Imports\n\n")
            for imp, count in sorted(imports.items(), key=lambda x: x[1], reverse=True)[
                :20
            ]:
                f.write(f"- {imp}: {count} uses\n")

            # Large Files
            f.write("\n## Large Files\n\n")
            for file_path, size in large_files:
                f.write(f"- {file_path}: {SizeAnalyzer.format_size(size)}\n")

        return output_file


class JsonReporter(BaseReporter):
    """Generates JSON reports."""

    def generate(self, stats: Dict, imports: Dict, large_files: List[tuple]) -> Path:
        """Generate a JSON report."""
        output_file = self.output_dir / f"project_scan_{self._get_timestamp()}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "statistics": stats,
            "imports": imports,
            "large_files": [
                {"path": str(path), "size": size} for path, size in large_files
            ],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return output_file


class ReportGenerator:
    """Generates reports in various formats."""

    def __init__(self, project_root: Path, analysis: Dict):
        self.project_root = project_root
        self.analysis = analysis
        self.report_dir = project_root / REPORT_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        template_dir = project_root / "templates"
        if template_dir.exists():
            self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        else:
            self.env = Environment()

    def save_report(self, formats: List[str] = None):
        """Save analysis results in specified formats."""
        formats = formats or DEFAULT_REPORT_FORMATS

        for fmt in formats:
            if fmt == "json":
                self._save_json_report()
            elif fmt == "markdown":
                self._save_markdown_report()
            else:
                logger.warning(f"Unsupported report format: {fmt}")

    def _save_json_report(self):
        """Save analysis results as JSON."""
        output_file = self.report_dir / f"project_analysis_{self._get_timestamp()}.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(self.analysis, f, indent=2)
        logger.info(f"Saved JSON report to {output_file}")

    def _save_markdown_report(self):
        """Save analysis results as Markdown."""
        output_file = self.report_dir / f"project_analysis_{self._get_timestamp()}.md"

        # Try to use template if available
        try:
            template = self.env.get_template(DEFAULT_REPORT_TEMPLATE)
            content = template.render(
                analysis=self.analysis,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                project_root=str(self.project_root),
            )
        except Exception as e:
            logger.warning(f"Failed to use template: {e}")
            content = self._generate_markdown_content()

        with output_file.open("w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Saved Markdown report to {output_file}")

    def _generate_markdown_content(self) -> str:
        """Generate markdown content without template."""
        lines = [
            "# Project Analysis Report",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\nProject Root: {self.project_root}",
            "\n## File Statistics\n",
        ]

        # File counts by language
        lang_counts = {}
        for file_data in self.analysis.values():
            lang = file_data.get("language", "unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1

        lines.append("\n### Files by Language")
        for lang, count in sorted(lang_counts.items()):
            lines.append(f"- {lang}: {count} files")

        # Complexity statistics
        total_complexity = sum(f.get("complexity", 0) for f in self.analysis.values())
        avg_complexity = total_complexity / len(self.analysis) if self.analysis else 0
        lines.extend(
            [
                "\n### Complexity Statistics",
                f"- Total Complexity: {total_complexity}",
                f"- Average Complexity: {avg_complexity:.1f}",
            ]
        )

        # Most complex files
        complex_files = sorted(
            self.analysis.items(), key=lambda x: x[1].get("complexity", 0), reverse=True
        )[:10]

        lines.extend(
            [
                "\n### Most Complex Files",
                *[
                    f"- {path}: {data.get('complexity', 0)}"
                    for path, data in complex_files
                ],
            ]
        )

        return "\n".join(lines)

    def generate_init_files(self, overwrite: bool = True):
        """Generate __init__.py files for Python packages."""
        for file_path, data in self.analysis.items():
            if data.get("language") == "python":
                dir_path = Path(file_path).parent
                init_file = dir_path / "__init__.py"

                if not init_file.exists() or overwrite:
                    try:
                        with init_file.open("w", encoding="utf-8") as f:
                            f.write('"""Package initialization."""\n\n')
                    except Exception as e:
                        logger.error(f"Failed to create {init_file}: {e}")

    def export_chatgpt_context(
        self, template_path: Optional[str] = None, output_path: Optional[str] = None
    ):
        """Export analysis results as ChatGPT context."""
        output_path = output_path or str(
            self.report_dir / "chatgpt_project_context.json"
        )

        # Try to use template if provided
        if template_path and Path(template_path).exists():
            try:
                template = self.env.get_template(template_path)
                content = template.render(analysis=self.analysis)
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return
            except Exception as e:
                logger.warning(f"Failed to use template: {e}")

        # Fallback to basic JSON export
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.analysis, f, indent=2)
