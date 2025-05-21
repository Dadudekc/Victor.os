# THEA Output Extractor

A robust utility for extracting THEA's responses from the Cursor interface. This tool provides a reliable way to capture THEA's output using visual cue detection and clipboard monitoring.

## Features

- Visual cue detection for reliable response completion detection
- Clipboard monitoring as a fallback method
- Dynamic waiting mechanism instead of fixed sleep
- Comprehensive error handling and logging
- Configurable timeouts and confidence thresholds

## Usage

```python
from dreamos.core.config import AppConfig
from dreamos.tools.functional.thea_output_extractor import extract_thea_response

# Create configuration
config = AppConfig()
config.set("paths.gui_images", "path/to/gui/templates")

# Extract THEA's response
response = extract_thea_response(config)
if response:
    print(f"Extracted response: {response}")
else:
    print("Failed to extract response")
```

## Configuration

The extractor requires the following configuration:

- `paths.gui_images`: Directory containing GUI template images
  - Must contain `thea_response_complete_cue.png` for visual cue detection
  - If not found, falls back to clipboard monitoring

## Constants

The following constants can be adjusted based on your needs:

- `RESPONSE_CHECK_INTERVAL`: Time between checks (default: 1.0 seconds)
- `MAX_WAIT_TIME`: Maximum time to wait for response (default: 60.0 seconds)
- `CONFIDENCE_THRESHOLD`: Image matching confidence (default: 0.8)

## Methods

### Visual Cue Detection

The primary method uses visual cue detection to determine when THEA has finished responding:

1. Continuously monitors for a visual cue in the Cursor interface
2. When the cue is detected, waits briefly for text to be fully rendered
3. Extracts the response from the clipboard

### Clipboard Monitoring

A fallback method that monitors clipboard changes:

1. Tracks clipboard content changes
2. When content changes, waits to see if it stabilizes
3. If no changes for 5 seconds, assumes response is complete
4. Extracts the final clipboard content

## Error Handling

The extractor includes comprehensive error handling:

- Logs warnings if visual cue image is not found
- Handles clipboard access errors gracefully
- Provides timeout protection against infinite waits
- Returns None for empty or invalid responses

## Testing

Run the test suite with:

```bash
pytest tests/tools/functional/test_thea_output_extractor.py
```

## Dependencies

- pyautogui: For visual cue detection
- pyperclip: For clipboard monitoring
- pytest: For testing

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 