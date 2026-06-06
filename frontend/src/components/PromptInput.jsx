import React, { useState } from 'react';
import {
  TextField,
  Button,
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  OutlinedInput,
  Slider,
  Typography,
  Alert,
  CircularProgress
} from '@mui/material';
import { Send, AutoAwesome } from '@mui/icons-material';
import { generateSurvey } from '../services/api';

const DOMAINS = [
  { value: 'labour', label: 'Labour & Employment' },
  { value: 'health', label: 'Health & Healthcare' },
  { value: 'education', label: 'Education' },
  { value: 'agriculture', label: 'Agriculture' },
  { value: 'household', label: 'Household' },
  { value: 'enterprise', label: 'Enterprise' }
];

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi (हिंदी)' },
  { value: 'bn', label: 'Bengali (বাংলা)' },
  { value: 'te', label: 'Telugu (తెలుగు)' },
  { value: 'ta', label: 'Tamil (தமிழ்)' },
  { value: 'mr', label: 'Marathi (मराठी)' }
];

const EXAMPLE_PROMPTS = [
  "Survey for rural women about healthcare access with income and satisfaction questions",
  "Employment survey for urban youth aged 18-25, focus on job satisfaction and career goals",
  "Health insurance awareness survey for elderly population in Hindi and English",
  "Agricultural practices survey for farmers, include crop types and irrigation methods",
  "Household consumption survey for low-income families with 10 questions",
  "Enterprise survey for MSME owners about business challenges and growth"
];

function PromptInput({ onSurveyGenerated, loading, setLoading }) {
  const [prompt, setPrompt] = useState('');
  const [selectedDomain, setSelectedDomain] = useState('');
  const [selectedLanguages, setSelectedLanguages] = useState(['en']);
  const [maxQuestions, setMaxQuestions] = useState(15);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!prompt.trim()) {
      setError('Please enter a survey description');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const request = {
        prompt: prompt.trim(),
        language: selectedLanguages,
        max_questions: maxQuestions,
        domain: selectedDomain || null,
        include_demographics: true
      };

      const result = await generateSurvey(request);
      onSurveyGenerated(result);
      
    } catch (err) {
      setError(err.message || 'Failed to generate survey');
    } finally {
      setLoading(false);
    }
  };

  const handleExampleClick = (examplePrompt) => {
    setPrompt(examplePrompt);
  };

  const handleLanguageChange = (event) => {
    const value = event.target.value;
    setSelectedLanguages(typeof value === 'string' ? value.split(',') : value);
  };

  return (
    <Box component="form" onSubmit={handleSubmit}>
      {/* Prompt Input */}
      <TextField
        fullWidth
        multiline
        rows={4}
        label="Describe your survey requirements"
        placeholder="e.g., A survey for rural women about access to healthcare with 8 questions, include income and satisfaction"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        variant="outlined"
        sx={{ mb: 2 }}
      />

      {/* Example Prompts */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          Example prompts:
        </Typography>
        {EXAMPLE_PROMPTS.map((example, index) => (
          <Chip
            key={index}
            label={example.substring(0, 50) + '...'}
            variant="outlined"
            size="small"
            onClick={() => handleExampleClick(example)}
            sx={{ mr: 1, mb: 1, cursor: 'pointer' }}
          />
        ))}
      </Box>

      {/* Domain Selection */}
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Domain (Optional)</InputLabel>
        <Select
          value={selectedDomain}
          onChange={(e) => setSelectedDomain(e.target.value)}
          label="Domain (Optional)"
        >
          <MenuItem value="">
            <em>Auto-detect from prompt</em>
          </MenuItem>
          {DOMAINS.map((domain) => (
            <MenuItem key={domain.value} value={domain.value}>
              {domain.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Language Selection */}
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel>Languages</InputLabel>
        <Select
          multiple
          value={selectedLanguages}
          onChange={handleLanguageChange}
          input={<OutlinedInput label="Languages" />}
          renderValue={(selected) => (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {selected.map((value) => {
                const lang = LANGUAGES.find(l => l.value === value);
                return (
                  <Chip key={value} label={lang?.label || value} size="small" />
                );
              })}
            </Box>
          )}
        >
          {LANGUAGES.map((language) => (
            <MenuItem key={language.value} value={language.value}>
              {language.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {/* Max Questions Slider */}
      <Box sx={{ mb: 3 }}>
        <Typography gutterBottom>
          Maximum Questions: {maxQuestions}
        </Typography>
        <Slider
          value={maxQuestions}
          onChange={(e, newValue) => setMaxQuestions(newValue)}
          min={3}
          max={25}
          marks={[
            { value: 3, label: '3' },
            { value: 10, label: '10' },
            { value: 15, label: '15' },
            { value: 25, label: '25' }
          ]}
          valueLabelDisplay="auto"
        />
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        variant="contained"
        fullWidth
        size="large"
        disabled={loading || !prompt.trim()}
        startIcon={loading ? <CircularProgress size={20} /> : <AutoAwesome />}
        sx={{ mb: 2 }}
      >
        {loading ? 'Generating Survey...' : 'Generate Survey'}
      </Button>

      {/* Info */}
      <Typography variant="caption" color="text.secondary">
        🎯 SATARK.AI: Rule Engine + RAG + ML • ⚡ Deterministic • 🔒 No Data Leaks • 🏛️ Government Grade
      </Typography>
    </Box>
  );
}

export default PromptInput;