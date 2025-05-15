import {
  AssessmentOutlined as AssessmentIcon,
  BalanceOutlined as BalanceIcon,
  HealingOutlined as HealingIcon,
  Insights as InsightsIcon,
  Loop as LoopIcon,
  Psychology as PsychologyIcon,
  Refresh as RefreshIcon,
  SpatialTrackingOutlined as SpatialTrackingIcon,
  Timeline as TimelineIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid,
  IconButton,
  LinearProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from 'recharts';

import React from 'react';

interface EmpathyScoreDetailsProps {
  scoreData: {
    agent_id: string;
    score: number;
    status: string;
    summary: string;
    timestamp: string;
    metrics: {
      violations: number;
      compliances: number;
      violation_severity: {
        low: number;
        medium: number;
        high: number;
        critical: number;
      };
    };
    value_scores: {
      [key: string]: number;
    };
    frequency: {
      violation_rate: number;
      compliance_rate: number;
      total_entries: number;
    };
    trend: {
      overall: number;
      weekly: number;
      daily: number;
    };
    recovery: {
      recovery_attempts: number;
      successful_recoveries: number;
      recovery_rate: number;
    };
    context: {
      awareness_score: number;
      context_metrics: any;
    };
    weighted_components: {
      core_values: number;
      frequency: number;
      trend: number;
      recovery: number;
      context: number;
    };
  };
  onRefresh?: () => void;
  historyData?: Array<{
    timestamp: string;
    score: number;
  }>;
}

const EmpathyScoreDetails: React.FC<EmpathyScoreDetailsProps> = ({
  scoreData,
  onRefresh,
  historyData = [],
}) => {
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'exemplary':
        return '#4caf50';
      case 'proficient':
        return '#8bc34a';
      case 'developing':
        return '#ffeb3b';
      case 'needs_improvement':
        return '#ff9800';
      case 'critical':
        return '#f44336';
      default:
        return '#757575';
    }
  };

  const formatStatus = (status: string): string => {
    return status
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const radarData = Object.entries(scoreData.weighted_components).map(([key, value]) => ({
    subject: key.charAt(0).toUpperCase() + key.slice(1).replace('_', ' '),
    score: value,
    fullMark: 100,
  }));

  const valueRadarData = Object.entries(scoreData.value_scores).map(([key, value]) => ({
    subject: key.charAt(0).toUpperCase() + key.slice(1),
    score: value,
    fullMark: 100,
  }));

  const severityData = Object.entries(scoreData.metrics.violation_severity).map(([key, value]) => ({
    name: key.charAt(0).toUpperCase() + key.slice(1),
    count: value,
  }));

  const trendData = [
    { name: 'Overall', value: scoreData.trend.overall },
    { name: 'Weekly', value: scoreData.trend.weekly },
    { name: 'Daily', value: scoreData.trend.daily },
  ];

  const historyChartData = historyData.map(item => ({
    date: new Date(item.timestamp).toLocaleDateString(),
    score: item.score,
  }));

  const getComponentIcon = (component: string) => {
    switch (component) {
      case 'core_values':
        return <BalanceIcon />;
      case 'frequency':
        return <LoopIcon />;
      case 'trend':
        return <TimelineIcon />;
      case 'recovery':
        return <HealingIcon />;
      case 'context':
        return <SpatialTrackingIcon />;
      default:
        return <AssessmentIcon />;
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
          <PsychologyIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Empathy Profile: {scoreData.agent_id}
        </Typography>
        {onRefresh && (
          <Button 
            startIcon={<RefreshIcon />} 
            variant="outlined" 
            onClick={onRefresh}
            size="small"
          >
            Refresh
          </Button>
        )}
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Empathy Score
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography 
                  variant="h2" 
                  sx={{ 
                    fontWeight: 'bold', 
                    color: getStatusColor(scoreData.status),
                    mr: 2 
                  }}
                >
                  {scoreData.score.toFixed(1)}
                </Typography>
                <Chip 
                  label={formatStatus(scoreData.status)} 
                  sx={{ 
                    bgcolor: getStatusColor(scoreData.status), 
                    color: 'white',
                    fontWeight: 'bold',
                    fontSize: '1rem',
                    px: 1
                  }} 
                />
              </Box>
              <Divider sx={{ my: 2 }} />
              <Typography variant="body1" paragraph>
                {scoreData.summary}
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Last updated: {new Date(scoreData.timestamp).toLocaleString()}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={8}>
          <Card variant="outlined" sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <InsightsIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
                Performance Metrics
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart outerRadius={90} data={radarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" />
                    <PolarRadiusAxis domain={[0, 100]} />
                    <Radar
                      name="Weighted Components"
                      dataKey="score"
                      stroke="#8884d8"
                      fill="#8884d8"
                      fillOpacity={0.6}
                    />
                    <RechartsTooltip />
                    <Legend />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Core Values Alignment
              </Typography>
              <Box sx={{ height: 250 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart outerRadius={90} data={valueRadarData}>
                    <PolarGrid />
                    <PolarAngleAxis dataKey="subject" />
                    <PolarRadiusAxis domain={[0, 100]} />
                    <Radar
                      name="Value Score"
                      dataKey="score"
                      stroke="#82ca9d"
                      fill="#82ca9d"
                      fillOpacity={0.6}
                    />
                    <RechartsTooltip />
                  </RadarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Trend
              </Typography>
              {historyChartData.length > 0 ? (
                <Box sx={{ height: 250 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={historyChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis domain={[0, 100]} />
                      <RechartsTooltip />
                      <Line
                        type="monotone"
                        dataKey="score"
                        stroke="#8884d8"
                        activeDot={{ r: 8 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              ) : (
                <Box sx={{ height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Typography variant="body2" color="text.secondary">
                    No historical data available
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Weighted Component Scores
              </Typography>
              <Grid container spacing={2}>
                {Object.entries(scoreData.weighted_components).map(([key, value]) => (
                  <Grid item xs={12} sm={6} md={4} lg={2.4} key={key}>
                    <Paper elevation={0} variant="outlined" sx={{ p: 2 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                        <Box sx={{ mr: 1 }}>
                          {getComponentIcon(key)}
                        </Box>
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                          {key.replace('_', ' ')}
                        </Typography>
                      </Box>
                      <Typography variant="h5" sx={{ fontWeight: 'bold', mb: 1 }}>
                        {value.toFixed(1)}
                      </Typography>
                      <LinearProgress
                        variant="determinate"
                        value={value}
                        sx={{
                          height: 8,
                          borderRadius: 5,
                          bgcolor: 'rgba(0,0,0,0.1)',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: value > 80 ? '#4caf50' : value > 60 ? '#ffeb3b' : '#f44336',
                          }
                        }}
                      />
                    </Paper>
                  </Grid>
                ))}
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Violations by Severity
              </Typography>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Severity</TableCell>
                      <TableCell align="right">Count</TableCell>
                      <TableCell align="right">Impact</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {severityData.map((row) => (
                      <TableRow key={row.name}>
                        <TableCell component="th" scope="row">
                          {row.name}
                        </TableCell>
                        <TableCell align="right">{row.count}</TableCell>
                        <TableCell align="right">
                          <Chip
                            size="small"
                            label={
                              row.name === 'Critical'
                                ? 'Very High'
                                : row.name === 'High'
                                ? 'High'
                                : row.name === 'Medium'
                                ? 'Medium'
                                : 'Low'
                            }
                            sx={{
                              bgcolor:
                                row.name === 'Critical'
                                  ? '#f44336'
                                  : row.name === 'High'
                                  ? '#ff9800'
                                  : row.name === 'Medium'
                                  ? '#ffeb3b'
                                  : '#8bc34a',
                              color: row.name === 'Medium' || row.name === 'Low' ? 'black' : 'white',
                            }}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recovery & Context Metrics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Recovery Effectiveness
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 'bold', mr: 2 }}>
                        {(scoreData.recovery.recovery_rate * 100).toFixed(1)}%
                      </Typography>
                      <Box sx={{ flexGrow: 1 }}>
                        <Tooltip title={`Recovery Rate: ${(scoreData.recovery.recovery_rate * 100).toFixed(1)}%`}>
                          <LinearProgress
                            variant="determinate"
                            value={scoreData.recovery.recovery_rate * 100}
                            sx={{
                              height: 8,
                              borderRadius: 5,
                              bgcolor: 'rgba(0,0,0,0.1)',
                              '& .MuiLinearProgress-bar': {
                                bgcolor: scoreData.recovery.recovery_rate > 0.8 ? '#4caf50' : scoreData.recovery.recovery_rate > 0.6 ? '#ffeb3b' : '#f44336',
                              }
                            }}
                          />
                        </Tooltip>
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary">
                      {scoreData.recovery.successful_recoveries} successful recoveries out of {scoreData.recovery.recovery_attempts} attempts
                    </Typography>
                  </Paper>
                </Grid>

                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Context Awareness
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 'bold', mr: 2 }}>
                        {(scoreData.context.awareness_score * 100).toFixed(1)}%
                      </Typography>
                      <Box sx={{ flexGrow: 1 }}>
                        <Tooltip title={`Context Awareness: ${(scoreData.context.awareness_score * 100).toFixed(1)}%`}>
                          <LinearProgress
                            variant="determinate"
                            value={scoreData.context.awareness_score * 100}
                            sx={{
                              height: 8,
                              borderRadius: 5,
                              bgcolor: 'rgba(0,0,0,0.1)',
                              '& .MuiLinearProgress-bar': {
                                bgcolor: scoreData.context.awareness_score > 0.8 ? '#4caf50' : scoreData.context.awareness_score > 0.6 ? '#ffeb3b' : '#f44336',
                              }
                            }}
                          />
                        </Tooltip>
                      </Box>
                    </Box>
                  </Paper>
                </Grid>

                <Grid item xs={12}>
                  <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Activity Summary
                    </Typography>
                    <Typography variant="body2">
                      Total Entries: <strong>{scoreData.frequency.total_entries}</strong>
                    </Typography>
                    <Typography variant="body2">
                      Compliance Rate: <strong>{(scoreData.frequency.compliance_rate * 100).toFixed(1)}%</strong>
                    </Typography>
                    <Typography variant="body2">
                      Violation Rate: <strong>{(scoreData.frequency.violation_rate * 100).toFixed(1)}%</strong>
                    </Typography>
                  </Paper>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default EmpathyScoreDetails; 