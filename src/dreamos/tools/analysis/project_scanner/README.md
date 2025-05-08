# Project Scanner

## Overview
The `project_scanner.py` script is used for scanning the Dream.OS project. It analyzes the project's structure and performs diagnostics or validation based on configuration settings.

## Requirements
The script requires a valid configuration file to run. The default config file path is:

```
D:/Dream.os/runtime/config/config.yaml
```

This file contains various paths and settings for the project scanner to operate correctly.

## Running the Script
To run the script, use the following command:

```
python -m dreamos.tools.analysis.project_scanner.project_scanner
```

Ensure the `config.yaml` file is present at the default path (`D:/Dream.os/runtime/config/config.yaml`). If the config file is missing, the script will fail with an error.

## Troubleshooting
If the script does not run, make sure the config file is in place and correctly configured. The script expects the paths defined within `config.yaml` to be valid.
