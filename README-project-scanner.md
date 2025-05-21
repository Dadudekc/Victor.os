# Dream.OS Project Scanner

The Project Scanner is a tool that analyzes your codebase and creates structured reports and context files for AI assistants.

## Features

- Scans your project files and analyzes their contents
- Identifies functions, classes, imports, and more
- Generates a detailed Markdown report of the project structure
- Creates context files for AI assistants (like ChatGPT)
- Uses caching to speed up subsequent scans
- Intelligently splits output to avoid token limits in AI models
- Excludes virtual environments, binary files, and other non-essential content

## Installation

The scanner is included with Dream.OS, but can also be used as a standalone module:

```bash
pip install dreamos-tools
```

Or directly from your project:

```bash
python -m dreamos.tools.project_scanner
```

## Usage

### Basic Use

```bash
python -m dreamos.tools.project_scanner --project-root /path/to/your/project
```

### Options

- `--project-root`: Root directory of the project to scan
- `--exclude`: Directory or file patterns to exclude (can be used multiple times)
  - Example: `--exclude node_modules --exclude "*.log"`
- `--no-cache`: Disable using the file hash cache
- `--workers`: Number of worker threads for analysis (default: 4)
- `--split-output`: How to split the context output (default: "directory")
  - Choices: "directory", "language", or "none"
- `--max-files-per-chunk`: Maximum files per chunk when using "none" split (default: 100)
- `--cache-file`: Custom path to cache file
- `--analysis-output`: Custom path for analysis report
- `--context-output`: Custom path for ChatGPT context file

### Output Splitting

One of the key features is the ability to split the context output for large projects:

1. **Directory-based splitting** (default): Creates separate files for each top-level directory
   ```bash
   python -m dreamos.tools.project_scanner --split-output directory
   ```

2. **Language-based splitting**: Groups files by programming language
   ```bash
   python -m dreamos.tools.project_scanner --split-output language
   ```

3. **Fixed-size chunks**: Splits into equal-sized chunks
   ```bash
   python -m dreamos.tools.project_scanner --split-output none --max-files-per-chunk 50
   ```

## Output Files

The scanner generates several files:

- `project_scan_report.md`: A detailed Markdown report about your project
- `project_context_*.json`: One or more files containing structured information about your project
- `project_context_index.json`: An index file that references all the context chunks
- `project_metadata.json`: Overall project statistics and metadata

By default, these files are saved in the `runtime/reports` directory of your project.

## Ignored Files and Directories

The scanner automatically ignores:

- Virtual environments (venv, .venv, etc.)
- Build artifacts and caches (__pycache__, node_modules, etc.)
- Binary files and large media files
- Version control directories (.git, .svn)
- IDE-specific directories (.vscode, .idea)
- Large files (over 10MB by default)

## Using with AI Assistants

The generated context files are designed to be used with AI assistants like ChatGPT:

1. Run the scanner to generate the context files
2. Upload the `project_context_*.json` files to your AI assistant
3. Ask questions about your codebase

For very large projects, you can upload just the index and metadata files first, then load specific chunks as needed based on the directory or language of interest.

## Troubleshooting

- **Scanner is slow**: Try increasing the number of workers with `--workers`
- **Output files are too large**: Use the `--split-output` option to break them into smaller chunks
- **Still picking up unwanted files**: Use `--exclude` to specify additional patterns to ignore 