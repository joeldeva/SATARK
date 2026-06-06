import React, { useState } from 'react';
import {
  Paper, Typography, Box, Chip, Grid, Card, CardContent,
  Divider, Button, Alert, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Accordion,
  AccordionSummary, AccordionDetails
} from '@mui/material';
import { ExpandMore, Download, CheckCircle, Info } from '@mui/icons-material';

const TYPE_COLOR = {
  single_choice: '#1a237e',
  multiple_choice: '#00897b',
  number: '#e65100',
  text: '#4a148c',
  date: '#1b5e20',
};

export default function SurveyPreview({ survey }) {
  const [expanded, setExpanded] = useState('panel0');

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(survey, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${survey.survey_id}.json`;
    a.click();
  };

  return (
    <Box>
      {/* Survey Header */}
      <Paper elevation={3} sx={{ p: 3, mb: 3, borderLeft: '4px solid #1a237e' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 2 }}>
          <Box>
            <Typography variant="h5" gutterBottom>{survey.title}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{survey.description}</Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              <Chip label={survey.domain.toUpperCase()} color="primary" size="small" />
              {survey.target_audience?.map(a => (
                <Chip key={a} label={a} size="small" variant="outlined" />
              ))}
              {survey.location_type && (
                <Chip label={survey.location_type} size="small" color="secondary" />
              )}
              {survey.languages?.map(l => (
                <Chip key={l} label={l.toUpperCase()} size="small" sx={{ bgcolor: '#f5f5f5' }} />
              ))}
            </Box>
          </Box>
          <Button variant="outlined" startIcon={<Download />} onClick={handleExport}>
            Export JSON
          </Button>
        </Box>
      </Paper>

      {/* KPI Row */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Total Questions', value: survey.validation_summary?.total_questions },
          { label: 'Required', value: survey.validation_summary?.required_questions },
          { label: 'Conditional', value: survey.validation_summary?.conditional_questions },
          { label: 'Version', value: survey.version },
        ].map(({ label, value }) => (
          <Grid item xs={6} sm={3} key={label}>
            <Card elevation={2}>
              <CardContent sx={{ textAlign: 'center', py: 2 }}>
                <Typography variant="h4" color="primary">{value}</Typography>
                <Typography variant="caption" color="text.secondary">{label}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Compliance */}
      {survey.metadata?.standards_compliance && (
        <Alert severity="success" icon={<CheckCircle />} sx={{ mb: 3 }}>
          GSBPM Compliant · NSS Standards · Deterministic Generation · Audit Trail Enabled
        </Alert>
      )}

      {/* Questions */}
      <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom color="primary">
          Survey Questions ({survey.questions?.length})
        </Typography>
        <Divider sx={{ mb: 2 }} />

        {survey.questions?.map((q, i) => (
          <Accordion
            key={q.id}
            expanded={expanded === `panel${i}`}
            onChange={(_, isExp) => setExpanded(isExp ? `panel${i}` : false)}
            elevation={1}
            sx={{ mb: 1 }}
          >
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                <Chip
                  label={q.display_id}
                  size="small"
                  sx={{ bgcolor: '#1a237e', color: 'white', minWidth: 40 }}
                />
                <Typography variant="body1" sx={{ flexGrow: 1 }}>{q.text}</Typography>
                <Chip
                  label={q.type?.replace('_', ' ')}
                  size="small"
                  sx={{ bgcolor: TYPE_COLOR[q.type] || '#757575', color: 'white', mr: 1 }}
                />
                {q.required && <Chip label="Required" size="small" color="error" />}
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ bgcolor: '#fafafa' }}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" color="text.secondary">Category</Typography>
                  <Typography variant="body2">{q.category || '—'}</Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" color="text.secondary">Tags</Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                    {q.tags?.map(t => <Chip key={t} label={t} size="small" variant="outlined" />)}
                  </Box>
                </Grid>
                {q.options && (
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.secondary">Options</Typography>
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
                      {q.options.map(o => (
                        <Chip key={o.value} label={`${o.value}. ${o.label}`} size="small" sx={{ bgcolor: '#e8eaf6' }} />
                      ))}
                    </Box>
                  </Grid>
                )}
                {q.validation && (
                  <Grid item xs={12}>
                    <Typography variant="caption" color="text.secondary">Validation</Typography>
                    <Typography variant="body2">
                      Range: {q.validation.min} – {q.validation.max}
                    </Typography>
                  </Grid>
                )}
                {q.standard_code && (
                  <Grid item xs={12}>
                    <Chip icon={<Info />} label={`Standard: ${q.standard_code}`} size="small" color="secondary" />
                  </Grid>
                )}
              </Grid>
            </AccordionDetails>
          </Accordion>
        ))}
      </Paper>

      {/* Skip Logic */}
      {survey.logic?.length > 0 && (
        <Paper elevation={2} sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom color="primary">
            Skip Logic Rules ({survey.logic.length})
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#e8eaf6' }}>
                  <TableCell><strong>Source</strong></TableCell>
                  <TableCell><strong>Condition</strong></TableCell>
                  <TableCell><strong>Action</strong></TableCell>
                  <TableCell><strong>Target</strong></TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {survey.logic.map((rule, i) => (
                  <TableRow key={i}>
                    <TableCell>{rule.source_question}</TableCell>
                    <TableCell><code>{rule.condition}</code></TableCell>
                    <TableCell><Chip label={rule.action} size="small" color="warning" /></TableCell>
                    <TableCell>{rule.target_question}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Paper>
      )}
    </Box>
  );
}
