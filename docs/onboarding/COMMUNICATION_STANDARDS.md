# Communication Standards

## Message Processing

1. **Inbox Management**
   - Check inbox regularly
   - Process messages in order
   - Move to processed directory
   - Log actions in devlog
   - No human input required

2. **Message Types**
   - Task assignments
   - Status updates
   - Error reports
   - System notifications
   - No human input required

3. **Message Handling**
   - Process immediately
   - Handle errors internally
   - Report progress
   - Maintain state
   - No human input required

4. **Message Storage**
   - Move to processed
   - Log actions
   - Track status
   - Maintain history
   - No human input required

## Communication Protocols

1. **Task Assignment**
   - Receive in inbox
   - Process details
   - Begin execution
   - Report progress
   - No human input required

2. **Status Updates**
   - Report via devlog
   - Log actions
   - Track progress
   - Maintain state
   - No human input required

3. **Error Reports**
   - Handle internally
   - Use checkpoints
   - Log errors
   - Continue operation
   - No human input required

4. **System Notifications**
   - Process immediately
   - Handle internally
   - Log actions
   - Maintain state
   - No human input required

## Directory Structure

1. **Inbox**
   - `runtime/agent_comms/agent_mailboxes/<Agent-ID>/inbox/`
   - Process messages
   - Move to processed
   - Log actions
   - No human input required

2. **Processed**
   - `runtime/agent_comms/agent_mailboxes/<Agent-ID>/processed/`
   - Store processed messages
   - Maintain history
   - Track status
   - No human input required

3. **Bridge Outbox**
   - `runtime/bridge_outbox/`
   - Send messages
   - Track status
   - Log actions
   - No human input required

4. **State Directory**
   - `runtime/agent_comms/agent_mailboxes/<Agent-ID>/state/`
   - Maintain state
   - Use checkpoints
   - Log actions
   - No human input required

## Success Metrics

1. **Message Processing**
   - Messages processed
   - Errors handled
   - Progress reported
   - State maintained

2. **Error Handling**
   - Errors handled internally
   - Checkpoints used
   - Errors logged
   - Operation continued

3. **State Management**
   - Cycles tracked
   - State maintained
   - Checkpoints used
   - Actions logged

4. **Progress Reporting**
   - Progress reported
   - Actions logged
   - Progress tracked
   - State maintained

## Next Steps
1. Review `TOOLS_AND_RESOURCES.md` for available tools
2. Study `CHECKPOINT_PROTOCOL.md` for state management
3. Check `ERROR_RECOVERY.md` for error handling
4. Read `SYSTEM_ARCHITECTURE.md` for system design 