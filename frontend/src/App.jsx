import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  AppBar,
  Toolbar,
  ThemeProvider,
  createTheme,
  CssBaseline,
  Chip,
  Alert,
  Button
} from '@mui/material';
import { Psychology, Security, Verified } from '@mui/icons-material';

import PromptInput from './components/PromptInput';
import SurveyCanvas from './components/SurveyCanvas';
import ValidationPanel from './components/ValidationPanel';
import { healthCheck, getSystemInfo } from './services/api';

// Create theme with government colors
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2', // Government blue
    },
    secondary: {
      main: '#ff9800', // Saffron
    },
    success: {
      main: '#4caf50', // Green
    },
    background: {
      default: '#f8f9fa',
    },
  },
  typography: {
    h4: {
      fontWeight: 600,
    },
    h6: {
      fontWeight: 500,
    },
  },
});

function App() {
  const [survey, setSurvey] = useState(null);
  const [intent, setIntent] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [engineTrace, setEngineTrace] = useState([]);
  const [validationScore, setValidationScore] = useState(0);

  // Check system health on startup
  useEffect(() => {
    checkSystemHealth();
  }, []);

  const checkSystemHealth = async () => {
    try {
      const [health, systemInfo] = await Promise.all([
        healthCheck(),
        getSystemInfo()
      ]);
      
      setSystemStatus({
        healthy: health.status === 'healthy',
        engines: health.engines,
        systemInfo: systemInfo
      });
    } catch (error) {
      console.error('System health check failed:', error);
      setSystemStatus({
        healthy: false,
        error: error.message
      });
    }
  };

  const handleSurveyGenerated = (result) => {
    setSurvey(result.survey);
    setIntent(result.intent);
    setErrors(result.errors || []);
    setWarnings(result.warnings || []);
    setEngineTrace(result.engine_trace || []);
    setValidationScore(result.validation_score || 0);
  };

  const handleSurveyUpdated = (updatedSurvey) => {
    setSurvey(updatedSurvey);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1 }}>
        {/* Header */}
        <AppBar position="static" elevation={2}>
          <Toolbar>
            <Psychology sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              SATARK.AI - Deterministic Survey Intelligence Engine
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip 
                icon={<Verified />} 
                label="Government Grade" 
                color="success" 
                size="small" 
              />
              <Chip 
                icon={<Security />} 
                label="No Data Leaks" 
                color="secondary" 
                size="small" 
              />
              <Button 
                color="inherit" 
                size="small"
                onClick={() => window.location.href = '/respond'}
                sx={{ ml: 1 }}
              >
                📝 Fill Survey
              </Button>
              <Button 
                color="inherit" 
                size="small"
                onClick={() => window.location.href = '/dashboard'}
              >
                📊 Dashboard
              </Button>
            </Box>
          </Toolbar>
        </AppBar>

        {/* System Status Banner */}
        {systemStatus && (
          <Box sx={{ p: 1 }}>
            {systemStatus.healthy ? (
              <Alert severity="success" sx={{ mb: 1 }}>
                <strong>SATARK.AI Operational</strong> - All engines loaded successfully. 
                Architecture: {systemStatus.systemInfo?.architecture}
              </Alert>
            ) : (
              <Alert severity="error" sx={{ mb: 1 }}>
                <strong>System Error</strong> - {systemStatus.error || 'Backend not responding'}
              </Alert>
            )}
          </Box>
        )}

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ mt: 2, mb: 3 }}>
          <Grid container spacing={3}>
            {/* Left Panel - Prompt Input */}
            <Grid item xs={12} md={4}>
              <Paper elevation={3} sx={{ p: 3, height: 'fit-content' }}>
                <Typography variant="h6" gutterBottom color="primary">
                  🔹 AI Intelligence Panel
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Describe your survey requirements in natural language
                </Typography>
                <PromptInput
                  onSurveyGenerated={handleSurveyGenerated}
                  loading={loading}
                  setLoading={setLoading}
                />
                
                {/* Intent Display */}
                {intent && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Extracted Intent:
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
                      <Typography variant="body2">
                        <strong>Domain:</strong> {intent.domain || 'Auto-detected'}<br />
                        <strong>Audience:</strong> {intent.audience || 'General'}<br />
                        <strong>Topic:</strong> {intent.topic || 'Survey topic'}<br />
                        <strong>Questions:</strong> {intent.num_questions || 'Auto'}<br />
                        <strong>Languages:</strong> {intent.languages?.join(', ') || 'English'}<br />
                        <strong>Confidence:</strong> {intent.confidence ? `${(intent.confidence * 100).toFixed(1)}%` : 'N/A'}
                      </Typography>
                    </Paper>
                  </Box>
                )}

                {/* Engine Trace */}
                {engineTrace && engineTrace.length > 0 && (
                  <Box sx={{ mt: 3 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Processing Trace:
                    </Typography>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50', maxHeight: 200, overflow: 'auto' }}>
                      {engineTrace.map((trace, index) => (
                        <Typography key={index} variant="caption" display="block">
                          <strong>Step {trace.step}:</strong> {trace.engine} - {trace.output}
                        </Typography>
                      ))}
                    </Paper>
                  </Box>
                )}
              </Paper>
            </Grid>

            {/* Center Panel - Survey Canvas */}
            <Grid item xs={12} md={5}>
              <Paper elevation={3} sx={{ p: 3, minHeight: '600px' }}>
                <Typography variant="h6" gutterBottom color="primary">
                  🔹 Generated Survey Canvas
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  GSBPM-compliant survey ready for deployment
                </Typography>
                <SurveyCanvas
                  survey={survey}
                  onSurveyUpdated={handleSurveyUpdated}
                  loading={loading}
                  validationScore={validationScore}
                />
              </Paper>
            </Grid>

            {/* Right Panel - Validation & Standards */}
            <Grid item xs={12} md={3}>
              <Paper elevation={3} sx={{ p: 3, height: 'fit-content' }}>
                <Typography variant="h6" gutterBottom color="primary">
                  🔹 Quality Assurance
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  GSBPM compliance and MoSPI standards validation
                </Typography>
                <ValidationPanel
                  survey={survey}
                  errors={errors}
                  warnings={warnings}
                  validationScore={validationScore}
                />
              </Paper>
            </Grid>
          </Grid>

          {/* Footer Info */}
          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              🎯 <strong>SATARK.AI</strong> - Hybrid Statistical Intelligence • 
              ✅ Deterministic • 🔒 No Data Leaks • 📊 Government Grade • 
              🏛️ GSBPM Compliant • 📋 MoSPI Standards
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
              Architecture: Rule Engine + Question Repository + NLP Classifier + Embedding Search + Statistical ML
            </Typography>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default App;