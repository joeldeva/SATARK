import React, { useState, useEffect } from 'react';
import {
  Paper, Typography, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, Button, Alert, CircularProgress, Box
} from '@mui/material';
import { Visibility, Refresh } from '@mui/icons-material';

const API = 'http://localhost:8001/api/v1';

export default function SurveyList({ onSelect }) {
  const [surveys, setSurveys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/surveys`);
      const data = await res.json();
      setSurveys(data.surveys || []);
    } catch (e) {
      setError('Could not load surveys. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const loadSurvey = async (survey_id) => {
    try {
      const res = await fetch(`${API}/surveys/${survey_id}`);
      const data = await res.json();
      onSelect(data.survey);
    } catch (e) {
      setError('Failed to load survey details.');
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return (
    <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
      <CircularProgress />
    </Box>
  );

  return (
    <Paper elevation={3} sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" color="primary">Generated Surveys</Typography>
        <Button startIcon={<Refresh />} onClick={load} size="small">Refresh</Button>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {surveys.length === 0 ? (
        <Alert severity="info">No surveys yet. Generate one from the first tab.</Alert>
      ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#e8eaf6' }}>
                <TableCell><strong>Title</strong></TableCell>
                <TableCell><strong>Domain</strong></TableCell>
                <TableCell><strong>Questions</strong></TableCell>
                <TableCell><strong>Status</strong></TableCell>
                <TableCell><strong>Created</strong></TableCell>
                <TableCell></TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {surveys.map(s => (
                <TableRow key={s.survey_id} hover>
                  <TableCell>{s.title}</TableCell>
                  <TableCell>
                    <Chip label={s.domain} size="small" color="primary" />
                  </TableCell>
                  <TableCell>{s.total_questions}</TableCell>
                  <TableCell>
                    <Chip
                      label={s.status}
                      size="small"
                      color={s.status === 'draft' ? 'warning' : 'success'}
                    />
                  </TableCell>
                  <TableCell>
                    {s.created_at ? new Date(s.created_at).toLocaleDateString('en-IN') : '—'}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => loadSurvey(s.survey_id)}
                    >
                      View
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
}
