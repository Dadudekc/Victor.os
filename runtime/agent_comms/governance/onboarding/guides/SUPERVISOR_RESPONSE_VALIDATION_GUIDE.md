# Supervisor's Guide to Agent Response Validation

**Version:** 2.0  
**Effective Date:** 2025-05-20  
**Status:** ACTIVE  
**Related Documents:**
- `docs/agents/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `docs/agents/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`

## 1. PURPOSE

This guide equips Dream.OS supervisors with standardized methods to validate, monitor, and enforce agent response quality. It establishes consistent validation frameworks to ensure all agent outputs meet system requirements and maintain operational integrity.

## 2. VALID AGENT RESPONSE CRITERIA

### 2.1. Core Validation Requirements

| Criterion | Description | Validation Method |
|-----------|-------------|-------------------|
| **Completeness** | Response addresses all aspects of the task or query | Content analysis against task definition |
| **Correctness** | Information provided is accurate and solutions work as intended | Functional testing of code/configurations |
| **Execution Proof** | Evidence that agent has run/tested their solution | Verification steps or test outputs |
| **Format Compliance** | Adherence to required structural formats | Schema validation |
| **Error-Free** | No error messages or debug artifacts | Pattern matching for error markers |

### 2.2. Response Structure Requirements

Every valid agent response must:

1. **Begin with action statement** or direct answer
2. **Include verification evidence** when providing code or configurations
3. **End with clear completion status** or next steps
4. **Maintain consistent voice** throughout
5. **Exclude debugging fragments** or incomplete segments

### 2.3. Examples of Valid vs. Invalid Responses

**VALID RESPONSE:**
```
Created heartbeat monitoring system with 60-second intervals. The system logs to `runtime/logs/heartbeat.log` and broadcasts status to the messaging bus.

Verification: Executed `python runtime/agent_tools/heartbeat_monitor.py --test` which successfully generated test heartbeats and properly logged events.

All components implemented according to specification.
```

**INVALID RESPONSE:**
```
I'm going to create a heartbeat monitoring system.

First, let me check the existing code...
[ERROR] File not found
Let me try a different approach...

Here's the code I would write:
```

## 3. DETECTION METHODOLOGY

### 3.1. Automated Detection

The `CursorAgentResponseMonitor` system automatically checks agent responses for:

1. **Minimum completeness thresholds**
   * Response length relative to query complexity
   * Coverage of specified requirements
   * Presence of all required response components

2. **Error markers**
   * Pattern matching for error strings (`Error:`, `Exception:`, etc.)
   * Incomplete code blocks or missing syntax elements
   * Debug statements or tracebacks

3. **Verification gaps**
   * Missing test/run evidence
   * Unverified functionality claims
   * Lack of execution confirmation

### 3.2. Manual Detection Guidelines

When reviewing agent responses manually, apply this checklist:

- [ ] Response directly addresses the query/task
- [ ] All steps are complete (no "to-do" items)
- [ ] Evidence of testing/execution is included
- [ ] No fragmentary content or unresolved errors
- [ ] Proper format and structure maintained
- [ ] Verification steps are clear and replicable
- [ ] No hallucinated files, functions, or paths

### 3.3. Common Failure Patterns

| Pattern | Indicators | Corrective Action |
|---------|------------|-------------------|
| **Task Abandonment** | Incomplete work, no conclusion | Reset agent and reassign task |
| **Hallucination** | References non-existent resources | Provide explicit file list and paths |
| **Tool Loop** | Repeated identical tool calls | Interrupt with parameter correction |
| **Verification Skip** | Claims success without evidence | Require explicit test execution |
| **Context Drift** | Response unrelated to task | Restore operational context |

## 4. ESCALATION FRAMEWORK

### 4.1. Progressive Intervention Ladder

1. **Level 1: Automated Retry**
   * System detects invalid response
   * Agent receives standardized validation failure message
   * Agent given opportunity to self-correct (max 3 attempts)

2. **Level 2: Supervisor Notice**
   * After 3 failed attempts, supervisor is notified
   * Supervisor reviews response and validation failures
   * Supervisor issues direct correction guidance

3. **Level 3: Contextual Reset**
   * Persistent failures trigger agent context reset
   * Agent operational loop reinitialized
   * Task reassigned or modified

4. **Level 4: System Intervention**
   * Pattern of failures across multiple tasks
   * Full agent redeployment with updated protocols
   * System-level review of affected workflows

### 4.2. Intervention Commands

```bash
# Reset retry counter for specific agent
python runtime/tools/supervisor.py reset-retries --agent=Agent-1

# Force validation on latest response
python runtime/tools/supervisor.py validate --agent=Agent-1 --force

# Reinitialize agent context
python runtime/tools/supervisor.py reset-context --agent=Agent-1

# Emergency halt of agent operations
python runtime/tools/supervisor.py pause --agent=Agent-1 --reason="Critical validation failures"
```

### 4.3. Documentation Requirements

For each escalation beyond Level 1:

1. Record the initial validation failure details
2. Document intervention actions taken
3. Track agent response to intervention
4. Note any system adjustments made
5. Log resolution outcome

## 5. VALIDATION WORKFLOWS

### 5.1. Daily Monitoring Routine

1. **Fleet Status Review**
   * Check `runtime/status/fleet_response_status.json`
   * Review overall validation metrics
   * Identify agents with high failure rates

2. **Sample Validation**
   * Randomly select and manually validate 3-5 agent responses
   * Compare manual results with automated validation
   * Calibrate validation thresholds if needed

3. **Escalation Management**
   * Address any pending Level 2+ escalations
   * Follow up on previous day's interventions
   * Document all intervention outcomes

### 5.2. Response Validation Checklist

**Standard Validation Protocol:**

- [ ] **Pre-Check**: Verify agent is operating within proper loop context
- [ ] **Content Analysis**: Evaluate response against task requirements
- [ ] **Verification Check**: Confirm solution testing evidence
- [ ] **Error Scan**: Check for error markers or incomplete segments
- [ ] **Format Compliance**: Verify structural requirements met
- [ ] **Post-Check**: Confirm agent returned to proper operational loop

### 5.3. Batch Processing

For system-wide validation review:

```bash
# Generate validation report for all agents
python runtime/tools/supervisor.py report --period=24h --output=report.md

# Identify agents with highest failure rates
python runtime/tools/supervisor.py rank --metric=validation_failures --top=5

# Bulk reset for system updates
python runtime/tools/supervisor.py bulk-operation --operation=reset-retry --filter=all
```

## 6. METRICS & MONITORING

### 6.1. Key Performance Indicators

| Metric | Healthy Range | Warning Threshold | Critical Threshold |
|--------|---------------|-------------------|-------------------|
| Fleet Success Rate | >95% | 85-95% | <85% |
| Retry Rate | <5% | 5-15% | >15% |
| Escalation Count | <1/day | 1-3/day | >3/day |
| Agent Recovery Rate | >90% | 75-90% | <75% |
| Validation Latency | <30sec | 30-60sec | >60sec |

### 6.2. Status Dashboards

1. **Fleet Status Dashboard**
   * `runtime/status/fleet_response_status.json`
   * Overall system health metrics
   * Historical validation trends

2. **Individual Agent Dashboards**
   * `runtime/status/agent_response_status_{agent_id}.json`
   * Per-agent validation history
   * Detailed failure reports

### 6.3. Alert Configuration

Configure alerts for:

1. Multiple consecutive failures by same agent
2. Fleet validation success rate dropping below 90%
3. More than 3 escalations in 24-hour period
4. Any critical threshold breach lasting >3 hours

## 7. SYSTEM MAINTENANCE

### 7.1. Validation Engine Updates

1. **Regular Testing**
   * Run test suite against validation engine weekly
   * Verify against known good/bad responses
   * Update pattern matching for emerging error types

2. **Configuration Management**
   * Store validation rules in `runtime/config/validation_rules.json`
   * Version control all rule changes
   * Document rationale for threshold adjustments

### 7.2. Log Management

1. **Validation Logs**
   * Stored in `runtime/logs/validation/`
   * Rotate logs weekly
   * Archive after 30 days

2. **Audit Reports**
   * Generate monthly validation audit
   * Track trends in failure types
   * Use to inform protocol updates

## 8. AGENT PROTOCOL REFERENCE

Agents are expected to adhere to these protocols:

### 8.1. Response Generation Protocol

1. **Pre-Execution Review**
   * Verify task understanding
   * Confirm available tools and resources
   * Plan verification approach

2. **Execution Phase**
   * Complete all required actions
   * Document progress
   * Test intermediate steps

3. **Verification Phase**
   * Execute solution to verify functionality
   * Document exact verification steps
   * Capture verification output

4. **Finalization**
   * Summarize results
   * Confirm all requirements met
   * Return to operational loop

### 8.2. Self-Verification Requirements

Agents must perform these verification steps:

1. For code changes:
   * Run/execute the created/modified code
   * Ensure no syntax errors or runtime exceptions
   * Verify expected functionality

2. For configuration changes:
   * Validate syntax
   * Test configuration loading
   * Verify system behavior with new configuration

3. For documentation:
   * Review for completeness
   * Verify consistency with code/systems
   * Confirm formatting compliance

## 9. CONCLUSION

Consistent agent response validation is critical to Dream.OS stability and performance. By implementing this supervision framework, you ensure reliable agent operations, minimize drift, and maintain system integrity.

Regular review of validation patterns often reveals opportunities for system-wide improvements. Use the data gathered through this process to continuously refine agent protocols and training.

---

**Important**: This guide should be reviewed and updated quarterly or whenever significant changes are made to the agent protocol stack. 