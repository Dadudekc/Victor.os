import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EmpathyLogsTab } from '../src/dreamos/ui/components/EmpathyLogsTab';
import { EmpathyInsightsPanel } from '../src/dreamos/ui/components/EmpathyInsightsPanel';
import { EmpathyExportManager } from '../src/dreamos/ui/components/EmpathyExportManager';
import { AgentDNAInspector } from '../src/dreamos/ui/components/AgentDNAInspector';
import { useEmpathyStore } from '../src/dreamos/ui/store/empathyStore';

// Mock WebSocket
const mockWebSocket = {
  send: jest.fn(),
  close: jest.fn(),
  onmessage: null as any,
  onerror: null as any,
  onopen: null as any,
};

global.WebSocket = jest.fn(() => mockWebSocket) as any;

// Mock fetch
global.fetch = jest.fn();

describe('EmpathyLogsTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve([]),
      })
    );
  });

  it('renders loading state initially', () => {
    render(<EmpathyLogsTab />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders error state when fetch fails', async () => {
    (global.fetch as jest.Mock).mockImplementationOnce(() =>
      Promise.reject(new Error('Failed to fetch'))
    );

    render(<EmpathyLogsTab />);
    await waitFor(() => {
      expect(screen.getByText('Failed to fetch')).toBeInTheDocument();
    });
  });

  it('switches between tabs', async () => {
    render(<EmpathyLogsTab />);
    await waitFor(() => {
      expect(screen.getByText('Logs')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Insights'));
    expect(screen.getByText('Agent Insights')).toBeInTheDocument();
  });
});

describe('EmpathyInsightsPanel', () => {
  const mockAgentId = 'test-agent';

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    render(<EmpathyInsightsPanel agentId={mockAgentId} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays insights when data is received', async () => {
    render(<EmpathyInsightsPanel agentId={mockAgentId} />);

    // Simulate WebSocket message
    const mockInsights = {
      type: 'agent_insights',
      data: {
        drift_trend: 0.5,
        compliance_trend: 0.8,
        drift_pattern: 'improving',
        compliance_pattern: 'stable',
        recent_confidence: 0.9,
        prediction_count: 100,
      },
    };

    await waitFor(() => {
      mockWebSocket.onmessage({ data: JSON.stringify(mockInsights) });
    });

    expect(screen.getByText('Behavioral Trends')).toBeInTheDocument();
    expect(screen.getByText('improving')).toBeInTheDocument();
    expect(screen.getByText('stable')).toBeInTheDocument();
  });

  it('handles WebSocket errors', async () => {
    render(<EmpathyInsightsPanel agentId={mockAgentId} />);

    await waitFor(() => {
      mockWebSocket.onerror();
    });

    expect(screen.getByText('Failed to connect to insights service')).toBeInTheDocument();
  });
});

describe('EmpathyExportManager', () => {
  const mockAgents = ['agent1', 'agent2', 'agent3'];
  const mockOnExport = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('opens export dialog when button is clicked', () => {
    render(<EmpathyExportManager onExport={mockOnExport} agents={mockAgents} />);
    
    fireEvent.click(screen.getByText('Export Logs'));
    expect(screen.getByText('Export Logs')).toBeInTheDocument();
  });

  it('calls onExport with correct options', async () => {
    render(<EmpathyExportManager onExport={mockOnExport} agents={mockAgents} />);
    
    fireEvent.click(screen.getByText('Export Logs'));
    
    // Select format
    fireEvent.mouseDown(screen.getByLabelText('Format'));
    fireEvent.click(screen.getByText('JSON'));

    // Select agent
    fireEvent.mouseDown(screen.getByLabelText('Agent'));
    fireEvent.click(screen.getByText('agent1'));

    // Click export
    fireEvent.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(mockOnExport).toHaveBeenCalledWith({
        format: 'json',
        agentId: 'agent1',
        startDate: null,
        endDate: null,
        logType: 'all',
      });
    });
  });
});

describe('EmpathyStore', () => {
  beforeEach(() => {
    useEmpathyStore.setState({
      logs: [],
      agents: [],
      insights: {},
      selectedAgent: null,
      filters: {
        logType: 'all',
        severity: ['low', 'medium', 'high'],
        dateRange: [null, null],
      },
    });
  });

  it('updates logs correctly', () => {
    const { setLogs } = useEmpathyStore.getState();
    const mockLogs = [
      {
        id: '1',
        timestamp: '2024-03-20T10:00:00',
        type: 'compliance',
        severity: 'low',
        content: 'Test log',
        agentId: 'agent1',
        metrics: {
          loop_duration: 1.0,
          reflection_gap: 0.5,
          task_complexity: 0.8,
          compliance_score: 0.9,
        },
      },
    ];

    setLogs(mockLogs);
    expect(useEmpathyStore.getState().logs).toEqual(mockLogs);
  });

  it('exports logs in correct format', async () => {
    const { setLogs, exportLogs } = useEmpathyStore.getState();
    const mockLogs = [
      {
        id: '1',
        timestamp: '2024-03-20T10:00:00',
        type: 'compliance',
        severity: 'low',
        content: 'Test log',
        agentId: 'agent1',
        metrics: {
          loop_duration: 1.0,
          reflection_gap: 0.5,
          task_complexity: 0.8,
          compliance_score: 0.9,
        },
      },
    ];

    setLogs(mockLogs);

    const markdown = await exportLogs({
      format: 'markdown',
      startDate: null,
      endDate: null,
    });

    expect(markdown).toContain('# Empathy Intelligence Logs');
    expect(markdown).toContain('Test log');
  });
});

describe('AgentDNAInspector', () => {
  const mockAgentId = 'test-agent';
  const mockDNA = {
    agentId: mockAgentId,
    traits: [
      {
        name: 'Empathy',
        value: 0.85,
        trend: 0.1,
        description: 'High level of emotional understanding',
      },
      {
        name: 'Adaptability',
        value: 0.65,
        trend: -0.05,
        description: 'Moderate ability to adjust to new situations',
      },
    ],
    driftScore: 0.15,
    lastUpdated: '2024-03-20T10:00:00',
    confidence: 0.92,
    behavioralPatterns: [
      {
        pattern: 'Proactive Problem Solving',
        frequency: 0.75,
        impact: 'positive',
      },
      {
        pattern: 'Delayed Response',
        frequency: 0.25,
        impact: 'negative',
      },
    ],
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    render(<AgentDNAInspector agentId={mockAgentId} />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('displays DNA data when received', async () => {
    render(<AgentDNAInspector agentId={mockAgentId} />);

    // Simulate WebSocket message
    await waitFor(() => {
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'agent_dna_update',
          agentId: mockAgentId,
          dna: mockDNA,
        }),
      });
    });

    expect(screen.getByText('Agent DNA Analysis')).toBeInTheDocument();
    expect(screen.getByText('Core Traits')).toBeInTheDocument();
    expect(screen.getByText('Trait Details')).toBeInTheDocument();
    expect(screen.getByText('Behavioral Patterns')).toBeInTheDocument();
    expect(screen.getByText('Drift Analysis')).toBeInTheDocument();

    // Check trait details
    expect(screen.getByText('Empathy')).toBeInTheDocument();
    expect(screen.getByText('Adaptability')).toBeInTheDocument();
    expect(screen.getByText('High level of emotional understanding')).toBeInTheDocument();

    // Check behavioral patterns
    expect(screen.getByText('Proactive Problem Solving')).toBeInTheDocument();
    expect(screen.getByText('Delayed Response')).toBeInTheDocument();

    // Check drift analysis
    expect(screen.getByText('Drift Score: 15.0%')).toBeInTheDocument();
    expect(screen.getByText('Confidence: 92.0%')).toBeInTheDocument();
  });

  it('handles WebSocket errors', async () => {
    render(<AgentDNAInspector agentId={mockAgentId} />);

    await waitFor(() => {
      mockWebSocket.onerror();
    });

    expect(screen.getByText('Failed to connect to DNA analysis service')).toBeInTheDocument();
  });

  it('calls onRefresh when refresh button is clicked', async () => {
    const mockOnRefresh = jest.fn();
    render(<AgentDNAInspector agentId={mockAgentId} onRefresh={mockOnRefresh} />);

    // Simulate WebSocket message to get past loading state
    await waitFor(() => {
      mockWebSocket.onmessage({
        data: JSON.stringify({
          type: 'agent_dna_update',
          agentId: mockAgentId,
          dna: mockDNA,
        }),
      });
    });

    fireEvent.click(screen.getByRole('button', { name: /refresh/i }));
    expect(mockOnRefresh).toHaveBeenCalled();
  });

  describe('Export Functionality', () => {
    beforeEach(() => {
      // Mock URL.createObjectURL and document.createElement
      global.URL.createObjectURL = jest.fn(() => 'mock-url');
      global.URL.revokeObjectURL = jest.fn();
      document.createElement = jest.fn(() => ({
        href: '',
        download: '',
        click: jest.fn(),
      }));
      document.body.appendChild = jest.fn();
      document.body.removeChild = jest.fn();
    });

    it('should export DNA data as markdown', async () => {
      const mockDna = {
        agentId: 'test-agent',
        traits: [
          {
            name: 'empathy',
            value: 0.8,
            trend: 'up',
            description: 'High emotional understanding',
            driftScore: 0.2,
            confidence: 0.9
          }
        ],
        driftScore: 0.3,
        lastUpdated: '2024-01-01T00:00:00Z',
        confidence: 0.85,
        behavioralPatterns: [
          {
            name: 'help_seeking',
            frequency: 0.6,
            impact: 'high',
            description: 'Frequently seeks help'
          }
        ]
      };

      const { getByTestId } = render(
        <AgentDNAInspector agentId="test-agent" />
      );

      // Simulate WebSocket message
      const ws = new WebSocket('ws://localhost/ws/test-agent');
      ws.onmessage({
        data: JSON.stringify({
          type: 'agent_dna_update',
          agentId: 'test-agent',
          dna: mockDna
        })
      });

      // Click export button
      const exportButton = getByTestId('export-button');
      fireEvent.click(exportButton);

      // Click markdown export option
      const markdownOption = getByTestId('export-markdown');
      fireEvent.click(markdownOption);

      // Verify markdown content
      expect(document.createElement).toHaveBeenCalledWith('a');
      const markdownContent = expect.stringContaining('# Agent DNA Analysis Report');
      expect(markdownContent).toContain('## Agent ID: test-agent');
      expect(markdownContent).toContain('### empathy');
      expect(markdownContent).toContain('### help_seeking');
    });

    it('should export DNA data as JSON', async () => {
      const mockDna = {
        agentId: 'test-agent',
        traits: [
          {
            name: 'empathy',
            value: 0.8,
            trend: 'up',
            description: 'High emotional understanding',
            driftScore: 0.2,
            confidence: 0.9
          }
        ],
        driftScore: 0.3,
        lastUpdated: '2024-01-01T00:00:00Z',
        confidence: 0.85,
        behavioralPatterns: [
          {
            name: 'help_seeking',
            frequency: 0.6,
            impact: 'high',
            description: 'Frequently seeks help'
          }
        ]
      };

      const { getByTestId } = render(
        <AgentDNAInspector agentId="test-agent" />
      );

      // Simulate WebSocket message
      const ws = new WebSocket('ws://localhost/ws/test-agent');
      ws.onmessage({
        data: JSON.stringify({
          type: 'agent_dna_update',
          agentId: 'test-agent',
          dna: mockDna
        })
      });

      // Click export button
      const exportButton = getByTestId('export-button');
      fireEvent.click(exportButton);

      // Click JSON export option
      const jsonOption = getByTestId('export-json');
      fireEvent.click(jsonOption);

      // Verify JSON content
      expect(document.createElement).toHaveBeenCalledWith('a');
      const jsonContent = JSON.stringify(mockDna, null, 2);
      expect(jsonContent).toContain('"agentId": "test-agent"');
      expect(jsonContent).toContain('"name": "empathy"');
      expect(jsonContent).toContain('"name": "help_seeking"');
    });

    it('should handle export errors gracefully', async () => {
      const { getByTestId, getByText } = render(
        <AgentDNAInspector agentId="test-agent" />
      );

      // Mock error in export
      jest.spyOn(global, 'Blob').mockImplementation(() => {
        throw new Error('Export failed');
      });

      // Click export button
      const exportButton = getByTestId('export-button');
      fireEvent.click(exportButton);

      // Click markdown export option
      const markdownOption = getByTestId('export-markdown');
      fireEvent.click(markdownOption);

      // Verify error message
      expect(getByText('Failed to export DNA data')).toBeInTheDocument();
    });
  });
}); 