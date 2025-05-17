import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  Divider,
  Grid,
  IconButton,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Close as CloseIcon,
  Compare as CompareIcon,
  ErrorOutline as ErrorOutlineIcon,
  Insights as InsightsIcon,
  Psychology as PsychologyIcon,
  Refresh as RefreshIcon,
  StarOutline as StarOutlineIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';
import React, { useEffect, useState } from 'react';

import EmpathyScoreCard from './EmpathyScoreCard';
import EmpathyScoreDetails from './EmpathyScoreDetails';

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

interface AgentComparison {
  timestamp: string;
  rankings: Array<[string, number]>;
  average_score: number;
  category_leaders: {
    [key: string]: {
      agent_id: string;
      score: number;
    }
  };
  empathy_status: string;
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

interface EmpathyScoresDashboardProps {
  onRefresh?: () => void;
}

const EmpathyScoresDashboard: React.FC<EmpathyScoresDashboardProps> = ({ onRefresh }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agentScores, setAgentScores] = useState<AgentScore[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedAgentData, setSelectedAgentData] = useState<AgentScoreDetailed | null>(null);
  const [agentHistoryData, setAgentHistoryData] = useState<any[]>([]);
  const [comparisonData, setComparisonData] = useState<AgentComparison | null>(null);
  const [thresholdStatus, setThresholdStatus] = useState<ThresholdStatus | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [dialogOpen, setDialogOpen] = useState(false);

  // Colors for status
  const statusColors = {
    exemplary: '#4caf50',
    proficient: '#8bc34a',
    developing: '#ffeb3b',
    needs_improvement: '#ff9800',
    critical: '#f44336',
    unknown: '#757575',
  };

  // Calculate score distribution for pie chart
  const getScoreDistribution = () => {
    const distribution = {
      exemplary: 0,
      proficient: 0,
      developing: 0,
      needs_improvement: 0,
      critical: 0,
    };

    agentScores.forEach(agent => {
      distribution[agent.status as keyof typeof distribution]++;
    });

    return Object.entries(distribution).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' '),
      value: count,
      color: statusColors[status as keyof typeof statusColors],
    }));
  };

  const fetchAgentScores = async (forceUpdate: boolean = false) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/empathy/scores?force_update=${forceUpdate}`);
      if (!response.ok) {
        throw new Error('Failed to fetch agent scores');
      }
      const data = await response.json();
      setAgentScores(data);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchAgentDetails = async (agentId: string) => {
    try {
      const response = await fetch(`/api/empathy/scores/${agentId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch details for agent ${agentId}`);
      }
      const data = await response.json();
      setSelectedAgentData(data);
      
      // Simulate historical data for now
      // In a real implementation, we would fetch this from an API endpoint
      const now = new Date();
      const mockHistory = Array.from({ length: 10 }, (_, i) => {
        const date = new Date();
        date.setDate(now.getDate() - (9 - i));
        return {
          timestamp: date.toISOString(),
          score: data.score - Math.random() * 10 + Math.random() * 10,
        };
      });
      mockHistory.push({
        timestamp: now.toISOString(),
        score: data.score,
      });
      
      setAgentHistoryData(mockHistory);
      setDialogOpen(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const fetchComparisonData = async () => {
    try {
      const response = await fetch('/api/empathy/comparison');
      if (!response.ok) {
        throw new Error('Failed to fetch comparison data');
      }
      const data = await response.json();
      setComparisonData(data);
    } catch (err: any) {
      console.error('Error fetching comparison data:', err);
    }
  };

  const fetchThresholdStatus = async () => {
    try {
      const response = await fetch('/api/empathy/threshold-status');
      if (!response.ok) {
        throw new Error('Failed to fetch threshold status');
      }
      const data = await response.json();
      setThresholdStatus(data);
    } catch (err: any) {
      console.error('Error fetching threshold status:', err);
    }
  };

  const handleRefresh = () => {
    fetchAgentScores(true);
    fetchComparisonData();
    fetchThresholdStatus();
    if (onRefresh) {
      onRefresh();
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgent(agentId);
    fetchAgentDetails(agentId);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  // Initial data fetch
  useEffect(() => {
    fetchAgentScores();
    fetchComparisonData();
    fetchThresholdStatus();
  }, []);

  const renderOverview = () => (
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">
              <PsychologyIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
              Agent Empathy Scores
            </Typography>
            <Button
              startIcon={<RefreshIcon />}
              variant="outlined"
              onClick={handleRefresh}
              size="small"
            >
              Refresh
            </Button>
          </Box>
          
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Alert severity="error">{error}</Alert>
          ) : (
            <Grid container spacing={2}>
              {agentScores.map((agent) => (
                <Grid item xs={12} sm={6} md={4} key={agent.agent_id}>
                  <EmpathyScoreCard
                    agentId={agent.agent_id}
                    score={agent.score}
                    status={agent.status}
                    summary={agent.summary}
                    trend={0} // We'd need to calculate this from history
                    lastUpdated={agent.timestamp}
                    onClick={() => handleAgentSelect(agent.agent_id)}
                  />
                </Grid>
              ))}
            </Grid>
          )}
        </Paper>
      </Grid>
      
      <Grid item xs={12} md={4}>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                <InsightsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                System Status
              </Typography>
              
              {thresholdStatus ? (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                    <Typography variant="h4" sx={{ fontWeight: 'bold', mr: 2 }}>
                      {thresholdStatus.average_score.toFixed(1)}
                    </Typography>
                    <Chip
                      label={thresholdStatus.status}
                      sx={{
                        bgcolor: 
                          thresholdStatus.status === 'Optimal' ? '#4caf50' :
                          thresholdStatus.status === 'Healthy' ? '#8bc34a' :
                          thresholdStatus.status === 'Stable' ? '#ffeb3b' :
                          thresholdStatus.status === 'Concerning' ? '#ff9800' : '#f44336',
                        color: thresholdStatus.status === 'Stable' ? 'black' : 'white',
                        fontWeight: 'bold',
                      }}
                    />
                  </Box>
                  
                  <Typography variant="body2" gutterBottom>
                    Agents below threshold: {thresholdStatus.agents_below_threshold}
                  </Typography>
                  
                  {thresholdStatus.critical_agents.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" color="error" gutterBottom>
                        <ErrorOutlineIcon sx={{ mr: 0.5, verticalAlign: 'middle', fontSize: '1rem' }} />
                        Critical Agents:
                      </Typography>
                      {thresholdStatus.critical_agents.map(agent => (
                        <Chip
                          key={agent.agent_id}
                          label={`${agent.agent_id}: ${agent.score.toFixed(1)}`}
                          size="small"
                          sx={{ mr: 1, mb: 1, bgcolor: '#f44336', color: 'white' }}
                          onClick={() => handleAgentSelect(agent.agent_id)}
                        />
                      ))}
                    </Box>
                  )}
                </>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <CircularProgress size={24} />
                </Box>
              )}
            </Paper>
          </Grid>
          
          <Grid item xs={12}>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                <AssessmentIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Score Distribution
              </Typography>
              
              {agentScores.length > 0 ? (
                <Box sx={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={getScoreDistribution()}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={80}
                        innerRadius={40}
                        fill="#8884d8"
                        dataKey="value"
                        nameKey="name"
                        label={({ name, value }) => value > 0 ? `${name}: ${value}` : ''}
                      >
                        {getScoreDistribution().map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <RechartsTooltip />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                  <Typography variant="body2" color="text.secondary">
                    No data available
                  </Typography>
                </Box>
              )}
            </Paper>
          </Grid>
          
          {comparisonData && (
            <Grid item xs={12}>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  <StarOutlineIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Top Performers
                </Typography>
                
                {comparisonData.rankings.length > 0 ? (
                  <Box>
                    {comparisonData.rankings.slice(0, 3).map((ranking, index) => (
                      <Box 
                        key={ranking[0]} 
                        sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          mb: 1,
                          p: 1,
                          bgcolor: index === 0 ? 'rgba(255, 215, 0, 0.1)' : 'transparent',
                          borderRadius: 1
                        }}
                      >
                        <Typography variant="h6" sx={{ mr: 2, width: 28, textAlign: 'center' }}>
                          {index + 1}.
                        </Typography>
                        <Typography variant="body1" sx={{ flexGrow: 1 }}>
                          {ranking[0]}
                        </Typography>
                        <Chip 
                          label={ranking[1].toFixed(1)} 
                          size="small" 
                          sx={{ 
                            bgcolor: index === 0 ? '#ffd700' : index === 1 ? '#c0c0c0' : '#cd7f32',
                            fontWeight: 'bold'
                          }} 
                        />
                      </Box>
                    ))}
                    
                    <Divider sx={{ my: 1 }} />
                    
                    <Typography variant="subtitle2" gutterBottom>
                      Category Leaders:
                    </Typography>
                    
                    <Grid container spacing={1}>
                      {Object.entries(comparisonData.category_leaders).map(([category, leader]) => (
                        <Grid item xs={6} key={category}>
                          <Tooltip title={`${leader.agent_id}: ${leader.score.toFixed(1)}`}>
                            <Chip
                              label={category.replace('_', ' ')}
                              size="small"
                              sx={{ 
                                textTransform: 'capitalize',
                                bgcolor: '#e0e0e0'
                              }}
                              onClick={() => handleAgentSelect(leader.agent_id)}
                            />
                          </Tooltip>
                        </Grid>
                      ))}
                    </Grid>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    No ranking data available
                  </Typography>
                )}
              </Paper>
            </Grid>
          )}
        </Grid>
      </Grid>
    </Grid>
  );

  const renderComparison = () => (
    <Grid container spacing={3}>
      <Grid item xs={12}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            <CompareIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Agent Score Comparison
          </Typography>
          
          {agentScores.length > 0 ? (
            <Box sx={{ height: 400 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={agentScores.map(agent => ({
                    agent_id: agent.agent_id,
                    score: agent.score,
                    status: agent.status,
                  }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 70 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="agent_id" 
                    angle={-45} 
                    textAnchor="end" 
                    height={70}
                    interval={0}
                  />
                  <YAxis domain={[0, 100]} />
                  <RechartsTooltip
                    formatter={(value, name, props) => [
                      `Score: ${value}`,
                      `Status: ${props.payload.status.charAt(0).toUpperCase() + props.payload.status.slice(1).replace('_', ' ')}`
                    ]}
                  />
                  <Bar 
                    dataKey="score" 
                    name="Empathy Score"
                  >
                    {agentScores.map((agent, index) => (
                      <Cell 
                        key={`cell-${index}`} 
                        fill={statusColors[agent.status as keyof typeof statusColors]}
                        onClick={() => handleAgentSelect(agent.agent_id)}
                        cursor="pointer"
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
              <Typography variant="body2" color="text.secondary">
                No comparison data available
              </Typography>
            </Box>
          )}
        </Paper>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            <TrendingUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Weighted Component Analysis
          </Typography>
          
          {agentScores.length > 0 && selectedAgentData ? (
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(selectedAgentData.weighted_components).map(([key, value]) => ({
                    component: key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' '),
                    score: value,
                  }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis 
                    dataKey="component" 
                    type="category" 
                    width={120}
                  />
                  <RechartsTooltip />
                  <Bar 
                    dataKey="score" 
                    name="Component Score"
                    fill="#8884d8"
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
              <Typography variant="body2" color="text.secondary">
                Select an agent to view component analysis
              </Typography>
            </Box>
          )}
        </Paper>
      </Grid>
      
      <Grid item xs={12} md={6}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" gutterBottom>
            <InsightsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Value Scores Comparison
          </Typography>
          
          {agentScores.length > 0 && selectedAgentData ? (
            <Box sx={{ height: 300 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={Object.entries(selectedAgentData.value_scores).map(([key, value]) => ({
                    value: key.charAt(0).toUpperCase() + key.slice(1),
                    score: value,
                  }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 50 }}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} />
                  <YAxis 
                    dataKey="value" 
                    type="category" 
                    width={120}
                  />
                  <RechartsTooltip />
                  <Bar 
                    dataKey="score" 
                    name="Value Score"
                    fill="#82ca9d"
                  />
                </BarChart>
              </ResponsiveContainer>
            </Box>
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 300 }}>
              <Typography variant="body2" color="text.secondary">
                Select an agent to view value scores
              </Typography>
            </Box>
          )}
        </Paper>
      </Grid>
    </Grid>
  );

  return (
    <Box sx={{ p: 2 }}>
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          indicatorColor="primary"
          textColor="primary"
          variant="fullWidth"
        >
          <Tab 
            icon={<PsychologyIcon />} 
            label="Overview" 
            id="empathy-tab-0"
            aria-controls="empathy-tabpanel-0"
          />
          <Tab 
            icon={<CompareIcon />} 
            label="Comparison" 
            id="empathy-tab-1"
            aria-controls="empathy-tabpanel-1"
          />
        </Tabs>
      </Paper>
      
      <Box
        role="tabpanel"
        hidden={tabValue !== 0}
        id="empathy-tabpanel-0"
        aria-labelledby="empathy-tab-0"
      >
        {tabValue === 0 && renderOverview()}
      </Box>
      
      <Box
        role="tabpanel"
        hidden={tabValue !== 1}
        id="empathy-tabpanel-1"
        aria-labelledby="empathy-tab-1"
      >
        {tabValue === 1 && renderComparison()}
      </Box>
      
      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        maxWidth="lg"
        fullWidth
      >
        <Box sx={{ position: 'absolute', right: 8, top: 8, zIndex: 1 }}>
          <IconButton onClick={handleCloseDialog}>
            <CloseIcon />
          </IconButton>
        </Box>
        
        <DialogContent>
          {selectedAgentData && (
            <EmpathyScoreDetails 
              scoreData={selectedAgentData}
              historyData={agentHistoryData}
              onRefresh={() => {
                if (selectedAgent) {
                  fetchAgentDetails(selectedAgent);
                }
              }}
            />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default EmpathyScoresDashboard; 