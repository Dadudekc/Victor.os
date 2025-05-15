import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Paper,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Psychology as PsychologyIcon,
  SentimentDissatisfied as SentimentDissatisfiedIcon,
  SentimentSatisfied as SentimentSatisfiedIcon,
  SentimentVeryDissatisfied as SentimentVeryDissatisfiedIcon,
  SentimentVerySatisfied as SentimentVerySatisfiedIcon,
  TrendingDown as TrendingDownIcon,
  TrendingFlat as TrendingFlatIcon,
  TrendingUp as TrendingUpIcon,
} from '@mui/icons-material';

import React from 'react';

interface EmpathyScoreCardProps {
  agentId: string;
  score: number;
  status: string;
  summary: string;
  trend?: number;
  valueScores?: { [key: string]: number };
  lastUpdated?: string;
  size?: 'small' | 'medium' | 'large';
  onClick?: () => void;
}

const EmpathyScoreCard: React.FC<EmpathyScoreCardProps> = ({
  agentId,
  score,
  status,
  summary,
  trend = 0,
  valueScores,
  lastUpdated,
  size = 'medium',
  onClick,
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

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'exemplary':
        return <SentimentVerySatisfiedIcon />;
      case 'proficient':
        return <SentimentSatisfiedIcon />;
      case 'developing':
        return <SentimentSatisfiedIcon sx={{ color: '#ffeb3b' }} />;
      case 'needs_improvement':
        return <SentimentDissatisfiedIcon />;
      case 'critical':
        return <SentimentVeryDissatisfiedIcon />;
      default:
        return <PsychologyIcon />;
    }
  };

  const getTrendIcon = (trend: number) => {
    if (trend > 3) {
      return <TrendingUpIcon sx={{ color: '#4caf50' }} />;
    } else if (trend < -3) {
      return <TrendingDownIcon sx={{ color: '#f44336' }} />;
    }
    return <TrendingFlatIcon sx={{ color: '#757575' }} />;
  };

  const formatStatus = (status: string): string => {
    return status
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  return (
    <Card 
      variant="outlined" 
      sx={{ 
        cursor: onClick ? 'pointer' : 'default',
        border: `2px solid ${getStatusColor(status)}`,
        transition: 'all 0.2s ease',
        '&:hover': {
          boxShadow: onClick ? 3 : 0,
          transform: onClick ? 'translateY(-2px)' : 'none',
        },
        height: size === 'small' ? 'auto' : '100%',
      }} 
      onClick={onClick}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant={size === 'small' ? 'subtitle1' : 'h6'} sx={{ fontWeight: 'bold' }}>
            {agentId}
          </Typography>
          <Chip 
            icon={getStatusIcon(status)}
            label={formatStatus(status)} 
            sx={{ 
              bgcolor: getStatusColor(status), 
              color: 'white',
              fontWeight: 'bold',
            }} 
            size={size === 'small' ? 'small' : 'medium'}
          />
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Typography 
            variant={size === 'small' ? 'h6' : 'h4'} 
            sx={{ 
              fontWeight: 'bold', 
              color: getStatusColor(status),
              mr: 2 
            }}
          >
            {score.toFixed(1)}
          </Typography>
          <Box sx={{ flexGrow: 1 }}>
            <Tooltip title={`Empathy Score: ${score.toFixed(1)}/100`}>
              <LinearProgress 
                variant="determinate" 
                value={score} 
                sx={{ 
                  height: size === 'small' ? 10 : 15, 
                  borderRadius: 5,
                  bgcolor: 'rgba(0,0,0,0.1)',
                  '& .MuiLinearProgress-bar': {
                    bgcolor: getStatusColor(status),
                  }
                }} 
              />
            </Tooltip>
          </Box>
          <Box sx={{ ml: 1 }}>
            {getTrendIcon(trend)}
          </Box>
        </Box>

        {size !== 'small' && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {summary}
          </Typography>
        )}

        {valueScores && size !== 'small' && (
          <Grid container spacing={1} sx={{ mt: 1 }}>
            {Object.entries(valueScores).map(([value, score]) => (
              <Grid item xs={6} key={value}>
                <Tooltip title={`${value.charAt(0).toUpperCase() + value.slice(1)}: ${score.toFixed(1)}/100`}>
                  <Paper 
                    variant="outlined" 
                    sx={{ 
                      p: 1, 
                      display: 'flex', 
                      flexDirection: 'column',
                      alignItems: 'center'
                    }}
                  >
                    <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                      {value}
                    </Typography>
                    <LinearProgress
                      variant="determinate"
                      value={score}
                      sx={{
                        width: '100%',
                        height: 5,
                        borderRadius: 5,
                        mt: 0.5,
                        '& .MuiLinearProgress-bar': {
                          bgcolor: score > 80 ? '#4caf50' : score > 60 ? '#ffeb3b' : '#f44336',
                        }
                      }}
                    />
                  </Paper>
                </Tooltip>
              </Grid>
            ))}
          </Grid>
        )}

        {lastUpdated && size !== 'small' && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block', textAlign: 'right' }}>
            Last updated: {new Date(lastUpdated).toLocaleString()}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export default EmpathyScoreCard; 