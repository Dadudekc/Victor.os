# src/dreamos/governance/event_types.py
class EventType:
    ELECTION_START            = "dreamos.governance.election.start"
    DECLARE_CANDIDACY         = "dreamos.governance.election.declare_candidacy"
    AGENT_VOTE                = "dreamos.governance.election.agent_vote"
    CONSENSUS_VOTE_COMPLETED  = "dreamos.consensus.vote.completed"
    ELECTION_RESULT           = "dreamos.governance.election.result" 