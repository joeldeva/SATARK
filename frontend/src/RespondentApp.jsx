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
  Chip,
  Alert,
  Button,
  Paper
} from '@mui/material';
import { Assignment, CheckCircle, Language } from '@mui/icons-material';
import SurveyResponseForm from './components/SurveyResponseForm';
import { generateSurvey } from './services/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#ff9800',
    },
    success: {
      main: '#4caf50',
    },
    background: {
      default: '#f8f9fa',
    },
  },
});

function RespondentApp() {
  const [survey, setSurvey] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load a demo survey on startup
  useEffect(() => {
    loadDemoSurvey();
  }, []);

  const loadDemoSurvey = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateSurvey({
        prompt: "Survey for farmers about crop production and income",
        languages: ["en"],
        max_questions: 10
      });
      
      if (result.success) {
        setSurvey(result.survey);
      } else {
        setError('Failed to load survey');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSurveySubmit = async (responses) => {
    console.log('Survey responses submitted:', responses);
    
    // Here you would typically send to backend
    // await submitSurveyResponse(responses);
    
    alert('Survey submitted successfully! (In production, this would be saved to the database)');
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ flexGrow: 1, minHeight: '100vh', bgcolor: 'background.default' }}>
        {/* Header */}
        <AppBar position="static" elevation={2}>
          <Toolbar>
            <Assignment sx={{ mr: 2 }} />
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              SATARK.AI - Survey Response Portal
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip 
                icon={<Language />} 
                label="English" 
                color="secondary" 
                size="small" 
              />
              <Chip 
                icon={<CheckCircle />} 
                label="Secure" 
                color="success" 
                size="small" 
              />
              <Button 
                color="inherit" 
                size="small"
                onClick={() => window.location.href = '/'}
                sx={{ ml: 1 }}
              >
                🎨 Design Survey
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

        {/* Main Content */}
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          {loading ? (
            <Paper sx={{ p: 4, textAlign: 'center' }}>
              <Typography>Loading survey...</Typography>
            </Paper>
          ) : (
            <>
              {/* Instructions */}
              <Alert severity="info" sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  <strong>Instructions:</strong>
                </Typography>
                <Typography variant="body2">
                  • Please answer all questions marked with * (required)<br />
                  • You can navigate back and forth between questions<br />
                  • Your progress is shown at the top<br />
                  • Click "Submit Survey" when you're done
                </Typography>
              </Alert>

              {/* Survey Form */}
              <SurveyResponseForm 
                survey={survey} 
                onSubmit={handleSurveySubmit}
              />

              {/* Load Different Survey */}
              <Box sx={{ mt: 4, textAlign: 'center' }}>
                <Button
                  variant="outlined"
                  onClick={loadDemoSurvey}
                  disabled={loading}
                >
                  Load New Survey
                </Button>
              </Box>
            </>
          )}

          {/* Footer */}
          <Box sx={{ mt: 6, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              🔒 Your responses are encrypted and secure • 
              📊 Data used for statistical purposes only • 
              🏛️ Government of India - MoSPI
            </Typography>
          </Box>
        </Container>
      </Box>
    </ThemeProvider>
  );
}

export default RespondentApp;
