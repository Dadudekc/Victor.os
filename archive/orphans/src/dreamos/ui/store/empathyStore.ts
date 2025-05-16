import { devtools, persist } from 'zustand/middleware';

import create from 'zustand';

interface LogEntry {
  id: string;
  timestamp: string;
  type: 'compliance' | 'violation';
  severity: 'low' | 'medium' | 'high';
  content: string;
  agentId: string;
  metrics: {
    loop_duration: number;
    reflection_gap: number;
    task_complexity: number;
    compliance_score: number;
  };
}

interface AgentInsights {
  drift_trend: number;
  compliance_trend: number;
  drift_pattern: string;
  compliance_pattern: string;
  recent_confidence: number;
  prediction_count: number;
}

interface AgentScore {
  agent_id: string;
  score: number;
  status: string;
  summary: string;
  timestamp: string;
}

interface AgentScoreDetailed extends AgentScore {
  metrics: any;
  value_scores: { [key: string]: number };
  frequency: any;
  trend: any;
  recovery: any;
  context: any;
  weighted_components: { [key: string]: number };
}

interface ThresholdStatus {
  timestamp: string;
  status: string;
  average_score: number;
  agents_below_threshold: number;
  critical_agents: Array<{
    agent_id: string;
    score: number;
  }>;
}

interface EmpathyState {
  logs: LogEntry[];
  agents: string[];
  insights: Record<string, AgentInsights>;
  selectedAgent: string | null;
  filters: {
    logType: 'all' | 'compliance' | 'violation';
    severity: ('low' | 'medium' | 'high')[];
    dateRange: [Date | null, Date | null];
  };
  // Actions
  setLogs: (logs: LogEntry[]) => void;
  addLog: (log: LogEntry) => void;
  setAgents: (agents: string[]) => void;
  setInsights: (agentId: string, insights: AgentInsights) => void;
  setSelectedAgent: (agentId: string | null) => void;
  setFilters: (filters: Partial<EmpathyState['filters']>) => void;
  exportLogs: (options: {
    format: 'markdown' | 'json';
    startDate: Date | null;
    endDate: Date | null;
    agentId?: string;
    logType?: 'compliance' | 'violation' | 'all';
  }) => Promise<string>;
}

interface EmpathyStore {
  // Logs
  logs: any[];
  filteredLogs: any[];
  agents: string[];
  loading: boolean;
  error: string | null;
  
  // Scores
  agentScores: AgentScore[];
  selectedAgent: string | null;
  selectedAgentData: AgentScoreDetailed | null;
  thresholdStatus: ThresholdStatus | null;
  scoreLoading: boolean;
  scoreError: string | null;
  
  // Actions
  fetchLogs: () => Promise<void>;
  filterLogs: (searchTerm: string, type: string, severity: string, agent: string) => void;
  fetchAgents: () => Promise<void>;
  exportLogs: (format: string) => Promise<{ content: string; format: string }>;
  
  // Score Actions
  fetchAgentScores: (forceUpdate?: boolean) => Promise<void>;
  fetchAgentDetails: (agentId: string) => Promise<void>;
  fetchThresholdStatus: () => Promise<void>;
  recalculateAgentScore: (agentId: string) => Promise<void>;
}

export const useEmpathyStore = create<EmpathyStore>()(
  devtools(
    persist(
      (set, get) => ({
        // Logs state
        logs: [],
        filteredLogs: [],
        agents: [],
        loading: false,
        error: null,
        
        // Scores state
        agentScores: [],
        selectedAgent: null,
        selectedAgentData: null,
        thresholdStatus: null,
        scoreLoading: false,
        scoreError: null,
        
        // Log Actions
        fetchLogs: async () => {
          try {
            set({ loading: true, error: null });
            const response = await fetch('/api/empathy/logs');
            if (!response.ok) {
              throw new Error('Failed to fetch logs');
            }
            const data = await response.json();
            set({ logs: data, filteredLogs: data, loading: false });
          } catch (err: any) {
            set({ error: err.message, loading: false });
          }
        },
        
        filterLogs: (searchTerm: string, type: string, severity: string, agent: string) => {
          const { logs } = get();
          let filtered = [...logs];
          
          if (searchTerm) {
            filtered = filtered.filter(log => 
              log.content?.toLowerCase().includes(searchTerm.toLowerCase())
            );
          }
          
          if (type !== 'all') {
            filtered = filtered.filter(log => log.type === type);
          }
          
          if (severity !== 'all') {
            filtered = filtered.filter(log => log.severity === severity);
          }
          
          if (agent !== 'all') {
            filtered = filtered.filter(log => log.agent_id === agent);
          }
          
          set({ filteredLogs: filtered });
        },
        
        fetchAgents: async () => {
          try {
            const response = await fetch('/api/empathy/agents');
            if (!response.ok) {
              throw new Error('Failed to fetch agents');
            }
            const data = await response.json();
            set({ agents: data });
          } catch (err: any) {
            console.error('Error fetching agents:', err.message);
          }
        },
        
        exportLogs: async (format: string) => {
          try {
            const { selectedAgent } = get();
            
            const params = new URLSearchParams();
            if (selectedAgent && selectedAgent !== 'all') {
              params.append('agent_id', selectedAgent);
            }
            params.append('format', format);
            
            const response = await fetch(`/api/empathy/logs/export?${params.toString()}`);
            if (!response.ok) {
              throw new Error('Failed to export logs');
            }
            
            return await response.json();
          } catch (err: any) {
            console.error('Error exporting logs:', err.message);
            throw err;
          }
        },
        
        // Score Actions
        fetchAgentScores: async (forceUpdate = false) => {
          try {
            set({ scoreLoading: true, scoreError: null });
            const response = await fetch(`/api/empathy/scores?force_update=${forceUpdate}`);
            if (!response.ok) {
              throw new Error('Failed to fetch agent scores');
            }
            const data = await response.json();
            set({ agentScores: data, scoreLoading: false });
          } catch (err: any) {
            set({ scoreError: err.message, scoreLoading: false });
          }
        },
        
        fetchAgentDetails: async (agentId: string) => {
          try {
            set({ selectedAgent: agentId, scoreLoading: true, scoreError: null });
            const response = await fetch(`/api/empathy/scores/${agentId}`);
            if (!response.ok) {
              throw new Error(`Failed to fetch details for agent ${agentId}`);
            }
            const data = await response.json();
            set({ selectedAgentData: data, scoreLoading: false });
          } catch (err: any) {
            set({ scoreError: err.message, scoreLoading: false });
          }
        },
        
        fetchThresholdStatus: async () => {
          try {
            const response = await fetch('/api/empathy/threshold-status');
            if (!response.ok) {
              throw new Error('Failed to fetch threshold status');
            }
            const data = await response.json();
            set({ thresholdStatus: data });
          } catch (err: any) {
            console.error('Error fetching threshold status:', err.message);
          }
        },
        
        recalculateAgentScore: async (agentId: string) => {
          try {
            set({ scoreLoading: true, scoreError: null });
            const response = await fetch(`/api/empathy/recalculate/${agentId}`, {
              method: 'POST',
            });
            if (!response.ok) {
              throw new Error(`Failed to recalculate score for agent ${agentId}`);
            }
            const data = await response.json();
            
            // Update the selected agent data
            set({ selectedAgentData: data });
            
            // Also update the agent in the agentScores array
            const { agentScores } = get();
            const updatedScores = agentScores.map(agent => 
              agent.agent_id === agentId 
                ? { 
                    agent_id: data.agent_id,
                    score: data.score,
                    status: data.status,
                    summary: data.summary,
                    timestamp: data.timestamp
                  } 
                : agent
            );
            
            set({ agentScores: updatedScores, scoreLoading: false });
            
            // Refresh threshold status
            get().fetchThresholdStatus();
          } catch (err: any) {
            set({ scoreError: err.message, scoreLoading: false });
          }
        }
      }),
      {
        name: 'empathy-storage',
        partialize: (state) => ({
          selectedAgent: state.selectedAgent,
          filters: state.filters,
        }),
      }
    )
  )
);

function generateMarkdown(logs: LogEntry[]): string {
  let markdown = '# Empathy Intelligence Logs\n\n';
  
  for (const log of logs) {
    markdown += `## ${log.timestamp} - ${log.type.toUpperCase()}\n`;
    markdown += `Agent: ${log.agentId}\n`;
    markdown += `Severity: ${log.severity}\n\n`;
    
    markdown += '### Metrics\n';
    for (const [key, value] of Object.entries(log.metrics)) {
      markdown += `- ${key}: ${value}\n`;
    }
    
    markdown += '\n### Content\n';
    markdown += `${log.content}\n\n`;
  }
  
  return markdown;
} 