import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Button,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Divider,
  Switch,
  FormControlLabel
} from '@mui/material';
import {
  ExpandMore,
  Edit,
  Delete,
  Add,
  DragIndicator,
  Visibility,
  VisibilityOff
} from '@mui/icons-material';

const QUESTION_TYPES = [
  { value: 'single_choice', label: 'Single Choice' },
  { value: 'multiple_choice', label: 'Multiple Choice' },
  { value: 'number', label: 'Number' },
  { value: 'text', label: 'Text' },
  { value: 'date', label: 'Date' },
  { value: 'scale', label: 'Scale (1-5)' }
];

const QUESTION_CATEGORIES = [
  { value: 'demographic', label: 'Demographic', color: 'primary' },
  { value: 'core', label: 'Core', color: 'secondary' },
  { value: 'sensitive', label: 'Sensitive', color: 'warning' },
  { value: 'follow_up', label: 'Follow-up', color: 'info' }
];

function SurveyCanvas({ survey, onSurveyUpdated, loading }) {
  const [editingQuestion, setEditingQuestion] = useState(null);
  const [showJson, setShowJson] = useState(false);
  const [expandedQuestions, setExpandedQuestions] = useState(new Set());

  useEffect(() => {
    if (survey && survey.questions) {
      // Auto-expand first few questions
      const firstThree = new Set(survey.questions.slice(0, 3).map(q => q.id));
      setExpandedQuestions(firstThree);
    }
  }, [survey]);

  if (loading) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="h6" color="text.secondary">
          🤖 AI is generating your survey...
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Applying GSBPM standards and MoSPI compliance
        </Typography>
      </Box>
    );
  }

  if (!survey) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="h6" color="text.secondary">
          👆 Enter a prompt to generate your survey
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Describe your survey requirements in natural language
        </Typography>
      </Box>
    );
  }

  const handleQuestionToggle = (questionId) => {
    const newExpanded = new Set(expandedQuestions);
    if (newExpanded.has(questionId)) {
      newExpanded.delete(questionId);
    } else {
      newExpanded.add(questionId);
    }
    setExpandedQuestions(newExpanded);
  };

  const getCategoryColor = (category) => {
    const categoryInfo = QUESTION_CATEGORIES.find(c => c.value === category);
    return categoryInfo?.color || 'default';
  };

  const renderQuestion = (question, index) => {
    const isExpanded = expandedQuestions.has(question.id);
    
    return (
      <Accordion
        key={question.id}
        expanded={isExpanded}
        onChange={() => handleQuestionToggle(question.id)}
        sx={{ mb: 1 }}
      >
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            <DragIndicator sx={{ mr: 1, color: 'text.secondary' }} />
            <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
              {question.id}: {question.text?.en || 'Untitled Question'}
            </Typography>
            <Chip
              label={question.category}
              size="small"
              color={getCategoryColor(question.category)}
              sx={{ mr: 1 }}
            />
            {question.required && (
              <Chip label="Required" size="small" color="error" variant="outlined" />
            )}
          </Box>
        </AccordionSummary>
        
        <AccordionDetails>
          <Box>
            {/* Question Text */}
            <TextField
              fullWidth
              label="Question Text (English)"
              value={question.text?.en || ''}
              variant="outlined"
              size="small"
              sx={{ mb: 2 }}
              InputProps={{ readOnly: true }}
            />
            
            {/* Hindi Translation if available */}
            {question.text?.hi && (
              <TextField
                fullWidth
                label="Question Text (Hindi)"
                value={question.text.hi}
                variant="outlined"
                size="small"
                sx={{ mb: 2 }}
                InputProps={{ readOnly: true }}
              />
            )}

            {/* Question Type and Category */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Type</InputLabel>
                <Select value={question.type} label="Type" disabled>
                  {QUESTION_TYPES.map(type => (
                    <MenuItem key={type.value} value={type.value}>
                      {type.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Category</InputLabel>
                <Select value={question.category} label="Category" disabled>
                  {QUESTION_CATEGORIES.map(cat => (
                    <MenuItem key={cat.value} value={cat.value}>
                      {cat.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              
              <FormControlLabel
                control={<Switch checked={question.required} disabled />}
                label="Required"
              />
            </Box>

            {/* Options for choice questions */}
            {question.options && question.options.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Answer Options:
                </Typography>
                {question.options.map((option, optIndex) => (
                  <Box key={optIndex} sx={{ display: 'flex', gap: 1, mb: 1 }}>
                    <TextField
                      size="small"
                      label="Value"
                      value={option.value}
                      sx={{ width: 80 }}
                      InputProps={{ readOnly: true }}
                    />
                    <TextField
                      size="small"
                      label="Label (EN)"
                      value={option.label?.en || ''}
                      sx={{ flexGrow: 1 }}
                      InputProps={{ readOnly: true }}
                    />
                    {option.label?.hi && (
                      <TextField
                        size="small"
                        label="Label (HI)"
                        value={option.label.hi}
                        sx={{ flexGrow: 1 }}
                        InputProps={{ readOnly: true }}
                      />
                    )}
                  </Box>
                ))}
              </Box>
            )}

            {/* Validation Rules */}
            {question.validation && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Validation Rules:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  {question.validation.min !== undefined && (
                    <Chip label={`Min: ${question.validation.min}`} size="small" />
                  )}
                  {question.validation.max !== undefined && (
                    <Chip label={`Max: ${question.validation.max}`} size="small" />
                  )}
                  {question.validation.pattern && (
                    <Chip label="Pattern validation" size="small" />
                  )}
                </Box>
              </Box>
            )}

            {/* Routing Logic */}
            {question.routing && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Routing Logic:
                </Typography>
                {question.routing.show_if && (
                  <Alert severity="info" size="small">
                    Show if: {question.routing.show_if}
                  </Alert>
                )}
                {question.routing.skip_to && (
                  <Alert severity="warning" size="small">
                    Skip to: {question.routing.skip_to}
                  </Alert>
                )}
              </Box>
            )}

            {/* Standard Code */}
            {question.standard_code && (
              <Typography variant="caption" color="text.secondary">
                Standard Code: {question.standard_code}
              </Typography>
            )}
          </Box>
        </AccordionDetails>
      </Accordion>
    );
  };

  return (
    <Box>
      {/* Survey Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" gutterBottom>
          {survey.title}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip label={`Domain: ${survey.domain}`} color="primary" />
          <Chip label={`${survey.questions?.length || 0} Questions`} />
          <Chip label={`Languages: ${survey.language?.join(', ')}`} />
          <Chip label={`Standard: ${survey.metadata?.standard}`} color="secondary" />
        </Box>
        
        {survey.target_audience && (
          <Typography variant="body2" color="text.secondary">
            Target Audience: {survey.target_audience}
          </Typography>
        )}
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Action Buttons */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Button
          variant="outlined"
          startIcon={showJson ? <VisibilityOff /> : <Visibility />}
          onClick={() => setShowJson(!showJson)}
          size="small"
        >
          {showJson ? 'Hide JSON' : 'View JSON'}
        </Button>
        <Button variant="outlined" startIcon={<Edit />} size="small" disabled>
          Edit Survey
        </Button>
        <Button variant="outlined" startIcon={<Add />} size="small" disabled>
          Add Question
        </Button>
      </Box>

      {/* JSON View */}
      {showJson && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" gutterBottom>
            Survey JSON (Ready for Deployment):
          </Typography>
          <Box sx={{ maxHeight: 400, overflow: 'auto' }}>
            <pre style={{ 
              backgroundColor: '#f5f5f5', 
              padding: '16px', 
              borderRadius: '4px',
              fontSize: '12px',
              overflow: 'auto'
            }}>
              {JSON.stringify(survey, null, 2)}
            </pre>
          </Box>
        </Box>
      )}

      {/* Questions List */}
      <Typography variant="h6" gutterBottom>
        Survey Questions ({survey.questions?.length || 0})
      </Typography>
      
      {survey.questions && survey.questions.length > 0 ? (
        <Box>
          {survey.questions.map((question, index) => renderQuestion(question, index))}
        </Box>
      ) : (
        <Alert severity="info">
          No questions generated. Try a more detailed prompt.
        </Alert>
      )}

      {/* Survey Footer Info */}
      <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Survey Metadata:
        </Typography>
        <Typography variant="body2" color="text.secondary">
          ID: {survey.survey_id}<br />
          Created: {survey.metadata?.created_at}<br />
          Version: {survey.metadata?.version}<br />
          GSBPM Phase: {survey.metadata?.gsbpm_phase}
        </Typography>
      </Box>
    </Box>
  );
}

export default SurveyCanvas;