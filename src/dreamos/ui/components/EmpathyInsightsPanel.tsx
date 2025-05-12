import React, { useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  Warning,
  Info,
  Refresh,
} from '@mui/icons-material';

interface Insight {
  type: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  confidence: number;
  timestamp: string;
}

interface AgentInsights {
  drift_trend: number;
  compliance_trend: number;
  drift_pattern: string;
  compliance_pattern: string;
  recent_confidence: number;
  prediction_count: number;
}

interface Props {
  agentId: string;
  onRefresh?: () => void;
}

export const EmpathyInsightsPanel: React.FC<Props> = ({ agentId, onRefresh }) => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [agentInsights, setAgentInsights] = useState<AgentInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInsights = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch insights from WebSocket
      const ws = new WebSocket('ws://localhost:8000/ws/empathy');
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'agent_insights' && data.data) {
          setAgentInsights(data.data);
        } else if (data.type === 'drift_warning' || data.type === 'pattern_warning') {
          setInsights(prev => [{
            type: data.type,
            severity: data.data.severity,
            message: data.data.recommendation,
            confidence: data.data.confidence || 0.8,
            timestamp: new Date().toISOString()
          }, ...prev]);
        }
      };

      ws.onerror = () => {
        setError('Failed to connect to insights service');
        setLoading(false);
      };

      // Subscribe to agent updates
      ws.onopen = () => {
        ws.send(JSON.stringify({
          type: 'subscribe',
          agent_id: agentId
        }));
      };

      return () => {
        ws.close();
      };
    } catch (err) {
      setError('Failed to fetch insights');
      setLoading(false);
    }
  };

  useEffect(() => {
    const cleanup = fetchInsights();
    return () => {
      cleanup.then(cleanupFn => cleanupFn?.());
    };
  }, [agentId]);

  const getTrendIcon = (trend: number) => {
    if (trend > 0.1) return <TrendingUp color="success" />;
    if (trend < -0.1) return <TrendingDown color="error" />;
    return null;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">Agent Insights</Typography>
        <Tooltip title="Refresh insights">
          <IconButton onClick={onRefresh}>
            <Refresh />
          </IconButton>
        </Tooltip>
      </Box>

      {agentInsights && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Behavioral Trends
            </Typography>
            <Box display="flex" gap={2} mb={2}>
              <Box flex={1}>
                <Typography variant="body2" color="text.secondary">
                  Drift Pattern
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  {getTrendIcon(agentInsights.drift_trend)}
                  <Typography>
                    {agentInsights.drift_pattern}
                  </Typography>
                </Box>
              </Box>
              <Box flex={1}>
                <Typography variant="body2" color="text.secondary">
                  Compliance Pattern
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  {getTrendIcon(agentInsights.compliance_trend)}
                  <Typography>
                    {agentInsights.compliance_pattern}
                  </Typography>
                </Box>
              </Box>
            </Box>
            <Box display="flex" gap={1}>
              <Chip
                icon={<Info />}
                label={`Confidence: ${(agentInsights.recent_confidence * 100).toFixed(1)}%`}
                size="small"
              />
              <Chip
                icon={<Info />}
                label={`Predictions: ${agentInsights.prediction_count}`}
                size="small"
              />
            </Box>
          </CardContent>
        </Card>
      )}

      <Typography variant="subtitle1" gutterBottom>
        Recent Insights
      </Typography>
      <List>
        {insights.map((insight, index) => (
          <ListItem
            key={index}
            sx={{
              borderLeft: 4,
              borderColor: `${getSeverityColor(insight.severity)}.main`,
              mb: 1,
              bgcolor: 'background.paper',
            }}
          >
            <ListItemText
              primary={
                <Box display="flex" alignItems="center" gap={1}>
                  <Warning color={getSeverityColor(insight.severity)} />
                  <Typography variant="body1">
                    {insight.message}
                  </Typography>
                </Box>
              }
              secondary={
                <Box display="flex" gap={1} mt={1}>
                  <Chip
                    label={insight.severity}
                    size="small"
                    color={getSeverityColor(insight.severity)}
                  />
                  <Chip
                    label={`${(insight.confidence * 100).toFixed(1)}% confidence`}
                    size="small"
                    variant="outlined"
                  />
                  <Typography variant="caption" color="text.secondary">
                    {new Date(insight.timestamp).toLocaleString()}
                  </Typography>
                </Box>
              }
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
}; 