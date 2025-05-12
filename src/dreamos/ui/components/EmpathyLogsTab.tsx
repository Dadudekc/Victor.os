import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Grid,
  Tooltip,
  Tabs,
  Tab,
  Button,
  Menu,
  Alert,
  AlertTitle,
  CircularProgress,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  FilterList as FilterIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  SwapHoriz as SwapHorizIcon,
  Download as DownloadIcon,
  MoreVert as MoreVertIcon,
  TrendingDown as TrendingDownIcon,
  Timeline as TimelineIcon,
  Psychology as PsychologyIcon,
  Insights as InsightsIcon
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { EmpathyInsightsPanel } from './EmpathyInsightsPanel';
import { EmpathyExportManager } from './EmpathyExportManager';
import { AgentDNAInspector } from './AgentDNAInspector';
import { useEmpathyStore } from '../store/empathyStore';

interface DriftWarning {
  type: 'drift_warning' | 'pattern_warning';
  agent_id: string;
  severity: 'high' | 'medium' | 'low';
  metrics?: {
    mean_compliance: number;
    compliance_std: number;
    trend: number;
  };
  violation_type?: string;
  count?: number;
  recommendation: string;
}

interface CompliancePrediction {
  predicted_compliance: number;
  confidence: number;
  trend: number;
  warning: string | null;
}

interface LogEntry {
  timestamp: string;
  type: 'violation' | 'compliance' | 'identity';
  severity?: 'low' | 'medium' | 'high' | 'critical';
  content: string;
  agent_id?: string;
  drift_warning?: DriftWarning;
  compliance_prediction?: CompliancePrediction;
}

interface EmpathyLogsTabProps {
  onRefresh?: () => void;
}

interface AgentAnalytics {
  id: string;
  complianceRate: number;
  violationsByType: { [key: string]: number };
  timeline: Array<{
    date: string;
    compliance: number;
    total: number;
  }>;
}

interface AgentInsights {
  key_metrics: { [key: string]: number };
  trends: { [key: string]: string };
  recommendations: string[];
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`empathy-tabpanel-${index}`}
      aria-labelledby={`empathy-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const EmpathyLogsTab: React.FC<EmpathyLogsTabProps> = ({ onRefresh }) => {
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<LogEntry[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [activeTab, setActiveTab] = useState(0);
  const [wsConnected, setWsConnected] = useState(false);
  const [complianceData, setComplianceData] = useState<any[]>([]);
  const [violationData, setViolationData] = useState<any[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [agentAnalytics, setAgentAnalytics] = useState<AgentAnalytics[]>([]);
  const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const [driftWarnings, setDriftWarnings] = useState<DriftWarning[]>([]);
  const [predictions, setPredictions] = useState<CompliancePrediction[]>([]);
  const [agentInsights, setAgentInsights] = useState<{ [key: string]: AgentInsights }>({});

  const {
    exportLogs,
  } = useEmpathyStore();

  // WebSocket connection
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/empathy');
    
    ws.onopen = () => {
      setWsConnected(true);
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'log_update') {
        // Update logs
        setLogs(prevLogs => {
          const newLogs = [...prevLogs];
          const index = newLogs.findIndex(log => log.timestamp === data.timestamp);
          
          if (index >= 0) {
            newLogs[index] = data;
          } else {
            newLogs.unshift(data);
          }
          
          return newLogs.slice(0, 100); // Keep last 100 logs
        });
        
        // Update drift warnings
        if (data.drift_warning) {
          setDriftWarnings(prev => {
            const newWarnings = [...prev];
            const index = newWarnings.findIndex(w => w.agent_id === data.drift_warning.agent_id);
            
            if (index >= 0) {
              newWarnings[index] = data.drift_warning;
            } else {
              newWarnings.push(data.drift_warning);
            }
            
            return newWarnings;
          });
        }
        
        // Update predictions
        if (data.compliance_prediction) {
          setPredictions(prev => {
            const newPredictions = [...prev];
            const index = newPredictions.findIndex(p => p.agent_id === data.agent_id);
            
            if (index >= 0) {
              newPredictions[index] = data.compliance_prediction;
            } else {
              newPredictions.push(data.compliance_prediction);
            }
            
            return newPredictions;
          });
        }
        
        // Update agent insights
        if (data.agent_insights) {
          setAgentInsights(prev => ({
            ...prev,
            [data.agent_id]: data.agent_insights
          }));
        }
      }
    };
    
    ws.onclose = () => {
      setWsConnected(false);
      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        setWsConnected(true);
      }, 5000);
    };
    
    return () => {
      ws.close();
    };
  }, []);

  // Initial data fetch
  useEffect(() => {
    fetchLogs();
  }, []);

  // Update filtered logs when filters change
  useEffect(() => {
    filterLogs();
  }, [logs, searchTerm, typeFilter, severityFilter, agentFilter]);

  // Update compliance data
  useEffect(() => {
    updateComplianceData();
  }, [logs]);

  // Fetch available agents
  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const response = await fetch('/api/empathy/agents');
        const data = await response.json();
        setAgents(data);
      } catch (error) {
        console.error('Failed to fetch agents:', error);
      }
    };
    fetchAgents();
  }, []);

  // Update agent analytics
  useEffect(() => {
    updateAgentAnalytics();
  }, [logs, selectedAgent]);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/empathy/logs');
      const data = await response.json();
      setLogs(data);

      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch empathy logs:', error);
      setError(error instanceof Error ? error.message : 'Failed to fetch data');
      setLoading(false);
    }
  };

  const filterLogs = () => {
    let filtered = [...logs];

    if (typeFilter !== 'all') {
      filtered = filtered.filter(log => log.type === typeFilter);
    }

    if (severityFilter !== 'all') {
      filtered = filtered.filter(log => log.severity === severityFilter);
    }

    if (agentFilter !== 'all') {
      filtered = filtered.filter(log => log.agent_id === agentFilter);
    }

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(log =>
        log.content.toLowerCase().includes(term) ||
        log.agent_id?.toLowerCase().includes(term)
      );
    }

    setFilteredLogs(filtered);
  };

  const updateComplianceData = () => {
    // Process logs for compliance chart
    const complianceByDay = new Map();
    const violationsByType = new Map();
    
    logs.forEach(log => {
      const date = new Date(log.timestamp).toLocaleDateString();
      
      if (log.type === 'compliance') {
        const current = complianceByDay.get(date) || { date, compliance: 0, total: 0 };
        current.total += 1;
        if (log.content.includes('✅')) {
          current.compliance += 1;
        }
        complianceByDay.set(date, current);
      }
      
      if (log.type === 'violation') {
        const type = log.content.split('—')[1]?.trim() || 'unknown';
        violationsByType.set(type, (violationsByType.get(type) || 0) + 1);
      }
    });
    
    setComplianceData(Array.from(complianceByDay.values()));
    setViolationData(
      Array.from(violationsByType.entries()).map(([type, count]) => ({
        type,
        count
      }))
    );
  };

  const updateAgentAnalytics = () => {
    const analytics: { [key: string]: AgentAnalytics } = {};
    
    logs.forEach(log => {
      const agentId = log.agent_id || 'system';
      if (!analytics[agentId]) {
        analytics[agentId] = {
          id: agentId,
          complianceRate: 0,
          violationsByType: {},
          timeline: []
        };
      }
      
      const date = new Date(log.timestamp).toLocaleDateString();
      
      if (log.type === 'compliance') {
        const timelineEntry = analytics[agentId].timeline.find(t => t.date === date) || {
          date,
          compliance: 0,
          total: 0
        };
        timelineEntry.total += 1;
        if (log.content.includes('✅')) {
          timelineEntry.compliance += 1;
        }
        if (!analytics[agentId].timeline.find(t => t.date === date)) {
          analytics[agentId].timeline.push(timelineEntry);
        }
      }
      
      if (log.type === 'violation') {
        const type = log.content.split('—')[1]?.trim() || 'unknown';
        analytics[agentId].violationsByType[type] = (analytics[agentId].violationsByType[type] || 0) + 1;
      }
    });
    
    // Calculate compliance rates
    Object.values(analytics).forEach(agent => {
      const totalActions = agent.timeline.reduce((sum, day) => sum + day.total, 0);
      const compliantActions = agent.timeline.reduce((sum, day) => sum + day.compliance, 0);
      agent.complianceRate = totalActions > 0 ? (compliantActions / totalActions) * 100 : 0;
    });
    
    setAgentAnalytics(Object.values(analytics));
  };

  const getSeverityColor = (severity?: string) => {
    switch (severity) {
      case 'critical':
        return '#d32f2f';
      case 'high':
        return '#f57c00';
      case 'medium':
        return '#fbc02d';
      case 'low':
        return '#7cb342';
      default:
        return '#757575';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'violation':
        return <WarningIcon color="error" />;
      case 'compliance':
        return <CheckCircleIcon color="success" />;
      case 'identity':
        return <SwapHorizIcon color="primary" />;
      default:
        return null;
    }
  };

  const renderComplianceChart = () => (
    <Box sx={{ height: 300, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Compliance Rate Over Time
      </Typography>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={complianceData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Line
            type="monotone"
            dataKey="compliance"
            stroke="#4caf50"
            name="Compliant Actions"
          />
          <Line
            type="monotone"
            dataKey="total"
            stroke="#2196f3"
            name="Total Actions"
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  );

  const renderViolationChart = () => (
    <Box sx={{ height: 300, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Violations by Type
      </Typography>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={violationData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="type" />
          <YAxis />
          <RechartsTooltip />
          <Legend />
          <Bar dataKey="count" fill="#f44336" name="Number of Violations" />
        </BarChart>
      </ResponsiveContainer>
    </Box>
  );

  const handleExport = async (options: any) => {
    const content = await exportLogs(options);
    
    // Create and download file
    const blob = new Blob([content], {
      type: options.format === 'markdown' ? 'text/markdown' : 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `empathy-logs-${new Date().toISOString()}.${options.format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderAgentAnalytics = () => (
    <Box>
      <FormControl sx={{ mb: 2 }}>
        <InputLabel>Agent</InputLabel>
        <Select
          value={selectedAgent}
          label="Agent"
          onChange={(e) => setSelectedAgent(e.target.value)}
        >
          <MenuItem value="all">All Agents</MenuItem>
          {agents.map(agent => (
            <MenuItem key={agent} value={agent}>{agent}</MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedAgent === 'all' ? (
        <Grid container spacing={2}>
          {agentAnalytics.map(agent => (
            <Grid item xs={12} md={6} key={agent.id}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="h6">{agent.id}</Typography>
                <Typography>Compliance Rate: {agent.complianceRate.toFixed(1)}%</Typography>
                <ResponsiveContainer width="100%" height={200}>
                  <RadarChart data={Object.entries(agent.violationsByType).map(([type, count]) => ({
                    type,
                    count
                  }))}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="type" />
                    <PolarRadiusAxis />
                    <Radar
                      name="Violations"
                      dataKey="count"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.6}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </Paper>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Box>
          {renderComplianceChart()}
          {renderViolationChart()}
        </Box>
      )}
    </Box>
  );

  const renderDriftWarnings = () => {
    if (driftWarnings.length === 0) return null;
    
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
          <PsychologyIcon sx={{ mr: 1 }} />
          ML-Based Drift Warnings
        </Typography>
        <Grid container spacing={2}>
          {driftWarnings.map((warning, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Alert
                severity={warning.severity === 'high' ? 'error' : 'warning'}
                sx={{ mb: 1 }}
              >
                <AlertTitle>
                  Drift Detected: {warning.agent_id}
                </AlertTitle>
                <Typography variant="body2">
                  Drift Score: {warning.metrics?.drift_score.toFixed(2)}
                  <br />
                  Compliance Probability: {(warning.metrics?.compliance_probability * 100).toFixed(1)}%
                  <br />
                  Confidence: {(warning.metrics?.confidence * 100).toFixed(1)}%
                  <br />
                  <br />
                  Recommendation: {warning.recommendation}
                </Typography>
              </Alert>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  const renderPredictions = () => {
    if (predictions.length === 0) return null;
    
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
          <TimelineIcon sx={{ mr: 1 }} />
          Compliance Predictions
        </Typography>
        <Grid container spacing={2}>
          {predictions.map((prediction, index) => (
            <Grid item xs={12} md={6} key={index}>
              <Alert severity="info" sx={{ mb: 1 }}>
                <AlertTitle>
                  Prediction: {prediction.agent_id}
                </AlertTitle>
                <Typography variant="body2">
                  Predicted Compliance: {(prediction.predicted_compliance * 100).toFixed(1)}%
                  <br />
                  Confidence: {(prediction.confidence * 100).toFixed(1)}%
                  <br />
                  <br />
                  Warning: {prediction.warning}
                </Typography>
              </Alert>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  const renderAgentInsights = () => {
    if (Object.keys(agentInsights).length === 0) return null;
    
    return (
      <Box sx={{ mb: 2 }}>
        <Typography variant="h6" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
          <InsightsIcon sx={{ mr: 1 }} />
          Agent Insights
        </Typography>
        <Grid container spacing={2}>
          {Object.entries(agentInsights).map(([agentId, insights]) => (
            <Grid item xs={12} md={6} key={agentId}>
              <Paper sx={{ p: 2 }}>
                <Typography variant="subtitle1" gutterBottom>
                  {agentId}
                </Typography>
                
                <Typography variant="subtitle2" gutterBottom>
                  Key Metrics:
                </Typography>
                <Box sx={{ mb: 2 }}>
                  <ResponsiveContainer width="100%" height={200}>
                    <RadarChart data={Object.entries(insights.key_metrics).map(([key, value]) => ({
                      metric: key,
                      value: value
                    }))}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="metric" />
                      <PolarRadiusAxis />
                      <Radar
                        name="Metrics"
                        dataKey="value"
                        stroke="#8884d8"
                        fill="#8884d8"
                        fillOpacity={0.6}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Trends:
                </Typography>
                <Box sx={{ mb: 2 }}>
                  {Object.entries(insights.trends).map(([metric, trend]) => (
                    <Typography key={metric} variant="body2">
                      {metric}: {trend}
                    </Typography>
                  ))}
                </Box>
                
                <Typography variant="subtitle2" gutterBottom>
                  Recommendations:
                </Typography>
                <Box>
                  {insights.recommendations.map((rec, index) => (
                    <Typography key={index} variant="body2" sx={{ mb: 1 }}>
                      • {rec}
                    </Typography>
                  ))}
                </Box>
              </Paper>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
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
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Logs" />
          <Tab label="Insights" />
          <Tab label="DNA Analysis" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Box display="flex" justifyContent="flex-end" mb={2}>
              <EmpathyExportManager
                onExport={handleExport}
                agents={agents}
              />
            </Box>
          </Grid>
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Recent Logs</Typography>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Type</TableCell>
                      <TableCell>Timestamp</TableCell>
                      <TableCell>Agent</TableCell>
                      <TableCell>Severity</TableCell>
                      <TableCell>Content</TableCell>
                      <TableCell>Drift</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {filteredLogs.map((log, index) => (
                      <TableRow key={index}>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            {getTypeIcon(log.type)}
                            <Typography sx={{ ml: 1 }}>
                              {log.type.charAt(0).toUpperCase() + log.type.slice(1)}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          {new Date(log.timestamp).toLocaleString()}
                        </TableCell>
                        <TableCell>{log.agent_id || 'System'}</TableCell>
                        <TableCell>
                          {log.severity && (
                            <Chip
                              label={log.severity}
                              size="small"
                              sx={{
                                backgroundColor: getSeverityColor(log.severity),
                                color: 'white',
                              }}
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography
                            sx={{
                              whiteSpace: 'pre-wrap',
                              fontFamily: 'monospace',
                            }}
                          >
                            {log.content}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          {log.drift_warning && (
                            <Tooltip title={log.drift_warning.recommendation}>
                              <TrendingDownIcon color="error" />
                            </Tooltip>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <EmpathyInsightsPanel
                agentId={selectedAgent || agents[0]}
                onRefresh={() => {
                  // Implement refresh logic
                }}
              />
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6">Agent Selection</Typography>
              {/* Add agent selection component here */}
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>

      <TabPanel value={tabValue} index={2}>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Paper sx={{ p: 2 }}>
              <AgentDNAInspector
                agentId={selectedAgent || agents[0]}
                onRefresh={() => {
                  // Implement refresh logic
                }}
              />
            </Paper>
          </Grid>
        </Grid>
      </TabPanel>
    </Box>
  );
};

export default EmpathyLogsTab; 