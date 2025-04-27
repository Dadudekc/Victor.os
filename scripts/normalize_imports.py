#!/usr/bin/env python3
import pathlib

# Mapping of old import paths to new locations
MAPPINGS = {
    'from dreamos.utils': 'from dreamos.services.utils',
    'import dreamos.utils': 'import dreamos.services.utils',
    'from dreamos.rendering': 'from dreamos.feedback.rendering',
    'import dreamos.rendering': 'import dreamos.feedback.rendering',
    'from dreamos.monitoring': 'from dreamos.services.monitoring',
    'import dreamos.monitoring': 'import dreamos.services.monitoring',
    'from dreamos.hooks': 'from dreamos.services.hooks',
    'import dreamos.hooks': 'import dreamos.services.hooks',
    'from dreamos.chat_engine': 'from dreamos.feedback.chat_engine',
    'import dreamos.chat_engine': 'import dreamos.feedback.chat_engine',
    'from dreamos.tools': 'from dreamos.coordination.tools',
    'import dreamos.tools': 'import dreamos.coordination.tools',
    'from dreamos.version': 'from dreamos.services.version',
    'import dreamos.version': 'import dreamos.services.version',
    'from dreamos.agent_bus': 'from dreamos.coordination.agent_bus',
    'import dreamos.agent_bus': 'import dreamos.coordination.agent_bus',
    'from dreamos.governance_memory_engine': 'from dreamos.memory.governance_memory_engine',
    'import dreamos.governance_memory_engine': 'import dreamos.memory.governance_memory_engine',
}

def normalize_file(path: pathlib.Path):
    text = path.read_text(encoding='utf-8')
    for old, new in MAPPINGS.items():
        if old in text:
            text = text.replace(old, new)
    path.write_text(text, encoding='utf-8')

def main():
    for py_file in pathlib.Path('src/dreamos').rglob('*.py'):
        normalize_file(py_file)
    print("Imports normalized.")

if __name__ == '__main__':
    main() 