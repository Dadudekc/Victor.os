import React, { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Alert,
  CircularProgress,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { Download, Save } from '@mui/icons-material';

interface ExportOptions {
  format: 'markdown' | 'json';
  startDate: Date | null;
  endDate: Date | null;
  agentId?: string;
  logType?: 'compliance' | 'violation' | 'all';
}

interface Props {
  onExport: (options: ExportOptions) => Promise<void>;
  agents: string[];
}

export const EmpathyExportManager: React.FC<Props> = ({ onExport, agents }) => {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [options, setOptions] = useState<ExportOptions>({
    format: 'markdown',
    startDate: null,
    endDate: null,
    logType: 'all',
  });

  const handleExport = async () => {
    try {
      setLoading(true);
      setError(null);
      await onExport(options);
      setOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export logs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        variant="contained"
        startIcon={<Download />}
        onClick={() => setOpen(true)}
      >
        Export Logs
      </Button>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Export Logs</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box display="flex" flexDirection="column" gap={2} mt={1}>
            <FormControl fullWidth>
              <InputLabel>Format</InputLabel>
              <Select
                value={options.format}
                label="Format"
                onChange={(e) => setOptions(prev => ({
                  ...prev,
                  format: e.target.value as 'markdown' | 'json'
                }))}
              >
                <MenuItem value="markdown">Markdown</MenuItem>
                <MenuItem value="json">JSON</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Log Type</InputLabel>
              <Select
                value={options.logType}
                label="Log Type"
                onChange={(e) => setOptions(prev => ({
                  ...prev,
                  logType: e.target.value as 'compliance' | 'violation' | 'all'
                }))}
              >
                <MenuItem value="all">All Logs</MenuItem>
                <MenuItem value="compliance">Compliance Logs</MenuItem>
                <MenuItem value="violation">Violation Logs</MenuItem>
              </Select>
            </FormControl>

            <FormControl fullWidth>
              <InputLabel>Agent</InputLabel>
              <Select
                value={options.agentId || ''}
                label="Agent"
                onChange={(e) => setOptions(prev => ({
                  ...prev,
                  agentId: e.target.value || undefined
                }))}
              >
                <MenuItem value="">All Agents</MenuItem>
                {agents.map(agent => (
                  <MenuItem key={agent} value={agent}>
                    {agent}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Start Date"
                value={options.startDate}
                onChange={(date) => setOptions(prev => ({
                  ...prev,
                  startDate: date
                }))}
                renderInput={(params) => <TextField {...params} fullWidth />}
              />

              <DatePicker
                label="End Date"
                value={options.endDate}
                onChange={(date) => setOptions(prev => ({
                  ...prev,
                  endDate: date
                }))}
                renderInput={(params) => <TextField {...params} fullWidth />}
              />
            </LocalizationProvider>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            onClick={handleExport}
            variant="contained"
            startIcon={loading ? <CircularProgress size={20} /> : <Save />}
            disabled={loading}
          >
            Export
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}; 