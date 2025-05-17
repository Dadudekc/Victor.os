import React, { useEffect, useState, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  Chip,
  Tooltip,
  IconButton,
  Button,
  Menu,
  MenuItem
} from '@mui/material';
import {
  Psychology,
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Info,
  Refresh,
  Download
} from '@mui/icons-material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
} from 'recharts';

interface AgentTrait {
  name: string;
  value: number;
  trend: 'up' | 'down' | 'stable';
  description: string;
  driftScore: number;
  lastUpdated: string;
  confidence: number;
}

interface AgentDNA {
  agentId: string;
  traits: AgentTrait[];
  driftScore: number;
  lastUpdated: string;
  confidence: number;
  behavioralPatterns: {
    name: string;
    frequency: number;
    impact: 'high' | 'medium' | 'low';
    description: string;
  }[];
}

interface Props {
  agentId: string;
  onRefresh?: () => void;
}

export const AgentDNAInspector: React.FC<Props> = ({ agentId, onRefresh }) => {
  const [dna, setDna] = useState<AgentDNA | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [exportMenu, setExportMenu] = useState<null | HTMLElement>(null);

  const connectWebSocket = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/dna/ws/${agentId}`;
    
    const socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
      console.log('WebSocket connected');
      // Subscribe to agent updates
      socket.send(JSON.stringify({
        type: 'subscribe',
        agent_id: agentId
      }));
    };
    
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'agent_dna_update') {
          setDna(data.dna);
          setLoading(false);
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };
    
    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Failed to connect to DNA analysis service');
      setLoading(false);
    };
    
    socket.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt to reconnect after 5 seconds
      setTimeout(connectWebSocket, 5000);
    };
    
    setWs(socket);
  }, [agentId]);

  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [connectWebSocket]);

  const handleRefresh = useCallback(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: 'request_analysis',
        agent_id: agentId
      }));
    }
    if (onRefresh) {
      onRefresh();
    }
  }, [ws, agentId, onRefresh]);

  const handleExport = useCallback(async (format: 'markdown' | 'json') => {
    if (!dna) return;

    try {
      let content: string;
      let filename: string;
      let mimeType: string;

      if (format === 'markdown') {
        content = generateMarkdown(dna);
        filename = `agent_dna_${agentId}_${new Date().toISOString().split('T')[0]}.md`;
        mimeType = 'text/markdown';
      } else {
        content = JSON.stringify(dna, null, 2);
        filename = `agent_dna_${agentId}_${new Date().toISOString().split('T')[0]}.json`;
        mimeType = 'application/json';
      }

      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Error exporting DNA data:', e);
      setError('Failed to export DNA data');
    }
  }, [dna, agentId]);

  const generateMarkdown = (dna: AgentDNA): string => {
    const lines: string[] = [
      `# Agent DNA Analysis Report`,
      `## Agent ID: ${dna.agentId}`,
      `Generated: ${new Date(dna.lastUpdated).toLocaleString()}`,
      ``,
      `## Overall Metrics`,
      `- Drift Score: ${(dna.driftScore * 100).toFixed(1)}%`,
      `- Analysis Confidence: ${(dna.confidence * 100).toFixed(1)}%`,
      ``,
      `## Core Traits`,
      ...dna.traits.map(trait => [
        `### ${trait.name}`,
        `- Value: ${(trait.value * 100).toFixed(1)}%`,
        `- Trend: ${trait.trend}`,
        `- Drift Score: ${(trait.driftScore * 100).toFixed(1)}%`,
        `- Confidence: ${(trait.confidence * 100).toFixed(1)}%`,
        `- Description: ${trait.description}`,
        ``
      ]).flat(),
      `## Behavioral Patterns`,
      ...dna.behavioralPatterns.map(pattern => [
        `### ${pattern.name}`,
        `- Frequency: ${(pattern.frequency * 100).toFixed(1)}%`,
        `- Impact: ${pattern.impact}`,
        `- Description: ${pattern.description}`,
        ``
      ]).flat()
    ];

    return lines.join('\n');
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp color="success" />;
      case 'down':
        return <TrendingDown color="error" />;
      default:
        return <TrendingFlat color="info" />;
    }
  };

  const getImpactColor = (impact: string) => {
    switch (impact) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!dna) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        No DNA data available for this agent
      </Alert>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5" component="h2">
          Agent DNA Analysis
        </Typography>
        <Box>
          <IconButton
            onClick={(e) => setExportMenu(e.currentTarget)}
            color="primary"
            sx={{ mr: 1 }}
            data-testid="export-button"
          >
            <Download />
          </IconButton>
          <IconButton onClick={handleRefresh} color="primary">
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      <Menu
        anchorEl={exportMenu}
        open={Boolean(exportMenu)}
        onClose={() => setExportMenu(null)}
      >
        <MenuItem 
          onClick={() => {
            handleExport('markdown');
            setExportMenu(null);
          }}
          data-testid="export-markdown"
        >
          Export as Markdown
        </MenuItem>
        <MenuItem 
          onClick={() => {
            handleExport('json');
            setExportMenu(null);
          }}
          data-testid="export-json"
        >
          Export as JSON
        </MenuItem>
      </Menu>

      <Grid container spacing={3}>
        {/* Core Traits */}
        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Core Traits
            </Typography>
            <Box height={400}>
              <RadarChart
                width={500}
                height={400}
                data={dna.traits}
                margin={{ top: 20, right: 30, left: 20, bottom: 20 }}
              >
                <PolarGrid />
                <PolarAngleAxis dataKey="name" />
                <PolarRadiusAxis angle={30} domain={[0, 1]} />
                <Radar
                  name="Trait Value"
                  dataKey="value"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.6}
                />
              </RadarChart>
            </Box>
          </Card>
        </Grid>

        {/* Trait Details */}
        <Grid item xs={12} md={6}>
          <Card sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Trait Details
            </Typography>
            {dna.traits.map((trait) => (
              <Box key={trait.name} mb={2}>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="subtitle1">
                    {trait.name}
                  </Typography>
                  <Box display="flex" alignItems="center">
                    <Tooltip title={`Confidence: ${(trait.confidence * 100).toFixed(1)}%`}>
                      <Chip
                        label={`${(trait.value * 100).toFixed(1)}%`}
                        color={trait.driftScore > 0.7 ? 'error' : 'default'}
                        size="small"
                        sx={{ mr: 1 }}
                      />
                    </Tooltip>
                    {getTrendIcon(trait.trend)}
                  </Box>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  {trait.description}
                </Typography>
              </Box>
            ))}
          </Card>
        </Grid>

        {/* Behavioral Patterns */}
        <Grid item xs={12}>
          <Card sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Behavioral Patterns
            </Typography>
            <Grid container spacing={2}>
              {dna.behavioralPatterns.map((pattern) => (
                <Grid item xs={12} sm={6} md={4} key={pattern.name}>
                  <Card variant="outlined" sx={{ p: 2 }}>
                    <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
                      <Typography variant="subtitle1">
                        {pattern.name}
                      </Typography>
                      <Chip
                        label={pattern.impact}
                        color={getImpactColor(pattern.impact)}
                        size="small"
                      />
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {pattern.description}
                    </Typography>
                    <Box mt={1}>
                      <Typography variant="caption" color="text.secondary">
                        Frequency: {(pattern.frequency * 100).toFixed(1)}%
                      </Typography>
                    </Box>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Card>
        </Grid>

        {/* Drift Analysis */}
        <Grid item xs={12}>
          <Card sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Drift Analysis
            </Typography>
            <Box display="flex" alignItems="center" mb={2}>
              <Typography variant="body1" sx={{ mr: 2 }}>
                Overall Drift Score:
              </Typography>
              <Chip
                label={`${(dna.driftScore * 100).toFixed(1)}%`}
                color={dna.driftScore > 0.7 ? 'error' : 'default'}
              />
            </Box>
            <Typography variant="body2" color="text.secondary">
              Last Updated: {new Date(dna.lastUpdated).toLocaleString()}
            </Typography>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}; 