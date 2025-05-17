import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmpathyLogsTab from '../../src/ui/components/EmpathyLogsTab'; // Adjusted import path

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onclose: (() => void) | null = null;
  send = jest.fn();
  close = jest.fn();
}

global.WebSocket = MockWebSocket as any;

// Mock fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    json: () => Promise.resolve([]),
  })
) as jest.Mock;

describe('EmpathyLogsTab', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(<EmpathyLogsTab />);
    expect(screen.getByText('Search Logs')).toBeInTheDocument();
  });

  it('handles WebSocket connection', async () => {
    render(<EmpathyLogsTab />);
    
    // Simulate WebSocket connection
    const ws = new WebSocket('ws://localhost:8000/ws/empathy');
    ws.onopen?.();
    
    await waitFor(() => {
      expect(screen.getByRole('button')).toHaveAttribute('color', 'success');
    });
  });

  it('handles log updates via WebSocket', async () => {
    render(<EmpathyLogsTab />);
    
    const ws = new WebSocket('ws://localhost:8000/ws/empathy');
    ws.onopen?.();
    
    // Simulate log update
    const logUpdate = {
      type: 'log_update',
      timestamp: new Date().toISOString(),
      log_type: 'compliance',
      severity: 'high',
      agent_id: 'test_agent',
      content: 'Test log content',
      drift_warning: {
        type: 'drift_warning',
        agent_id: 'test_agent',
        severity: 'high',
        metrics: {
          drift_score: -0.8,
          compliance_probability: 0.3,
          confidence: 0.9
        },
        recommendation: 'Test recommendation'
      }
    };
    
    ws.onmessage?.({ data: JSON.stringify(logUpdate) } as any);
    
    await waitFor(() => {
      expect(screen.getByText('Test log content')).toBeInTheDocument();
      expect(screen.getByText('Drift Detected: test_agent')).toBeInTheDocument();
    });
  });

  it('filters logs correctly', async () => {
    render(<EmpathyLogsTab />);
    
    // Set type filter
    const typeFilter = screen.getByLabelText('Type');
    fireEvent.change(typeFilter, { target: { value: 'compliance' } });
    
    // Set severity filter
    const severityFilter = screen.getByLabelText('Severity');
    fireEvent.change(severityFilter, { target: { value: 'high' } });
    
    // Set search term
    const searchInput = screen.getByLabelText('Search Logs');
    fireEvent.change(searchInput, { target: { value: 'test' } });
    
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/empathy/logs');
    });
  });

  it('handles export functionality', async () => {
    render(<EmpathyLogsTab />);
    
    // Click export button
    const exportButton = screen.getByTitle('Export');
    fireEvent.click(exportButton);
    
    // Click export option
    const exportOption = screen.getByText('Export as Markdown');
    fireEvent.click(exportOption);
    
    // Verify download was triggered
    await waitFor(() => {
      expect(document.createElement).toHaveBeenCalledWith('a');
    });
  });

  it('displays agent insights correctly', async () => {
    render(<EmpathyLogsTab />);
    
    const ws = new WebSocket('ws://localhost:8000/ws/empathy');
    ws.onopen?.();
    
    // Simulate agent insights update
    const insightsUpdate = {
      type: 'log_update',
      agent_id: 'test_agent',
      agent_insights: {
        key_metrics: {
          compliance_rate: 0.8,
          response_time: 0.5,
          reflection_depth: 0.9
        },
        trends: {
          compliance: 'improving',
          response_time: 'stable'
        },
        recommendations: ['Test recommendation 1', 'Test recommendation 2']
      }
    };
    
    ws.onmessage?.({ data: JSON.stringify(insightsUpdate) } as any);
    
    await waitFor(() => {
      expect(screen.getByText('Agent Insights')).toBeInTheDocument();
      expect(screen.getByText('test_agent')).toBeInTheDocument();
      expect(screen.getByText('Test recommendation 1')).toBeInTheDocument();
    });
  });

  it('handles tab switching', () => {
    render(<EmpathyLogsTab />);
    
    // Switch to Analytics tab
    const analyticsTab = screen.getByText('Analytics');
    fireEvent.click(analyticsTab);
    
    expect(screen.getByText('Compliance Rate Over Time')).toBeInTheDocument();
  });

  it('handles WebSocket disconnection', async () => {
    render(<EmpathyLogsTab />);
    
    const ws = new WebSocket('ws://localhost:8000/ws/empathy');
    ws.onopen?.();
    
    // Simulate disconnection
    ws.onclose?.();
    
    await waitFor(() => {
      expect(screen.getByRole('button')).toHaveAttribute('color', 'error');
    });
    
    // Verify reconnection attempt
    await waitFor(() => {
      expect(screen.getByRole('button')).toHaveAttribute('color', 'success');
    }, { timeout: 6000 });
  });
}); 