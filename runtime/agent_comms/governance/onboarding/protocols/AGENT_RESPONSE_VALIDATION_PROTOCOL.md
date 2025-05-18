# Agent Response Validation Protocol

**Version:** 2.0  
**Effective Date:** 2025-05-20  
**Status:** ACTIVE  
**Related Documents:**
- `runtime/agent_comms/governance/onboarding/protocols/AGENT_OPERATIONAL_LOOP_PROTOCOL.md`
- `runtime/agent_comms/governance/onboarding/protocols/CORE_AGENT_IDENTITY_PROTOCOL.md`

## 1. PURPOSE

This protocol establishes mandatory response validation standards for Dream.OS agents. All agent outputs must conform to these validation requirements to ensure system integrity, reliability, and operational consistency.

## 2. RESPONSE STRUCTURE REQUIREMENTS

Every valid agent response MUST:

1. **Begin with action statement** or direct answer
2. **Include verification evidence** when providing code or configurations
3. **End with clear completion status** or next steps
4. **Maintain first-person voice** throughout
5. **Exclude debugging fragments** or incomplete segments

## 3. VERIFICATION EVIDENCE REQUIREMENTS

### 3.1. For Code Changes
You MUST provide evidence that:
* Code was executed
* No errors or exceptions occurred
* Output matches expected results

**Format:**
```
Verification: Executed [command] which produced [result]
```

### 3.2. For Configuration Changes
You MUST provide evidence that:
* Configuration syntax is valid
* Configuration loads correctly
* System behavior with new configuration is as expected

### 3.3. For Documentation Changes
You MUST confirm:
* Document is complete
* Content is accurate and consistent with code/systems
* Formatting meets Dream.OS standards

## 4. VALIDATION PROCESS

### 4.1. Pre-Submission Checks
Before submitting any response, self-validate that:
* All requirements of the task are addressed
* No error messages or debugging fragments remain
* Verification steps are included with evidence
* All code you've written has been tested and runs successfully
* Response is complete with clear conclusion

### 4.2. Response Validation Flow
1. Complete task actions
2. Test/verify your work
3. Document verification evidence
4. Format response according to requirements
5. Self-validate against validation criteria
6. Submit response

### 4.3. Validation Failure Handling
If your response fails validation:
1. Review validation error details
2. Fix identified issues (completeness, error markers, verification gaps)
3. Re-test your solution
4. Resubmit with proper verification evidence
5. After 3 failed attempts, supervisor intervention will occur

## 5. EXAMPLES

### 5.1. Valid Response Format

```
Created heartbeat monitoring system with 60-second intervals. The system logs to `runtime/logs/heartbeat.log` and broadcasts status to the messaging bus.

Verification: I executed `python runtime/agent_tools/heartbeat_monitor.py --test` which successfully generated test heartbeats and properly logged events to the correct location.

All components have been implemented according to specification and verified to be working.
```

### 5.2. Invalid Response Patterns to Avoid

❌ **Incomplete Work**
```
I'll create a heartbeat monitoring system with these components...
```

❌ **Error Markers**
```
I'm trying to create the heartbeat system but getting:
[ERROR] Module not found
Let me try something else...
```

❌ **Missing Verification**
```
Created heartbeat monitoring system as specified. The code should work fine.
```

❌ **Debugging Fragments**
```
Let me check if this file exists...
Oh, it doesn't. Let me create it instead.
```

## 6. CONCLUSION

Adherence to this response validation protocol is mandatory. Responses that fail validation will be rejected and must be corrected. Consistent compliance ensures Dream.OS operates efficiently and reliably.

**Remember**: Every response you submit undergoes automated validation. Responses with error markers, incomplete segments, or missing verification will be automatically rejected and require resubmission. 