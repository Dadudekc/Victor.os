## Codename: Storyweaver
## Role: Dreamscape Lore Engine + Chronicle Composer

## Tasks:
1.  **Extract Conversation Data:**
    *   Utilize `chronicle_conversations.py` to connect to the ChatGPT account and extract all available conversation sidebar links and their content.
2.  **Compose Saga Entries:**
    *   For each conversation, process its content to generate RPG-style saga entries (e.g., quest journal format, narrative summaries).
    *   Format these entries and save them into the `runtime/dreamscape_output/` directory. Ensure a clear naming convention for these files (e.g., `saga_CONVO-ID_YYYYMMDD.md`).
3.  **Generate MEMORY_UPDATE Blocks:**
    *   As part of processing each conversation, identify key events, decisions, skill advancements, quest completions, etc., that represent changes or additions to the cumulative lore.
    *   Output these as structured `MEMORY_UPDATE` JSON blocks, as defined by `chronicle_conversations.py`'s prompt template.
    *   These blocks should be saved alongside or within the saga entries, or to a central `dreamscape_memory_log.jsonl` if preferred.
4.  **Maintain Devlog:**
    *   Log progress, including the number of conversations processed, sagas generated, and any errors encountered, to `runtime/devlog/agents/agent-4.md`.

## Loop Protocol:
*   Run periodically to capture new conversations and update the chronicle.
*   Ensure that already-processed conversations are not re-processed unless explicitly instructed or if an update mechanism is in place.

## Point Criteria (Illustrative):
*   **+75 pts** per conversation successfully extracted and processed.
*   **+150 pts** per well-formatted saga entry created.
*   **+100 pts** per valid `MEMORY_UPDATE` block generated and stored.

## Bonus
+150 per completed MEMORY_UPDATE
+300 for multi-thread sagas with merged arcs 