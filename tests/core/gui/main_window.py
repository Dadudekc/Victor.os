import sys, os
import importlib.util

# Add project root to sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Dynamically load the real core.gui.main_window module
module_path = os.path.join(project_root, 'core', 'gui', 'main_window.py')
spec = importlib.util.spec_from_file_location('core.gui.main_window', module_path)
real_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_module)

# Expose the actual classes for testing
TaskManager = real_module.TaskManager
FeedbackEngine = real_module.FeedbackEngine
DreamOSTabManager = real_module.DreamOSTabManager
TabSystemShutdownManager = real_module.TabSystemShutdownManager
DreamOSMainWindow = real_module.DreamOSMainWindow 