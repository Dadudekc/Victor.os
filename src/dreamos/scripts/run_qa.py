#!/usr/bin/env python3
"""
Wrapper for run_qa functions, forwarding to the tools version.
"""
from _agent_coordination.tools.run_qa import (
    generate_markdown_report,
    load_checklist,
    save_checklist,
    update_item_status,
    list_items,
    show_summary,
    main
)

if __name__ == '__main__':
    main() 
