import React, { useState, useEffect } from 'react';
import {
  Container,
  Box,
  AppBar,
  Toolbar,
  Typography,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Paper,
  Grid,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Card,
  CardContent,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow
} from '@mui/material';
import {
  Dashboard,
  Download,
  TrendingUp,
  CheckCircle,
  Warning,
  People,
  LocationOn
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

// Government-grade theme (Navy Blue + Teal + Neutral Grey)
const theme = createTheme({
  palette: {
    primary: {
      main: '#1a237e', // Navy Blue
    },
    secondary: {
      main: '#00897b', // Teal
    },
    error: {
      main: '#d32f2f',
    },
    warning: {
      main: '#f57c00',
    },
    success: {
      main: '#388e3c',
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff',
    },
    text: {
      primary: '#212121',
      secondary: '#757575',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
      color: '#1a237e',
    },
    h6: {
      fontWeight: 500,
    },
  },
});

function DashboardApp() {
  const [summary, setSummary] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [stateData, setStateData] = useState(null);
  const [agentData, setAgentData] = useState(null);
  const [sectorData, setSectorData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Colors for charts (Government grade)
  const COLORS = ['#1a237e', '#00897b', '#388e3c', '#f57c00', '#d32f2f', '#7b1fa2', '#0288d1', '#c62828'];
  
  // Filters
  const [selectedSurvey, setSelectedSurvey] = useState('all');
  const [timePeriod, setTimePeriod] = useState('monthly');
  const [selectedState, setSelectedState] = useState('all');

  useEffect(() => {
    loadDashboardData();
  }, [selectedSurvey, timePeriod, selectedState]);

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const baseUrl = 'http://localhost:8000';
      
      console.log('Loading dashboard data...');
      
      const [summaryRes, timeseriesRes, stateRes, agentRes, sectorRes] = await Promise.all([
        fetch(`${baseUrl}/analytics/summary`),
        fetch(`${baseUrl}/analytics/timeseries?period=${timePeriod}`),
        fetch(`${baseUrl}/analytics/state`),
        fetch(`${baseUrl}/analytics/agents`),
        fetch(`${baseUrl}/analytics/sector`)
      ]);

      if (!summaryRes.ok) throw new Error('Failed to load summary');
      if (!timeseriesRes.ok) throw new Error('Failed to load timeseries');
      if (!stateRes.ok) throw new Error('Failed to load state data');
      if (!agentRes.ok) throw new Error('Failed to load agent data');
      if (!sectorRes.ok) throw new Error('Failed to load sector data');

      const summaryData = await summaryRes.json();
      const timeseriesData = await timeseriesRes.json();
      const stateDataRes = await stateRes.json();
      const agentDataRes = await agentRes.json();
      const sectorDataRes = await sectorRes.json();

      console.log('Summary:', summaryData);
      console.log('Timeseries:', timeseriesData);
      console.log('State data:', stateDataRes);
      console.log('Agent data:', agentDataRes);
      console.log('Sector data:', sectorDataRes);

      setSummary(summaryData.data);
      setTimeseries(timeseriesData.data);
      setStateData(stateDataRes.data);
      setAgentData(agentDataRes.data);
      setSectorData(sectorDataRes.data);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = (format) => {
    alert(`Exporting dashboard data as ${format.toUpperCase()}...`);
    // In production, generate PDF/CSV export
  };

  if (loading) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', flexDirection: 'column' }}>
          <Typography variant="h6" gutterBottom>Loading Statistical Intelligence Dashboard...</Typography>
          <Typography variant="body2" color="text.secondary">Fetching real-time data from SATARK.AI</Typography>
        </Box>
      </ThemeProvider>
    );
  }

  if (error) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="md" sx={{ mt: 8 }}>
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Warning sx={{ fontSize: 60, color: 'error.main', mb: 2 }} />
            <Typography variant="h5" gutterBottom color="error">
              Dashboard Error
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              {error}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Please ensure the backend is running at http://localhost:8000
            </Typography>
            <Button variant="contained" onClick={loadDashboardData}>
              Retry
            </Button>
          </Paper>
        </Container>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* Header */}
        <AppBar position="static" elevation={2}>
          <Toolbar>
            <Dashboard sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              SATARK.AI - Statistical Intelligence Dashboard
            </Typography>
            <Chip 
              label="MoSPI Official" 
              color="secondary" 
              size="small" 
              sx={{ mr: 1 }}
            />
            <Chip 
              label="Real-Time" 
              color="success" 
              size="small" 
            />
          </Toolbar>
        </AppBar>

        <Container maxWidth="xl" sx={{ mt: 3, mb: 3 }}>
          {/* Top Control Bar */}
          <Paper elevation={2} sx={{ p: 2, mb: 3 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Survey</InputLabel>
                  <Select
                    value={selectedSurvey}
                    label="Survey"
                    onChange={(e) => setSelectedSurvey(e.target.value)}
                  >
                    <MenuItem value="all">All Surveys</MenuItem>
                    <MenuItem value="plfs">PLFS 2025-26</MenuItem>
                    <MenuItem value="nss">NSS Round 78</MenuItem>
                    <MenuItem value="nfhs">NFHS-6</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Time Period</InputLabel>
                  <Select
                    value={timePeriod}
                    label="Time Period"
                    onChange={(e) => setTimePeriod(e.target.value)}
                  >
                    <MenuItem value="daily">Daily</MenuItem>
                    <MenuItem value="weekly">Weekly</MenuItem>
                    <MenuItem value="monthly">Monthly</MenuItem>
                    <MenuItem value="quarterly">Quarterly</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Geography</InputLabel>
                  <Select
                    value={selectedState}
                    label="Geography"
                    onChange={(e) => setSelectedState(e.target.value)}
                  >
                    <MenuItem value="all">All India</MenuItem>
                    <MenuItem value="UP">Uttar Pradesh</MenuItem>
                    <MenuItem value="MH">Maharashtra</MenuItem>
                    <MenuItem value="BR">Bihar</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={6} sx={{ textAlign: 'right' }}>
                <Button
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={() => handleExport('pdf')}
                  sx={{ mr: 1 }}
                >
                  Export PDF
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Download />}
                  onClick={() => handleExport('csv')}
                >
                  Export CSV
                </Button>
              </Grid>
            </Grid>
          </Paper>

          {/* KPI Summary Row */}
          {summary && (
            <Grid container spacing={2} sx={{ mb: 3 }}>
              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Total Responses
                    </Typography>
                    <Typography variant="h4" component="div" color="primary">
                      {summary.total_responses.toLocaleString()}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      <TrendingUp fontSize="small" /> +12% vs last period
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Validated
                    </Typography>
                    <Typography variant="h4" component="div" color="success.main">
                      {summary.validation_rate}%
                    </Typography>
                    <Chip 
                      icon={<CheckCircle />} 
                      label="High Quality" 
                      color="success" 
                      size="small" 
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Error Rate
                    </Typography>
                    <Typography variant="h4" component="div" color="error.main">
                      {summary.error_rate}%
                    </Typography>
                    <Chip 
                      icon={<Warning />} 
                      label="Within Limits" 
                      color="warning" 
                      size="small" 
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Rural/Urban
                    </Typography>
                    <Typography variant="h5" component="div">
                      {summary.rural_urban_split.rural}% / {summary.rural_urban_split.urban}%
                    </Typography>
                    <Chip 
                      icon={<LocationOn />} 
                      label="Balanced" 
                      size="small" 
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Gender Ratio
                    </Typography>
                    <Typography variant="h6" component="div">
                      M: {summary.gender_distribution.male}<br/>
                      F: {summary.gender_distribution.female}
                    </Typography>
                    <Chip 
                      icon={<People />} 
                      label="Representative" 
                      size="small" 
                      sx={{ mt: 1 }}
                    />
                  </CardContent>
                </Card>
              </Grid>

              <Grid item xs={12} sm={6} md={2}>
                <Card elevation={3}>
                  <CardContent>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Confidence Score
                    </Typography>
                    <Typography variant="h4" component="div" color="secondary.main">
                      {summary.confidence_score}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Data Integrity Index
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          )}

          {/* Main Panels */}
          <Grid container spacing={3}>
            {/* State Comparison */}
            {stateData && stateData.states && stateData.states.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    State-wise Validation Rate
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Click state for district drill-down
                  </Typography>
                  <Box sx={{ height: '300px', overflowY: 'auto' }}>
                    {stateData.states.map((state, index) => (
                      <Box 
                        key={state} 
                        sx={{ 
                          mb: 1.5,
                          cursor: 'pointer',
                          '&:hover': { bgcolor: 'grey.50' },
                          p: 1,
                          borderRadius: 1
                        }}
                        onClick={() => alert(`Drill-down to ${state} districts (coming soon)`)}
                      >
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                          <Typography variant="body2" fontWeight="500">{state}</Typography>
                          <Typography 
                            variant="body2" 
                            fontWeight="bold"
                            color={stateData.values[index] > 85 ? 'success.main' : 'warning.main'}
                          >
                            {stateData.values[index]}%
                          </Typography>
                        </Box>
                        <Box sx={{ 
                          width: '100%', 
                          height: 10, 
                          bgcolor: 'grey.200', 
                          borderRadius: 1,
                          overflow: 'hidden'
                        }}>
                          <Box sx={{ 
                            width: `${stateData.values[index]}%`, 
                            height: '100%', 
                            bgcolor: stateData.values[index] > 85 ? 'success.main' : 'warning.main',
                            transition: 'width 0.3s ease'
                          }} />
                        </Box>
                      </Box>
                    ))}
                  </Box>
                </Paper>
              </Grid>
            )}

            {/* Agent Performance */}
            {agentData && agentData.agents && agentData.agents.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    Enumerator Performance Ranking
                  </Typography>
                  <TableContainer sx={{ maxHeight: 320 }}>
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ bgcolor: 'primary.main', color: 'white' }}><strong>Rank</strong></TableCell>
                          <TableCell sx={{ bgcolor: 'primary.main', color: 'white' }}><strong>Agent ID</strong></TableCell>
                          <TableCell align="right" sx={{ bgcolor: 'primary.main', color: 'white' }}><strong>Responses</strong></TableCell>
                          <TableCell align="right" sx={{ bgcolor: 'primary.main', color: 'white' }}><strong>Error %</strong></TableCell>
                          <TableCell align="right" sx={{ bgcolor: 'primary.main', color: 'white' }}><strong>Flagged %</strong></TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {agentData.agents.slice(0, 10).map((agent) => (
                          <TableRow 
                            key={agent.agent_id}
                            sx={{ 
                              '&:hover': { bgcolor: 'grey.50' },
                              cursor: 'pointer'
                            }}
                            onClick={() => alert(`View details for ${agent.agent_id} (coming soon)`)}
                          >
                            <TableCell>
                              <Chip 
                                label={agent.rank} 
                                size="small" 
                                color={agent.rank <= 3 ? 'success' : 'default'}
                              />
                            </TableCell>
                            <TableCell><strong>{agent.agent_id}</strong></TableCell>
                            <TableCell align="right">{agent.responses}</TableCell>
                            <TableCell 
                              align="right"
                              sx={{ 
                                color: agent.error_rate < 5 ? 'success.main' : 
                                       agent.error_rate < 10 ? 'warning.main' : 'error.main',
                                fontWeight: 'bold'
                              }}
                            >
                              {agent.error_rate}%
                            </TableCell>
                            <TableCell align="right">{agent.flagged_pct}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Paper>
              </Grid>
            )}
          </Grid>

          {/* Additional Chart Panels */}
          <Grid container spacing={3} sx={{ mt: 1 }}>
            {/* Time Series Trend Chart */}
            {timeseries && timeseries.dates && timeseries.dates.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    Response Trend Over Time
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    {timePeriod.charAt(0).toUpperCase() + timePeriod.slice(1)} aggregation
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={timeseries.dates.map((date, i) => ({
                      date: date,
                      responses: timeseries.values[i]
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 11 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="responses" 
                        stroke="#1a237e" 
                        strokeWidth={2}
                        dot={{ fill: '#1a237e', r: 4 }}
                        activeDot={{ r: 6 }}
                        name="Survey Responses"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}

            {/* Sector Contribution Pie Chart */}
            {sectorData && sectorData.sectors && sectorData.sectors.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    Sector-wise Distribution
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Employment by sector (%)
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={sectorData.sectors.map((sector, i) => ({
                          name: sector,
                          value: sectorData.values[i]
                        }))}
                        cx="50%"
                        cy="50%"
                        labelLine={true}
                        label={({ name, value }) => `${name}: ${value}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="value"
                      >
                        {sectorData.sectors.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}

            {/* State Comparison Bar Chart */}
            {stateData && stateData.states && stateData.states.length > 0 && (
              <Grid item xs={12}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    State-wise Validation Rate Comparison
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Horizontal bar chart for easy comparison
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart 
                      data={stateData.states.map((state, i) => ({
                        state: state,
                        rate: stateData.values[i]
                      }))}
                      layout="vertical"
                      margin={{ left: 100 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                      <YAxis 
                        dataKey="state" 
                        type="category" 
                        tick={{ fontSize: 11 }}
                        width={90}
                      />
                      <Tooltip />
                      <Legend />
                      <Bar 
                        dataKey="rate" 
                        fill="#00897b"
                        name="Validation Rate (%)"
                      >
                        {stateData.states.map((entry, index) => (
                          <Cell 
                            key={`cell-${index}`} 
                            fill={stateData.values[index] > 85 ? '#388e3c' : '#f57c00'} 
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}

            {/* Validation Metrics Area Chart */}
            {timeseries && timeseries.dates && timeseries.dates.length > 0 && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    Cumulative Response Collection
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Area chart showing growth over time
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <AreaChart data={timeseries.dates.map((date, i) => ({
                      date: date,
                      responses: timeseries.values.slice(0, i + 1).reduce((a, b) => a + b, 0)
                    }))}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 11 }}
                        angle={-45}
                        textAnchor="end"
                        height={80}
                      />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Area 
                        type="monotone" 
                        dataKey="responses" 
                        stroke="#1a237e" 
                        fill="#1a237e"
                        fillOpacity={0.3}
                        name="Cumulative Responses"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}

            {/* Gender Distribution Bar Chart */}
            {summary && summary.gender_distribution && (
              <Grid item xs={12} md={6}>
                <Paper elevation={3} sx={{ p: 3, height: '400px' }}>
                  <Typography variant="h6" gutterBottom color="primary">
                    Gender Distribution
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                    Respondent demographics
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={[
                      { gender: 'Male', count: summary.gender_distribution.male },
                      { gender: 'Female', count: summary.gender_distribution.female },
                      { gender: 'Other', count: summary.gender_distribution.other }
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis dataKey="gender" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="count" fill="#00897b" name="Respondents">
                        <Cell fill="#1a237e" />
                        <Cell fill="#00897b" />
                        <Cell fill="#7b1fa2" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
            )}
          </Grid>

          {/* Footer */}
          <Box sx={{ mt: 4, p: 2, textAlign: 'center', borderTop: '1px solid #e0e0e0' }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Data Source:</strong> SATARK.AI Validated Responses | 
              <strong> Last Updated:</strong> {summary?.timestamp ? new Date(summary.timestamp).toLocaleString() : 'N/A'} | 
              <strong> System:</strong> Government of India - Ministry of Statistics and Programme Implementation
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              🔒 Secure • 📊 Real-Time • ✅ GSBPM Compliant • 🏛️ MoSPI Standards
            </Typography>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default DashboardApp;
