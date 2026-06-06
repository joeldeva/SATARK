import React, { useState } from 'react';
import {
  Box, AppBar, Toolbar, Typography, Container, Paper,
  TextField, Button, CircularProgress, Alert, Chip,
  Grid, Card, CardContent, Divider, Tabs, Tab
} from '@mui/material';
import { AutoAwesome, Assignment, CheckCircle } from '@mui/icons-material';
import SurveyPreview from './SurveyPreview';
import SurveyList from './SurveyList';

const API = 'http://localhost:8001/api/v1';

const EXAMPLE_PROMPTS = [
  'A survey for rural women about healthcare access with 8 questions',
  'Employment survey for youth in urban areas covering job satisfaction and income',
  'Agriculture survey for farmers about crop yield and government schemes with 10 questions',
  'Household expenditure survey covering food, education and health spending',
];

export default function SurveyDesigner() {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [survey, setSurvey] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState(0);

  const generate = async () => {
    if (!prompt.trim() || prompt.length < 10) {
      setError('Please enter a prompt of at least 10 characters.');
      return;
    }
    setLoading(true);
    setError(null);
    setSurvey(null);
    try {
      const res = await fetch(`${API}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, user_id: 'officer_001' }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Generation failed');
      setSurvey(data.survey);
      setTab(1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: 'background.default' }}>
      {/* Header */}
      <AppBar position="static" elevation={2} sx={{ bgcolor: '#1a237e' }}>
        <Toolbar>
          <Assignment sx={{ mr: 1.5 }} />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
              SATARK — Survey Intelligence Platform
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              सतर्क | Vigilant Data Collection for Vigilant India
            </Typography>
          </Box>
          <Chip label="MoSPI" color="secondary" size="small" sx={{ mr: 1 }} />
          <Chip label="v1.0" size="small" sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: 'white' }} />
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 6 }}>
        {/* Tabs */}
        <Paper elevation={2} sx={{ mb: 3 }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} indicatorColor="primary" textColor="primary">
            <Tab label="Generate Survey" icon={<AutoAwesome />} iconPosition="start" />
            <Tab label="Preview" icon={<Assignment />} iconPosition="start" disabled={!survey} />
            <Tab label="All Surveys" icon={<CheckCircle />} iconPosition="start" />
          </Tabs>
        </Paper>

        {/* Tab 0: Generator */}
        {tab === 0 && (
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Paper elevation={3} sx={{ p: 3 }}>
                <Typography variant="h5" gutterBottom>
                  Generate Survey from Natural Language
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                  Describe your survey in plain English. SATARK will retrieve relevant questions
                  from the official NSS/PLFS/NFHS question bank and structure them automatically.
                </Typography>

                <TextField
                  fullWidth
                  multiline
                  rows={4}
                  label="Survey Prompt"
                  placeholder="e.g. A survey for rural women about healthcare access with 8 questions"
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  variant="outlined"
                  sx={{ mb: 2 }}
                />

                {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

                <Button
                  variant="contained"
                  size="large"
                  onClick={generate}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <AutoAwesome />}
                  sx={{ minWidth: 180 }}
                >
                  {loading ? 'Generating...' : 'Generate Survey'}
                </Button>
              </Paper>
            </Grid>

            <Grid item xs={12} md={4}>
              <Paper elevation={2} sx={{ p: 3 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  Example Prompts
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {EXAMPLE_PROMPTS.map((p, i) => (
                  <Box
                    key={i}
                    onClick={() => setPrompt(p)}
                    sx={{
                      p: 1.5, mb: 1.5, borderRadius: 1, cursor: 'pointer',
                      border: '1px solid #e0e0e0',
                      '&:hover': { bgcolor: '#e8eaf6', borderColor: '#1a237e' },
                      fontSize: 13
                    }}
                  >
                    {p}
                  </Box>
                ))}
              </Paper>

              <Paper elevation={2} sx={{ p: 3, mt: 2 }}>
                <Typography variant="subtitle1" fontWeight={600} gutterBottom>
                  How It Works
                </Typography>
                <Divider sx={{ mb: 2 }} />
                {[
                  ['1. Parse', 'NLP extracts domain, audience, location'],
                  ['2. Retrieve', 'RAG finds relevant questions from NSS/PLFS bank'],
                  ['3. Rules', 'Mandatory questions + ordering applied'],
                  ['4. Validate', 'Statistical checks + skip logic generated'],
                ].map(([step, desc]) => (
                  <Box key={step} sx={{ mb: 1.5 }}>
                    <Typography variant="body2" fontWeight={600} color="primary">{step}</Typography>
                    <Typography variant="caption" color="text.secondary">{desc}</Typography>
                  </Box>
                ))}
              </Paper>
            </Grid>
          </Grid>
        )}

        {/* Tab 1: Preview */}
        {tab === 1 && survey && <SurveyPreview survey={survey} />}

        {/* Tab 2: All Surveys */}
        {tab === 2 && <SurveyList onSelect={s => { setSurvey(s); setTab(1); }} />}
      </Container>
    </Box>
  );
}
