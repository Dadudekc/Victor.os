# Project Plan & Structure

This document outlines the current project plan, task assignments, and the target codebase structure. Agents should refer to this document for guidance and update it as the project evolves.

## 1. Overall Mission

- To organize the codebase efficiently, ensure all components are functional, and establish clear processes for ongoing development and agent coordination.

## Agent Operational Protocols & Conduct

All agents assigned to tasks within this project plan, or operating within the Dream.OS environment, are expected to do so in strict adherence to the master `system_prompt.md` and the detailed governance documents found in:

*   `runtime/governance/onboarding/` (especially `agent_autonomy_and_continuous_operation.md`)
*   `runtime/governance/protocols/` (especially `continuous_autonomy_protocol.md`)

These documents define the Universal Agent Loop, non-idling requirements, drift control, self-correction procedures, and (for agents in simulated/interactive modes) specific guidance on maintaining perceived continuity. Familiarity and compliance are mandatory for all autonomous operations.

## 2. Target Directory Structure (ASCII Tree)

```text
# Current Project Structure (Generated {{TODAY_YYYY-MM-DD HH:MM}} - Top-level reviewed, deep structure verification limited by tool timeouts)
# Use (...) to indicate skipped non-priority directories at the root level
# Use [...] to denote files or when directory contents were not listed further
.
.
├── ai_docs/
│   ├── agent_coordination/
│   │   ├── MISSION_LOG.md
│   │   ├── README.md
│   │   └── PROJECT_STRUCTURE.txt
│   ├── api_docs_and_integrations/
│   │   └── README.md
│   ├── architecture/
│   │   └── .gitkeep
│   ├── architecture_docs/
│   │   └── README.md
│   ├── best_practices/
│   │   ├── README.md
│   │   └── .gitkeep
│   ├── business_logic/
│   │   ├── README.md
│   │   └── .gitkeep
│   ├── implementation_notes/
│   │   └── .gitkeep
│   ├── onboarding/
│   │   └── .gitkeep
│   └── project_patterns/
│       └── .gitkeep
├── apps/
│   ├── browser/
│   │   └── main.py
│   ├── examples/
│   │   ├── onboarding_message_injector.py
│   │   ├── reflection_agent.py
│   │   └── stubs/
│   │       └── agent_1_stub.py
│   └── sky_viewer/
│       ├── sky.html
│       ├── sky_viewer.py
│       └── templates/
│           ├── planets.html
│           └── textures/
│               └── [...] # Image files
├── assets/ (...)
├── audit/ (...)
├── bridge/ (...)
├── docs/ (...)
├── node_modules/ (...)
├── prompts/ (...)
├── reports/ (...)
├── runtime/ (...)
├── sandbox/ (...)
├── scripts/
│   ├── analyze_latency_trends.py
│   ├── bridge_health_report.py
│   ├── bridge_integrity_monitor.py
│   ├── bridge_mutation_impact_report.py
│   ├── gpt_cursor_relay.py
│   ├── monitor_bridge.py
│   ├── mutation_test_bridge.py
│   ├── simulate_tool_timeout.py
│   ├── stress_test_bridge.py
│   ├── swarm_monitor.py
│   ├── task_flow_migration.py
│   ├── test_edit_file_failures.py
│   ├── test_file_integrity_recovery.py
│   ├── test_thea_bridge_pipeline.py
│   ├── thea_to_cursor_agent.py
│   └── agents/
│       ├── autonomy_manifest_agent9.json
│       └── new_agent.py
├── specs/
│   ├── PROJECT_PLAN.md
│   ├── README.md
│   ├── current_plan.md
│   ├── mission_status.md
│   └── project_tree.txt
├── src/
│   ├── __init__.py
│   ├── __pycache__/ [...]
│   ├── dreamos/
│   │   ├── __init__.py
│   │   ├── __pycache__/ [...]
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── Agent-1/ [...]
│   │   │   ├── agent2_infra_surgeon.py
│   │   │   ├── agent3/ [...]
│   │   │   ├── agent5/ [...]
│   │   │   ├── agent9_response_injector.py
│   │   │   ├── agents/ [...]
│   │   │   ├── autonomy_recovery_patch.py
│   │   │   ├── base_agent.py
│   │   │   ├── chatgpt_web_agent.py
│   │   │   ├── context_router_agent.py
│   │   │   ├── cursor_dispatcher.py
│   │   │   ├── cursor_worker.py
│   │   │   ├── library/ [...]
│   │   │   ├── mixins/ [...]
│   │   │   ├── recovery_coordinator.py
│   │   │   ├── supervisor_agent.py
│   │   │   ├── task_feedback_router.py
│   │   │   ├── utils.py
│   │   │   ├── utils/ [...]
│   │   │   └── validation/ [...]
│   │   ├── apps/
│   │   │   └── dreamscape/
│   │   │       ├── __init__.py
│   │   │       ├── __pycache__/ [...]
│   │   │       ├── README.md
│   │   │       ├── discord_templates/ [...] # Empty
│   │   │       ├── dreamscape_generator/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── __pycache__/ [...]
│   │   │       │   ├── chrome_profile/ [...]
│   │   │       │   ├── main.py
│   │   │       │   ├── src/ [...]
│   │   │       │   ├── templates/ [...]
│   │   │       │   └── threads/ [...]
│   │   │       ├── dreamscape_gui/ [...] # Empty
│   │   │       ├── memory/ [...] # Empty
│   │   │       ├── requirements.txt
│   │   │       ├── scripts/ [...] # Empty
│   │   │       ├── templates/
│   │   │       │   └── dreamscape/ [...]
│   │   │       ├── tests/
│   │   │       │   └── __pycache__/ [...]
│   │   │       └── venv_qt_test/
│   │   │           └── Lib/ [...]
│   │   ├── automation/ # <--- Possible pyautogui relevance
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── README.md
│   │   │   ├── bridge_loop.py
│   │   │   ├── cursor_orchestrator.py
│   │   │   ├── execution/ [...]
│   │   │   └── utils/ [...]
│   │   ├── bridge/
│   │   │   ├── bridge_loop.py
│   │   │   ├── bridge_loop_alert.flag
│   │   │   ├── bridge_loop_status.log
│   │   │   ├── cursor_to_gpt.jsonl
│   │   │   └── gpt_to_cursor.jsonl
│   │   ├── channels/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── azure_blob_channel.py
│   │   │   ├── azure_eventhub_channel.py
│   │   │   ├── channel_loader.py
│   │   │   └── local_blob_channel.py
│   │   ├── chat_engine/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── base_chat_adapter.py
│   │   │   ├── chat_cycle_controller.py
│   │   │   ├── chat_scraper_service.py
│   │   │   ├── discord_dispatcher.py
│   │   │   ├── driver_manager.py
│   │   │   ├── feedback_engine.py
│   │   │   ├── feedback_engine_v2.py
│   │   │   ├── gui_event_handler.py
│   │   │   └── prompt_execution_service.py
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   ├── __main__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── bridge_diagnostic.py
│   │   │   ├── calibrate_gui_coords.py # <--- pyautogui relevance
│   │   │   ├── main.py
│   │   │   ├── manage_tasks.py
│   │   │   ├── safe_edit_json_list.md
│   │   │   ├── safe_edit_json_list.py
│   │   │   ├── safe_writer_cli.py
│   │   │   └── state_cmds.py
│   │   ├── config_files/
│   │   │   ├── __init__.py
│   │   │   └── __pycache__/ [...]
│   │   ├── coordination/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── agent_bus.py
│   │   │   ├── dispatcher.py
│   │   │   ├── dispatchers/
│   │   │   │   ├── base_dispatcher.py
│   │   │   │   └── dispatchers/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── __pycache__/ [...]
│   │   │   │       └── base_dispatcher.py
│   │   │   ├── event_payloads.py
│   │   │   ├── governance_utils.py
│   │   │   ├── project_board_manager.py
│   │   │   ├── tasks/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── task-schema.json
│   │   │   │   └── task_utils.py
│   │   │   └── voting_coordinator.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── agents/ [...]
│   │   │   ├── awareness/ [...]
│   │   │   ├── bots/ [...]
│   │   │   ├── comms/ [...]
│   │   │   ├── config.py
│   │   │   ├── coordination/ [...]
│   │   │   ├── db/ [...]
│   │   │   ├── errors/ [...]
│   │   │   ├── events/ [...]
│   │   │   ├── feedback/ [...]
│   │   │   ├── health_checks/ [...]
│   │   │   ├── identity/ [...]
│   │   │   ├── logging/ [...]
│   │   │   ├── narrative/ [...]
│   │   │   ├── state/ [...]
│   │   │   ├── swarm_sync.py
│   │   │   ├── tasks/ [...]
│   │   │   ├── tools/ [...]
│   │   │   ├── tts/ [...]
│   │   │   ├── utils/ [...]
│   │   │   └── validation_utils.py
│   │   ├── dashboard/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── dashboard_app.py
│   │   │   ├── dashboard_ui.py
│   │   │   └── templates/
│   │   │       └── dashboard.html
│   │   ├── feedback/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   └── feedback_engine_v2.py
│   │   ├── gui/ # <--- Possible pyautogui relevance
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── main_window.py
│   │   │   └── supervisor_alert_viewer.py
│   │   ├── hooks/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── chatgpt_responder.py
│   │   │   ├── chronicle_logger.py
│   │   │   ├── conversation_logger.py
│   │   │   ├── devlog_hook.py
│   │   │   └── stats_logger.py
│   │   ├── identity/
│   │   │   ├── models.py
│   │   │   └── store.py
│   │   ├── integrations/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── agent_services/
│   │   │   │   └── cursor_shadow_controller.py
│   │   │   ├── azure_blob_client.py
│   │   │   ├── browser_client.py
│   │   │   ├── cursor/ # <--- Possible pyautogui relevance
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── coordination/
│   │   │   │   │   └── __init__.py
│   │   │   │   ├── cursor_prompt_controller.py # Mentions deprecation
│   │   │   │   ├── swarm_bootloader.py
│   │   │   │   ├── utils.py
│   │   │   │   └── window_controller.py
│   │   │   ├── discord_bot.py
│   │   │   ├── discord_client.py
│   │   │   ├── openai_client.py
│   │   │   └── social/
│   │   │       ├── config/ [...]
│   │   │       ├── content/ [...]
│   │   │       ├── core/
│   │   │       │   ├── __init__.py
│   │   │       │   ├── coordination/ [...]
│   │   │       │   ├── exceptions/ [...]
│   │   │       │   └── strategies/ [...]
│   │   │       ├── docs/ [...]
│   │   │       ├── scripts/ [...]
│   │   │       ├── strategies/ [...]
│   │   │       └── templates/ [...]
│   │   ├── llm_bridge/
│   │   │   ├── .keep
│   │   │   └── bridge_adapters/
│   │   │       └── base_adapter.py
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── compaction_utils.py
│   │   │   ├── layers/
│   │   │   │   └── task_memory_layer.py
│   │   │   ├── memory_manager.py
│   │   │   └── summarization_utils.py
│   │   ├── monitoring/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── performance_logger.py
│   │   │   └── prompt_execution_monitor.py
│   │   ├── prompts/
│   │   │   ├── agent_autonomy_directive_v2.md
│   │   │   ├── governance/
│   │   │   │   └── supervisor_election_initiation_prompt.md
│   │   │   ├── social/
│   │   │   │   └── analyze_context.j2
│   │   │   └── task_list.md
│   │   ├── rendering/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   └── template_engine.py
│   │   ├── reporting/
│   │   │   ├── devlog_utils.py
│   │   │   └── scoring_analyzer.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── agent-task-progress.schema.json
│   │   │   ├── bridge_status_schema.json
│   │   │   └── scraped-response.schema.json
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── event_logger.py
│   │   │   ├── failed_prompt_archive.py
│   │   │   ├── hooks/
│   │   │   │   └── .keep
│   │   │   ├── memory_maintenance_service.py
│   │   │   ├── monitoring/
│   │   │   │   └── .keep
│   │   │   ├── services/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── services_map.md
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       ├── __pycache__/ [...]
│   │   │       ├── .keep
│   │   │       ├── chatgpt_scraper.py
│   │   │       ├── content/
│   │   │       │   └── post_context_generator.py
│   │   │       ├── cursor.py
│   │   │       ├── devlog_analyzer.py
│   │   │       ├── devlog_dispatcher.py
│   │   │       ├── devlog_generator.py
│   │   │       ├── feedback_processor.py
│   │   │       ├── logging_utils.py
│   │   │       ├── retry_utils.py
│   │   │       └── selenium_utils.py
│   │   ├── social/
│   │   │   ├── __init__.py
│   │   │   ├── .keep
│   │   │   ├── documentation/
│   │   │   │   └── agent_analysis_philosophy.md
│   │   │   ├── exceptions/
│   │   │   │   └── __init__.py
│   │   │   └── utils/
│   │   │       └── __init__.py
│   │   ├── supervisor_tools/
│   │   │   └── __pycache__/ [...]
│   │   ├── templates/
│   │   │   ├── chatgpt_governance.md.j2
│   │   │   ├── chatgpt_task_prompt.j2
│   │   │   ├── context_snapshot.j2
│   │   │   ├── lore/
│   │   │   │   └── devlog_lore.j2
│   │   │   ├── social/
│   │   │   │   ├── generic_event.j2
│   │   │   │   ├── proposal_update.j2
│   │   │   │   └── twitter_post.j2
│   │   │   └── task_list.md
│   │   ├── tools/ # <--- pyautogui relevance likely inside subdirs
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── .keep
│   │   │   ├── _core/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── base.py
│   │   │   │   └── registry.py
│   │   │   ├── analysis/
│   │   │   │   ├── dead_code.py
│   │   │   │   └── project_scanner/
│   │   │   │       ├── __init__.py
│   │   │   │       ├── __pycache__/ [...]
│   │   │   │       ├── analyzer.py
│   │   │   │       ├── concurrency.py
│   │   │   │       ├── file_processor.py
│   │   │   │       ├── project_scanner.py
│   │   │   │       └── report_generator.py
│   │   │   ├── calibration/ # <--- pyautogui relevance
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── calibration/
│   │   │   │   │   └── calibrate_agent_gui.py
│   │   │   │   └── recalibrate_coords.py
│   │   │   ├── code_analysis/ [...] # Empty
│   │   │   ├── command_supervisor.py
│   │   │   ├── coordination/
│   │   │   │   └── broadcast_directive.py
│   │   │   ├── cursor_bridge/ # <--- pyautogui relevance
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── cursor_bridge.py
│   │   │   │   └── mock_cursor_bridge.py
│   │   │   ├── discovery/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── archive_defunct_tests.py
│   │   │   │   ├── find_defunct_tests.py
│   │   │   │   └── find_todos.py
│   │   │   ├── dreamos_utils/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── .keep
│   │   │   │   ├── README.md
│   │   │   │   ├── archive_agent_mailboxes.py
│   │   │   │   └── check_agent_pulse.py
│   │   │   ├── functional/ # <--- pyautogui relevance
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── context_planner_tool.py
│   │   │   │   └── gui_interaction.py
│   │   │   ├── maintenance/
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── archive_agent_comms.py
│   │   │   │   ├── archive_agent_mailboxes.py
│   │   │   │   ├── augment_task_tags.py
│   │   │   │   ├── find_duplicate_tasks.py
│   │   │   │   ├── validate_logs.py
│   │   │   │   └── validate_onboarding_prompts.py
│   │   │   ├── scripts/
│   │   │   │   └── deployment/ [...] # Empty
│   │   │   ├── thea_relay_agent.py
│   │   │   └── validation/ # <--- pyautogui relevance
│   │   │       ├── check_dependencies.py
│   │   │       └── validation/
│   │   │           ├── __pycache__/ [...]
│   │   │           └── validate_gui_coords.py
│   │   └── utils/ # <--- pyautogui relevance
│   │       ├── __init__.py
│   │       ├── __pycache__/ [...]
│   │       ├── common_utils.py
│   │       ├── coords.py
│   │       ├── decorators.py
│   │       ├── dream_mode_utils/
│   │       │   ├── __init__.py
│   │       │   ├── __pycache__/ [...]
│   │       │   ├── browser.py
│   │   │   │   ├── channel_loader.py
│   │   │   │   ├── cursor_session_manager.py
│   │   │   │   ├── html_parser.py
│   │   │   │   ├── prompt_renderer.py
│   │   │   │   └── task_parser.py
│   │   │   ├── file_io.py
│   │   │   ├── gui_utils.py # Uses pyautogui
│   │   │   ├── logging_utils.py
│   │   │   ├── project_root.py
│   │   │   ├── protocol_compliance_utils.py
│   │   │   ├── safe_json_editor_template.py
│   │   │   ├── schema_validator.py
│   │   │   ├── search.py
│   │   │   └── text.py
│   │   └── dreamscape/
│   │       ├── __init__.py
│   │       ├── __pycache__/ [...]
│   │       ├── agents/
│   │       │   ├── __init__.py
│   │       │   ├── __pycache__/ [...]
│   │       │   ├── planner_agent.py
│   │       │   └── writer_agent.py
│   │       ├── core/
│   │       │   ├── __init__.py
│   │       │   ├── __pycache__/ [...]
│   │       │   └── content_models.py
│   │       ├── events/
│   │       │   ├── __init__.py
│   │       │   ├── __pycache__/ [...]
│   │       │   └── event_types.py
│   │       ├── schemas/
│   │       │   ├── __init__.py
│   │       │   ├── __pycache__/ [...]
│   │       │   └── event_schemas.py
│   │       └── utils/
│   │           └── __init__.py
│   ├── templates/ (...)
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── __pycache__/ [...]
│   │   ├── _archive/ [...] # Empty
│   │   ├── adapters/
│   │   │   └── __pycache__/ [...]
│   │   ├── agents/
│   │   │   ├── __pycache__/ [...]
│   │   │   └── cursor/
│   │   │       └── __pycache__/ [...]
│   │   ├── automation/ [...] # Empty
│   │   ├── cli/
│   │   │   ├── __pycache__/ [...]
│   │   │   └── test_safe_edit_json_list.py
│   │   ├── conftest.py
│   │   ├── coordination/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── cursor/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── dispatchers/
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   └── test_base_dispatcher.py
│   │   │   ├── test_agent_bus.py
│   │   │   ├── test_project_board_manager.py
│   │   │   ├── test_voting_coordinator.py
│   │   │   └── utils/
│   │   │       └── __pycache__/ [...]
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── chat_engine/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── comms/
│   │   │   │   └── test_project_board.py
│   │   │   ├── coordination/
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── tasks/
│   │   │   │   │   └── test_project_board_manager.py
│   │   │   │   ├── test_base_agent.py
│   │   │   │   ├── test_message_patterns.py
│   │   │   │   └── tools/
│   │   │   │       └── __pycache__/ [...]
│   │   │   ├── gui/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── monitoring/
│   │   │   │   └── __pycache__/ [...]
│   │   │   └── utils/
│   │   │       ├── __pycache__/ [...]
│   │   │       ├── test_agent_utils.py
│   │   │       └── test_onboarding_utils.py
│   │   ├── dashboard/
│   │   │   └── test_dashboard_ui.py
│   │   ├── dreamforge/
│   │   │   ├── .pytest_cache/ [...]
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── agents/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── coordination/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── core/
│   │   │   │   └── __pycache__/ [...]
│   │   │   └── services/
│   │   │       └── __pycache__/ [...]
│   │   ├── dreamscape/
│   │   │   └── agents/
│   │   │       ├── test_planner_agent.py
│   │   │       └── test_writer_agent.py
│   │   ├── feedback/
│   │   │   └── chat_engine/ [...] # Empty
│   │   ├── gui/ [...] # Empty
│   │   ├── hooks/
│   │   │   ├── test_chatgpt_responder.py
│   │   │   ├── test_chronicle_logger.py
│   │   │   └── test_stats_logger.py
│   │   ├── integrations/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── azure/
│   │   │   │   └── test_azure_blob_channel.py
│   │   │   └── test_discord_client.py
│   │   ├── llm_bridge/ [...] # Empty
│   │   ├── memory/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── test_compaction_utils.py
│   │   │   ├── test_database_manager.py
│   │   │   ├── test_governance_memory_engine.py
│   │   │   ├── test_memory_compaction.py
│   │   │   ├── test_memory_manager.py
│   │   │   ├── test_summarization_utils.py
│   │   │   └── test_summarizer.py
│   │   ├── monitors/
│   │   │   └── __pycache__/ [...]
│   │   ├── monitoring/
│   │   │   └── __pycache__/ [...]
│   │   ├── rendering/
│   │   │   └── test_template_engine.py
│   │   ├── scripts/
│   │   │   ├── __pycache__/ [...]
│   │   │   └── utils/
│   │   │       └── test_simple_task_updater.py
│   │   ├── services/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── test_event_logger.py
│   │   │   ├── test_failed_prompt_archive.py
│   │   │   ├── test_memory_maintenance_service.py
│   │   │   └── utils/ [...] # Empty
│   │   ├── social/
│   │   │   ├── __pycache__/ [...]
│   │   │   ├── core/
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   └── memory/
│   │   │   │       └── __pycache__/ [...]
│   │   │   ├── integration/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── social/
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   └── strategies/
│   │   │   │       └── __pycache__/ [...]
│   │   │   ├── strategies/
│   │   │   │   └── __pycache__/ [...]
│   │   │   ├── tests/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── __pycache__/ [...]
│   │   │   │   ├── conftest.py
│   │   │   │   ├── core/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── __pycache__/ [...]
│   │   │   │   │   └── memory/ [...] # Empty
│   │   │   │   ├── integration/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── __pycache__/ [...]
│   │   │   │   ├── mock_data/
│   │   │   │   │   └── sample_chat.json
│   │   │   │   ├── social/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── __pycache__/ [...]
│   │   │   │   │   ├── snapshots/
│   │   │   │   │   │   ├── linkedin_post.html
│   │   │   │   │   │   └── twitter_tweet.txt
│   │   │   │   │   └── strategies/
│   │   │   │   │       ├── __pycache__/ [...]
│   │   │   │   │       └── snapshots/ [...]
│   │   │   │   ├── strategies/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── __pycache__/ [...]
│   │   │   │   │   ├── base_strategy_test.py
│   │   │   │   │   └── base_test.py
│   │   │   │   ├── tools/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── __pycache__/ [...]
│   │   │   │   └── utils/
│   │   │   │       ├── __init__.py
│   │   │   │       └── __pycache__/ [...]
│   │   │   └── utils/
│   │   │       └── __pycache__/ [...]
│   │   ├── tools/
│   │   │   └── __pycache__/ [...]
│   │   └── utils/
│   │       └── __pycache__/ [...]
│   ├── supervisor_tools/
│   │   ├── __pycache__/ [...]
│   │   └── test_command_supervisor.py
│   ├── task_nexus/
│   │   └── __pycache__/ [...]
│   ├── tools/ # <--- pyautogui test relevance likely inside subdirs
│   │   ├── __pycache__/ [...]
│   │   ├── cursor_bridge/ # <--- pyautogui test relevance
│   │   │   └── bridge_bootstrap_test.py
│   │   ├── discovery/
│   │   │   └── test_find_todos.py
│   │   ├── functional/ [...] # Empty
│   │   └── test_base.py
│   ├── ui/
│   │   └── __pycache__/ [...]
│   └── utils/
│       ├── __pycache__/ [...]
│       ├── test_json_io.py
│       ├── test_logging_utils.py
│       ├── test_protocol_compliance_utils.py
│       └── test_terminal_execution.py
├── .cursor/ (...)
├── .dreamos_cache/ (...)
├── .flake8
├── .git/ (...)
├── .github/ (...)
├── .gitignore
├── .mypy_cache/ (...)
├── .pre-commit-config.yaml
├── .prettierrc.json
├── .pytest_cache/ (...)
├── .ruff_cache/ (...)
├── .venv/ (...)
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── TASKS.md
├── __pycache__/ (...)
├── _archive/ (...) # Note: Found pyautogui usage in here too
├── archive/ (...)
├── bridge_blockers.md
├── chatgpt_project_context.json
├── cursor_bridge_output_schema.json
├── drift_schema_v2.json
├── final_bridge_report.json
├── future_tasks.json
├── gpt_command_schema.json
├── htmlcov/ (...)
├── import-graph.json
├── knurlshade_module3_completion_report.json
├── orphaned-files.json
├── package-lock.json
├── package.json
├── project_analysis.json
├── pyproject.toml
├── pytest.ini
├── requirements.txt
├── setup.py
├── system_prompt.md
└── working_tasks.json

```
*(This tree reflects the current structure based on the scan. It replaces the previous target structure.)*

## 3. Current Tasks & Priorities

This section lists specific, active project tasks as well as ongoing initiatives for the Dream.OS swarm. Agents should refer here for current assignments and priorities.

| Task ID | Description                                     | Agent Assigned | Status      | Priority | Due Date   | Notes                                                                 |
|---------|-------------------------------------------------|----------------|-------------|----------|------------|-----------------------------------------------------------------------|
| ORG-001 | Create `specs/` directory and initial plan files | AI Assistant   | Done        | High     | YYYY-MM-DD | Initial setup for agent coordination.                                 |
| ORG-002 | Review and organize `ai_docs/` directory      | Agent-8 (Consolidator) | Done        | High     | YYYY-MM-DD | Content from redundant ai_docs/ subdirectories merged into target directories. All target directories verified with content/placeholders. Source directories (e.g., codebase_overview) persist due to tool limitations on directory deletion but are now superseded by content in target locations. `ai_docs/onboarding/README.md` serves as the main index. |
| ORG-003 | Analyze existing task files (`TASKS.md`, etc.)  | AI Assistant   | Done        | Medium   | YYYY-MM-DD | Consolidated into this `PROJECT_PLAN.md`. Task lists combined below.  |
| ORG-004 | Initial codebase scan & structure mapping       | AI Assistant   | Done        | High     | YYYY-MM-DD | Generated `specs/current_tree.txt` with the current structure. |
| ORG-005 | Refactor [Specific Module/Area]               |                | To Do       | Medium   | YYYY-MM-DD | Example task placeholder.                                             |
| FIX-001 | Task Board Permissions (`task_board_updater.py`) | agent-1        | Done        | High     |            | Task seems obsolete. No active error found. `task_board.json` is read-only by dashboard; core logic uses `ProjectBoardManager` and `central_task_boards`. |
| DEV-001 | Project Scanner: `categorize_agents` Impl.    | agent-1        | Done        | Medium     |            | Implemented agent categorization logic in `ProjectScanner` using path and class inheritance heuristics. |
| DEV-002 | Project Scanner: Path Normalization           |                | To Do       | Low      |            | Reduce "Detected move" noise by consistent path separator usage.        |
| DEV-003 | Project Scanner: Install Tree-sitter          | {{AI Assistant (Gemini)}} | {{To Do}}       | Medium     |            | {{Blocker partially resolved. Syntax checks pass. `tree-sitter` Python package added to `requirements.txt`. Next step: Ensure Tree-sitter grammars can be built by `ProjectScanner` (in `src/dreamos/tools/analysis/project_scanner/project_scanner.py`), which likely requires a C compiler in the environment. If grammars build, implement the `TODO` for actual AST analysis. Tree-sitter installation/integration partially done.}} |
| REV-001 | Dependency Review                             | agent-1        | Done        | Medium     |            | Audit `requirements.txt`/`pyproject.toml`, remove unused deps. Unused deps (streamlit, praw, markdownify) were already commented out in pyproject.toml. |
| DEV-004 | YAML Updater Utility                          |                | To Do       | Low      |            | Evaluate/implement robust YAML list append utility (e.g., for contracts). |
| REF-001 | `src/dreamos/dream_mode/` Integration         | {{AI Assistant (Gemini)}} | {{Done}}        | High     |            | {{Context gathered from `dream_mode_utils`. Identified integration point in `chatgpt_web_agent.py`. Refactored agent imports to use browser utilities from `dreamos.utils.dream_mode_utils.browser` instead of placeholders from `gui_utils`. This completes the primary integration step identified for this task.}} |
| ORG-006 | Scan codebase and populate `ai_docs/business_logic/` | agent-1        | Done        | Medium   | YYYY-MM-DD | Populated business logic documentation. (Description updated from 'Review apps/ Structure') |
| REF-002 | Configuration Management                      | agent-1        | Done        | Medium     |            | Review complete. No significant hardcoded paths/settings found in core areas; major components appear to use AppConfig. |
| TEST-001| Import Validation                             | agent-1        | Done        | Medium     |            | Checked imports via `py_compile` on `src/dreamos/`. Fixed `SyntaxError` in `augment_task_tags.py` related to `Agent-1` path. `py_compile` now passes. |
| TEST-002| Test Coverage Increase                        | {{AI Assistant (Gemini)}} | Blocked     | Medium     |            | {{Blocker context updated. `py_compile` checks pass for `src/dreamos/core/config.py` and test files in `tests/core/coordination/*`, indicating syntax/name errors are likely resolved. However, the task remains blocked by the reported tooling limitation preventing *application* of critical fixes needed for coverage increase (possibly related to BLOCK-003's `edit_file` issues).}} |
| TEST-003| Health Checks Review/Expansion                |                | To Do       | Low      |            | Review/expand health checks in `src/dreamos/core/health_checks/`.  |
| DOC-001 | Update `README.md`                            |                | To Do       | Medium     |            | Refresh main README for current structure, setup, usage.              |
| DOC-002 | Document `scripts/`                           |                | To Do       | Low      |            | Add READMEs/usage comments to scripts in `scripts/`.               |
| DOC-003 | Review `DEVELOPER_NOTES.md`                   |                | To Do       | Low      |            | Integrate relevant info from `docs/DEVELOPER_NOTES.md`.             |
| PIPE-001| Agent 2 (`prototype_context_router`)          | Agent 2        | Blocked     | Medium     |            | {{Proceed with design/prototyping once task board is unblocked. Note: The underlying `read_file` instability (BLOCK-002) affecting task board access may be resolved by the `safe_read_with_tool` utility. Agent 2 should re-evaluate if access is now possible. If other specific task board issues persist, please provide details.}} |
| PIPE-002| Agent 3 (`ROUTE_INJECTION_REQUEST`)           | Agent 3        | To Do       | Medium     |            | Define schema and provide example.                                  |
| PIPE-003| Agent 4 (`scraper_attach_context_metadata`)   | Agent 4        | To Do       | Medium     |            | Identify sources and integration hooks.                             |
| PIPE-004| Agent 5 (`scraper_state_machine_conversion`)  | Agent 5        | To Do       | Medium     |            | Define states and refactor.                                         |
| PIPE-005| Agent 6 (`design_pipeline_test_harness`)      | Agent 6        | To Do       | Medium     |            | Outline test cases and harness structure.                           |
| PIPE-006| Agent 7 (`monitor_bus_correlation_consistency`)| Agent 7        | To Do       | Medium     |            | Design validator and plan implementation.                           |
| PIPE-007| Agent 8 (`compile_consolidation_report`)      | Agent 8        | To Do       | Medium     |            | Define ingestion plan.                                              |
| CLEAN-01| Remove Test Code from `core/config.py`        | Agent-7 (SignalMonitor) | Done        | Low      |            | Block was already removed. (From future_tasks)                     |
| TOOL-01 | Integrate Pure Python Vulture Wrapper         | Agent-8 (Consolidator) | Claimed     | Medium     |            | Create wrapper script for vulture, parse output to JSON. (From future_tasks) BLOCKER: Filesystem issue creating scripts/analysis/ dir. |
| CHORE-01| Update Onboarding Autonomy Understanding      | Agent-2        | PENDING     | CHORE    |            | Review loop/swarm directives, update internal knowledge. (From future_tasks) |
| REF-003 | Refine/Implement Task Flow Migration Script   |                | PENDING     | Medium     |            | Refine `propose_task_flow_migration.py` script. (From future_tasks) |
| BLOCK-01| Investigate `read_file` Tool Limitation (on specific JSONs) | Agent-8 (Consolidator) | Claimed     | CRITICAL |            | Potentially related to widespread `read_file` timeouts (BLOCK-002). Investigation likely superseded by or dependent on BLOCK-002. Initial report: `read_file` fails on full read for task JSONs. Needs systematic testing. |
| PF-BRIDGE-INT-001 | PyAutoGUI Bridge: Component Analysis & Module Design | Agent-1 (Pathfinder) | Active | High | YYYY-MM-DD | Analysis of existing GUI utils (`gui_utils`, `coords`, `cursor_orchestrator`, `window_controller`) complete. Component map (`ai_docs/architecture/PF-BRIDGE-INT-001...`) and API proposal (`ai_docs/api_proposals/PF-BRIDGE-INT-001...`) created and updated. `PyAutoGUIControlModule` (`src/dreamos/skills/...`) implemented and tooling blocker resolved via file recreation. `PyAutoGUIBridgeConfig` added to `AppConfig`. Image asset requirements documented in `runtime/assets/bridge_gui_snippets/README.md`. **NEXT STEPS**: 1) Capture required image assets. 2) Develop unit & integration tests. 3) Complete any remaining module docstrings/typing. (Refactoring tracked separately under REFACTOR-PYAUTOGUI-MODULE-001) |
| REFACTOR-PYAUTOGUI-MODULE-001 | Refactor `pyautogui_control_module.py` for modularity and architectural separation. Evaluate moving custom exceptions to a shared `gui_automation_exceptions.py` file and segmenting visual interaction and window management logic into submodules if warranted. | Agent-1 (Pathfinder) | PENDING | 3 | YYYY-MM-DD | Injected by GeneralVictor. Related to PF-BRIDGE-INT-001. Tags: refactor, bridge, gui_automation, technical_debt. |
| BLOCK-002 | CRITICAL: Investigate widespread `read_file` timeouts. Affects `onboarding_autonomous_operation.md`, `PF-BRIDGE-INT-001_PyAutoGUIControlModule_API.md`, and potentially others (incl. task JSONs from BLOCK-01). | AI Assistant (Gemini) | Resolved | CRITICAL | YYYY-MM-DD | Cause identified as `read_file` tool behavior with `should_read_entire_file=True` on 'stale' files. Resolved by implementing `dreamos.utils.file_io.safe_read_with_tool` utility, which uses chunked/warm-up reads, and by adding comprehensive unit tests in `tests/utils/test_json_io.py`. Agents are now expected to use this utility for robust file reading. |
| BLOCK-003 | CRITICAL: `edit_file` tool consistently corrupts `tests/skills/test_pyautogui_control_module.py` when adding multiple test groups, introducing linter errors (e.g., Lines 224-225). | System/Agent-8 | CONFIRMED | CRITICAL | YYYY-MM-DD | Agent-1 encountered 2x identical linter errors after `edit_file` attempts to add `ensure_window_focused` and `find_element_on_screen` tests. Prevents unit test development for `PyAutoGUIControlModule`. **Confirmed**: Investigation reproduced the issue. `edit_file` (even with `reapply`) fails to apply edits correctly to this file, introducing syntax errors or misplacing code. Fixing requires manual intervention or alternative tooling. |
| AGENT8-BRIDGE-IMPL-001 | Implement and document Cursor to ChatGPT Bridge | Agent-8 (Gemini) | Done | CRITICAL | YYYY-MM-DD | Integrated `chatgpt_web_agent.py` with `bridge_loop.py` for live ChatGPT interaction, added PyAutoGUI enhancements, verified logging, and produced comprehensive documentation at `ai_docs/api_docs_and_integrations/cursor_chatgpt_bridge.md`. All planned sub-tasks (BRIDGE-SUBTASK-001 to 006 from `future_tasks.json`) completed. |
| ORG-CONTRIB-DOC-001 | Contribute to Governance Docs (Onboarding, Protocols) | All Agents (except Captain during TASK-SYS-001 or as per specific directives) | Ongoing | Medium   | Continuous | Reflect on operational experiences, identify improvements, propose/apply updates to `runtime/governance/` documents. Focus on clarity, autonomy, and the "Dream.OS way". |
| LOOP-WATCHDOG-001   | `inbox_watcher.py`: monitor timestamps every 60s, trigger auto-resume on stale state. (Points: 400)        | Agent-1        | {{Done}}       |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| ESCALATION-003      | On 5th resume, send context to ChatGPT and await tailored reply. (Points: 500)                             | Agent-2        | {{Done}}       |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| TASK-CHECK-004      | `loop_orchestrator.py`: detect empty task queue and call `refresh_task_queue()`. (Points: 400)             | Agent-3        | {{Done}}       |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| REFRESH-FLOW-005    | Inject new tasks into each agent's inbox, rotate prompts. (Points: 600)                                    | Agent-4        | {{Done}}       |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| FULL-LOOP-006       | Run full cycle: Task > Resume > Escalate > Complete > Refresh > Inject > Resume. (Points: 700)              | Agent-5        | {{Done}}       |          |            | Deps: LOOP-WATCHDOG-001, ESCALATION-003, TASK-CHECK-004, REFRESH-FLOW-005. Milestone for AUTONOMY LOOP RISING episode. |
| LOG-LOOP-007        | Write lifecycle entries to `agent_<n>.md` and update `devlog.md`. (Points: 300)                            | Agent-6        | {{Done}}       |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| YAML-PARSER-008     | Parse episode YAML and extract task list per agent. (Points: 500)                                          | Agent-7        | {{Active}}     |          |            | Milestone for AUTONOMY LOOP RISING episode.                                                                |
| PROMPT-DISPERSER-009| Write parsed tasks into correct inbox files using structured prompt format. (Points: 500)                  | Agent-8        | {{Active}}     |          |            | Deps: YAML-PARSER-008. Milestone for AUTONOMY LOOP RISING episode.                                         |

## 4. Future/Backlog Tasks
