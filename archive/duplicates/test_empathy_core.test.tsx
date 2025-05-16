import { render, screen, fireEvent } from '@testing-library/react';
import { EmpathyStore } from '../src/dreamos/ui/stores/empathyStore';

describe('EmpathyStore', () => {
  let store: EmpathyStore;

  beforeEach(() => {
    store = new EmpathyStore();
  });

  test('initializes with empty logs', () => {
    expect(store.logs).toEqual([]);
  });

  test('updates logs correctly', () => {
    const newLogs = [
      { id: '1', timestamp: new Date().toISOString(), content: 'Test log 1' },
      { id: '2', timestamp: new Date().toISOString(), content: 'Test log 2' }
    ];

    store.updateLogs(newLogs);
    expect(store.logs).toEqual(newLogs);
  });

  test('exports logs in correct format', () => {
    const logs = [
      { id: '1', timestamp: '2024-01-01T00:00:00Z', content: 'Test log 1' },
      { id: '2', timestamp: '2024-01-01T00:01:00Z', content: 'Test log 2' }
    ];

    store.updateLogs(logs);
    const exported = store.exportLogs('markdown');
    
    expect(exported).toContain('# Empathy Logs Export');
    expect(exported).toContain('Test log 1');
    expect(exported).toContain('Test log 2');
  });
}); 