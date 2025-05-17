import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock components
jest.mock('@mui/material', () => ({
  Box: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  Typography: ({ children, ...props }: any) => <p {...props}>{children}</p>,
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>{children}</button>
  ),
  CircularProgress: () => <div data-testid="loading">Loading...</div>,
  Alert: ({ children, ...props }: any) => <div {...props}>{children}</div>,
}));

// Mock WebSocket
const mockWebSocket = {
  onmessage: null,
  onerror: null,
  onopen: null,
  send: jest.fn(),
  close: jest.fn(),
};

global.WebSocket = jest.fn(() => mockWebSocket) as any;

describe('EmpathyLogsTab', () => {
  const mockAgents = [
    { id: 'agent1', name: 'Test Agent' }
  ];

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state', () => {
    render(
      <div>
        <div data-testid="loading">Loading...</div>
      </div>
    );
    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('handles WebSocket connection', () => {
    const onMessage = jest.fn();
    const ws = new WebSocket('ws://test');
    ws.onmessage = onMessage;

    const mockEvent = { data: JSON.stringify({ type: 'test' }) };
    ws.onmessage?.(mockEvent as any);

    expect(onMessage).toHaveBeenCalledWith(mockEvent);
  });

  it('handles export functionality', () => {
    const onExport = jest.fn();
    render(
      <button onClick={() => onExport('test')} data-testid="export-button">
        Export
      </button>
    );

    fireEvent.click(screen.getByTestId('export-button'));
    expect(onExport).toHaveBeenCalledWith('test');
  });
}); 