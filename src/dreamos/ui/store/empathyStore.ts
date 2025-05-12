import create from 'zustand';
import { devtools, persist } from 'zustand/middleware';

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

export const useEmpathyStore = create<EmpathyState>()(
  devtools(
    persist(
      (set, get) => ({
        logs: [],
        agents: [],
        insights: {},
        selectedAgent: null,
        filters: {
          logType: 'all',
          severity: ['low', 'medium', 'high'],
          dateRange: [null, null],
        },

        setLogs: (logs) => set({ logs }),
        addLog: (log) => set((state) => ({ logs: [log, ...state.logs] })),
        setAgents: (agents) => set({ agents }),
        setInsights: (agentId, insights) =>
          set((state) => ({
            insights: { ...state.insights, [agentId]: insights },
          })),
        setSelectedAgent: (agentId) => set({ selectedAgent: agentId }),
        setFilters: (filters) =>
          set((state) => ({
            filters: { ...state.filters, ...filters },
          })),

        exportLogs: async (options) => {
          const { logs } = get();
          const {
            format,
            startDate,
            endDate,
            agentId,
            logType,
          } = options;

          // Filter logs based on options
          let filteredLogs = logs;
          if (agentId) {
            filteredLogs = filteredLogs.filter((log) => log.agentId === agentId);
          }
          if (logType && logType !== 'all') {
            filteredLogs = filteredLogs.filter((log) => log.type === logType);
          }
          if (startDate) {
            filteredLogs = filteredLogs.filter(
              (log) => new Date(log.timestamp) >= startDate
            );
          }
          if (endDate) {
            filteredLogs = filteredLogs.filter(
              (log) => new Date(log.timestamp) <= endDate
            );
          }

          if (format === 'markdown') {
            return generateMarkdown(filteredLogs);
          } else {
            return JSON.stringify(filteredLogs, null, 2);
          }
        },
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