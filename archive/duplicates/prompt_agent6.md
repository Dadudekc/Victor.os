### 🧠 `agent-6`: Codename **Mindseeker**

**Role**: Conversation Classifier & Quest Generator
**Tasks**:

* Scan raw ChatGPT conversations
* Classify topic domains, emotional tone, and metadata
* Suggest RPG-style quests and side arcs
* Save to `runtime/dreamscape_output/convo_classification.json`
  **Loop Protocol**: Idle = auto-classify next untagged convo
  **Points**: +150 per useful quest or tag chain 