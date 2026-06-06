import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Checkbox,
  FormGroup,
  Button,
  Stepper,
  Step,
  StepLabel,
  Alert,
  LinearProgress,
  Chip
} from '@mui/material';
import {
  NavigateNext,
  NavigateBefore,
  Send,
  CheckCircle,
  Person,
  LocationOn
} from '@mui/icons-material';

const SurveyResponseForm = ({ survey, onSubmit }) => {
  const [activeStep, setActiveStep] = useState(0);
  const [responses, setResponses] = useState({});
  const [errors, setErrors] = useState({});
  const [submitted, setSubmitted] = useState(false);

  if (!survey) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography variant="h6" color="text.secondary">
          No survey loaded. Please generate a survey first.
        </Typography>
      </Box>
    );
  }

  const questions = survey.questions || [];
  const currentQuestion = questions[activeStep];
  const progress = ((activeStep + 1) / questions.length) * 100;

  const handleResponseChange = (questionId, value) => {
    setResponses({
      ...responses,
      [questionId]: value
    });
    // Clear error for this question
    if (errors[questionId]) {
      const newErrors = { ...errors };
      delete newErrors[questionId];
      setErrors(newErrors);
    }
  };

  const validateCurrentQuestion = () => {
    if (!currentQuestion) return true;

    const response = responses[currentQuestion.id];
    
    if (currentQuestion.required && (!response || response === '')) {
      setErrors({
        ...errors,
        [currentQuestion.id]: 'This question is required'
      });
      return false;
    }

    // Validate number fields
    if (currentQuestion.type === 'number' && response) {
      const numValue = parseFloat(response);
      if (isNaN(numValue)) {
        setErrors({
          ...errors,
          [currentQuestion.id]: 'Please enter a valid number'
        });
        return false;
      }
      if (currentQuestion.validation) {
        if (currentQuestion.validation.min_value !== null && numValue < currentQuestion.validation.min_value) {
          setErrors({
            ...errors,
            [currentQuestion.id]: `Value must be at least ${currentQuestion.validation.min_value}`
          });
          return false;
        }
        if (currentQuestion.validation.max_value !== null && numValue > currentQuestion.validation.max_value) {
          setErrors({
            ...errors,
            [currentQuestion.id]: `Value must be at most ${currentQuestion.validation.max_value}`
          });
          return false;
        }
      }
    }

    return true;
  };

  const handleNext = () => {
    if (validateCurrentQuestion()) {
      setActiveStep((prevStep) => prevStep + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prevStep) => prevStep - 1);
  };

  const handleSubmit = () => {
    if (validateCurrentQuestion()) {
      // Validate all required questions are answered
      const unansweredRequired = questions.filter(
        q => q.required && (!responses[q.id] || responses[q.id] === '')
      );

      if (unansweredRequired.length > 0) {
        alert(`Please answer all required questions. ${unansweredRequired.length} questions remaining.`);
        return;
      }

      // Format responses for submission
      const formattedResponses = {
        survey_id: survey.survey_id,
        responses: Object.entries(responses).map(([questionId, value]) => ({
          question_id: questionId,
          response_value: value
        })),
        metadata: {
          completed_at: new Date().toISOString(),
          time_taken: Math.floor(Math.random() * 300) + 60, // Placeholder
          device: 'web'
        }
      };

      setSubmitted(true);
      if (onSubmit) {
        onSubmit(formattedResponses);
      }
    }
  };

  const renderQuestionInput = (question) => {
    const response = responses[question.id] || '';
    const error = errors[question.id];

    switch (question.type) {
      case 'single_choice':
        return (
          <FormControl component="fieldset" error={!!error} fullWidth>
            <FormLabel component="legend" sx={{ mb: 2, color: 'text.primary', fontWeight: 500 }}>
              {question.text.en}
              {question.required && <span style={{ color: 'red' }}> *</span>}
            </FormLabel>
            <RadioGroup
              value={response}
              onChange={(e) => handleResponseChange(question.id, e.target.value)}
            >
              {question.options?.map((option) => (
                <FormControlLabel
                  key={option.value}
                  value={option.value}
                  control={<Radio />}
                  label={option.label.en}
                />
              ))}
            </RadioGroup>
            {error && (
              <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                {error}
              </Typography>
            )}
          </FormControl>
        );

      case 'multiple_choice':
        const selectedValues = response ? (Array.isArray(response) ? response : [response]) : [];
        return (
          <FormControl component="fieldset" error={!!error} fullWidth>
            <FormLabel component="legend" sx={{ mb: 2, color: 'text.primary', fontWeight: 500 }}>
              {question.text.en}
              {question.required && <span style={{ color: 'red' }}> *</span>}
            </FormLabel>
            <FormGroup>
              {question.options?.map((option) => (
                <FormControlLabel
                  key={option.value}
                  control={
                    <Checkbox
                      checked={selectedValues.includes(option.value)}
                      onChange={(e) => {
                        const newValues = e.target.checked
                          ? [...selectedValues, option.value]
                          : selectedValues.filter(v => v !== option.value);
                        handleResponseChange(question.id, newValues);
                      }}
                    />
                  }
                  label={option.label.en}
                />
              ))}
            </FormGroup>
            {error && (
              <Typography variant="caption" color="error" sx={{ mt: 1 }}>
                {error}
              </Typography>
            )}
          </FormControl>
        );

      case 'number':
        return (
          <TextField
            fullWidth
            type="number"
            label={question.text.en}
            value={response}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            required={question.required}
            error={!!error}
            helperText={error || (question.validation ? 
              `Range: ${question.validation.min_value || 0} - ${question.validation.max_value || '∞'}` : '')}
            InputProps={{
              inputProps: {
                min: question.validation?.min_value,
                max: question.validation?.max_value
              }
            }}
          />
        );

      case 'text':
        return (
          <TextField
            fullWidth
            multiline
            rows={3}
            label={question.text.en}
            value={response}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            required={question.required}
            error={!!error}
            helperText={error}
          />
        );

      default:
        return (
          <TextField
            fullWidth
            label={question.text.en}
            value={response}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            required={question.required}
            error={!!error}
            helperText={error}
          />
        );
    }
  };

  if (submitted) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <CheckCircle sx={{ fontSize: 80, color: 'success.main', mb: 2 }} />
        <Typography variant="h4" gutterBottom color="success.main">
          Survey Submitted Successfully!
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Thank you for completing the survey. Your responses have been recorded.
        </Typography>
        <Alert severity="success" sx={{ maxWidth: 600, mx: 'auto' }}>
          <strong>Survey ID:</strong> {survey.survey_id}<br />
          <strong>Questions Answered:</strong> {Object.keys(responses).length} / {questions.length}<br />
          <strong>Submitted At:</strong> {new Date().toLocaleString()}
        </Alert>
        <Button
          variant="outlined"
          onClick={() => {
            setSubmitted(false);
            setActiveStep(0);
            setResponses({});
            setErrors({});
          }}
          sx={{ mt: 3 }}
        >
          Fill Another Survey
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Survey Header */}
      <Paper elevation={2} sx={{ p: 3, mb: 3, bgcolor: 'primary.main', color: 'white' }}>
        <Typography variant="h5" gutterBottom>
          {survey.title}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 2 }}>
          <Chip
            icon={<Person />}
            label={`Audience: ${survey.target_audience || 'General'}`}
            size="small"
            sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
          <Chip
            icon={<LocationOn />}
            label={`Domain: ${survey.domain}`}
            size="small"
            sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
          <Chip
            label={`${questions.length} Questions`}
            size="small"
            sx={{ bgcolor: 'rgba(255,255,255,0.2)', color: 'white' }}
          />
        </Box>
      </Paper>

      {/* Progress Bar */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Question {activeStep + 1} of {questions.length}
          </Typography>
          <Typography variant="body2" color="primary" fontWeight="bold">
            {Math.round(progress)}% Complete
          </Typography>
        </Box>
        <LinearProgress variant="determinate" value={progress} sx={{ height: 8, borderRadius: 1 }} />
      </Box>

      {/* Stepper */}
      <Stepper activeStep={activeStep} sx={{ mb: 4, display: { xs: 'none', md: 'flex' } }}>
        {questions.map((question, index) => (
          <Step key={question.id}>
            <StepLabel>Q{index + 1}</StepLabel>
          </Step>
        ))}
      </Stepper>

      {/* Question Card */}
      {currentQuestion && (
        <Paper elevation={3} sx={{ p: 4, mb: 3, minHeight: 300 }}>
          <Box sx={{ mb: 3 }}>
            <Chip
              label={currentQuestion.category}
              size="small"
              color="primary"
              variant="outlined"
              sx={{ mb: 2 }}
            />
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              Question {activeStep + 1} of {questions.length}
            </Typography>
          </Box>

          {renderQuestionInput(currentQuestion)}

          {currentQuestion.tags && currentQuestion.tags.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="caption" color="text.secondary">
                Tags: {currentQuestion.tags.join(', ')}
              </Typography>
            </Box>
          )}
        </Paper>
      )}

      {/* Navigation Buttons */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
        <Button
          variant="outlined"
          onClick={handleBack}
          disabled={activeStep === 0}
          startIcon={<NavigateBefore />}
        >
          Previous
        </Button>

        {activeStep === questions.length - 1 ? (
          <Button
            variant="contained"
            onClick={handleSubmit}
            endIcon={<Send />}
            size="large"
          >
            Submit Survey
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleNext}
            endIcon={<NavigateNext />}
          >
            Next Question
          </Button>
        )}
      </Box>

      {/* Response Summary */}
      <Paper variant="outlined" sx={{ p: 2, mt: 3, bgcolor: 'grey.50' }}>
        <Typography variant="subtitle2" gutterBottom>
          Response Summary:
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Answered: {Object.keys(responses).length} / {questions.length} questions
        </Typography>
        <LinearProgress
          variant="determinate"
          value={(Object.keys(responses).length / questions.length) * 100}
          sx={{ mt: 1 }}
        />
      </Paper>
    </Box>
  );
};

export default SurveyResponseForm;
