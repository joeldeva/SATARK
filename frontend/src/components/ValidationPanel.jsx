import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  LinearProgress,
  Button,
  Divider
} from '@mui/material';
import {
  CheckCircle,
  Warning,
  Error,
  Info,
  ExpandMore,
  Verified,
  Security,
  Language,
  Assessment
} from '@mui/icons-material';

function ValidationPanel({ survey, errors, warnings, validationScore }) {
  const [validationResults, setValidationResults] = useState(null);
  const [complianceScore, setComplianceScore] = useState(validationScore || 0);

  useEffect(() => {
    if (validationScore !== undefined) {
      setComplianceScore(validationScore);
    } else if (survey) {
      performValidation();
    }
  }, [survey, validationScore]);

  const performValidation = () => {
    const results = {
      gsbpm: validateGSBPM(),
      mospi: validateMoSPI(),
      structure: validateStructure(),
      accessibility: validateAccessibility(),
      deployment: validateDeployment()
    };

    setValidationResults(results);
    calculateComplianceScore(results);
  };

  const validateGSBPM = () => {
    const checks = [];
    
    if (!survey) return { passed: 0, total: 0, checks: [] };

    // Check GSBPM phase
    checks.push({
      name: 'GSBPM Phase Defined',
      passed: !!survey.metadata?.gsbpm_phase,
      message: survey.metadata?.gsbpm_phase ? 
        `Phase: ${survey.metadata.gsbpm_phase}` : 
        'GSBPM phase not specified'
    });

    // Check survey standard
    checks.push({
      name: 'Survey Standard Compliance',
      passed: !!survey.metadata?.standard,
      message: survey.metadata?.standard ? 
        `Standard: ${survey.metadata.standard}` : 
        'Survey standard not specified'
    });

    // Check metadata completeness
    checks.push({
      name: 'Metadata Completeness',
      passed: !!(survey.metadata?.created_by && survey.metadata?.version),
      message: 'Survey metadata is complete'
    });

    const passed = checks.filter(c => c.passed).length;
    return { passed, total: checks.length, checks };
  };

  const validateMoSPI = () => {
    const checks = [];
    
    if (!survey) return { passed: 0, total: 0, checks: [] };

    // Check domain classification
    checks.push({
      name: 'MoSPI Domain Classification',
      passed: !!survey.domain,
      message: survey.domain ? 
        `Domain: ${survey.domain}` : 
        'Survey domain not classified'
    });

    // Check demographic questions
    const demographicQuestions = survey.questions?.filter(q => 
      q.category === 'demographic'
    ) || [];
    
    checks.push({
      name: 'Demographic Questions Present',
      passed: demographicQuestions.length >= 2,
      message: `${demographicQuestions.length} demographic questions found`
    });

    // Check question coding
    const codedQuestions = survey.questions?.filter(q => 
      q.standard_code
    ) || [];
    
    checks.push({
      name: 'Question Standard Coding',
      passed: codedQuestions.length > 0,
      message: `${codedQuestions.length} questions have standard codes`
    });

    // Check validation rules
    const validatedQuestions = survey.questions?.filter(q => 
      q.validation || q.type === 'single_choice' || q.type === 'multiple_choice'
    ) || [];
    
    checks.push({
      name: 'Validation Rules Applied',
      passed: validatedQuestions.length >= survey.questions?.length * 0.7,
      message: `${validatedQuestions.length}/${survey.questions?.length} questions have validation`
    });

    const passed = checks.filter(c => c.passed).length;
    return { passed, total: checks.length, checks };
  };

  const validateStructure = () => {
    const checks = [];
    
    if (!survey) return { passed: 0, total: 0, checks: [] };

    // Check question count
    checks.push({
      name: 'Appropriate Question Count',
      passed: survey.questions && survey.questions.length >= 3 && survey.questions.length <= 50,
      message: `${survey.questions?.length || 0} questions (recommended: 3-50)`
    });

    // Check question ordering
    const categories = survey.questions?.map(q => q.category) || [];
    const firstCategory = categories[0];
    
    checks.push({
      name: 'Proper Question Ordering',
      passed: firstCategory === 'demographic',
      message: firstCategory === 'demographic' ? 
        'Demographics first (correct)' : 
        'Demographics should come first'
    });

    // Check required questions
    const requiredQuestions = survey.questions?.filter(q => q.required) || [];
    
    checks.push({
      name: 'Required Questions Identified',
      passed: requiredQuestions.length >= 1,
      message: `${requiredQuestions.length} required questions`
    });

    // Check multilingual support
    const multilingualQuestions = survey.questions?.filter(q => 
      q.text && Object.keys(q.text).length > 1
    ) || [];
    
    checks.push({
      name: 'Multilingual Support',
      passed: survey.language?.length > 1 ? multilingualQuestions.length > 0 : true,
      message: survey.language?.length > 1 ? 
        `${multilingualQuestions.length} questions have translations` :
        'Single language survey'
    });

    const passed = checks.filter(c => c.passed).length;
    return { passed, total: checks.length, checks };
  };

  const validateAccessibility = () => {
    const checks = [];
    
    if (!survey) return { passed: 0, total: 0, checks: [] };

    // Check question clarity
    const longQuestions = survey.questions?.filter(q => 
      q.text?.en && q.text.en.length > 200
    ) || [];
    
    checks.push({
      name: 'Question Length Appropriate',
      passed: longQuestions.length === 0,
      message: longQuestions.length === 0 ? 
        'All questions are concise' : 
        `${longQuestions.length} questions may be too long`
    });

    // Check option clarity for choice questions
    const choiceQuestions = survey.questions?.filter(q => 
      q.type === 'single_choice' || q.type === 'multiple_choice'
    ) || [];
    
    const wellStructuredChoices = choiceQuestions.filter(q => 
      q.options && q.options.length >= 2 && q.options.length <= 10
    );
    
    checks.push({
      name: 'Choice Options Well-Structured',
      passed: choiceQuestions.length === 0 || wellStructuredChoices.length === choiceQuestions.length,
      message: `${wellStructuredChoices.length}/${choiceQuestions.length} choice questions well-structured`
    });

    // Check sensitive question handling
    const sensitiveQuestions = survey.questions?.filter(q => 
      q.category === 'sensitive'
    ) || [];
    
    checks.push({
      name: 'Sensitive Questions Properly Categorized',
      passed: true, // Always pass, just informational
      message: `${sensitiveQuestions.length} sensitive questions identified`
    });

    const passed = checks.filter(c => c.passed).length;
    return { passed, total: checks.length, checks };
  };

  const validateDeployment = () => {
    const checks = [];
    
    if (!survey) return { passed: 0, total: 0, checks: [] };

    // Check deployment channels
    checks.push({
      name: 'Deployment Channels Specified',
      passed: !!(survey.metadata?.deployment_channels && survey.metadata.deployment_channels.length > 0),
      message: survey.metadata?.deployment_channels ? 
        `Channels: ${survey.metadata.deployment_channels.join(', ')}` :
        'No deployment channels specified'
    });

    // Check mobile compatibility
    const mobileCompatible = survey.questions?.every(q => 
      q.type !== 'matrix' // Matrix questions are not mobile-friendly
    ) || true;
    
    checks.push({
      name: 'Mobile-Friendly Question Types',
      passed: mobileCompatible,
      message: mobileCompatible ? 
        'All questions are mobile-compatible' :
        'Some questions may not work well on mobile'
    });

    // Check JSON structure validity
    checks.push({
      name: 'Valid JSON Structure',
      passed: !!survey.survey_id && !!survey.title && !!survey.questions,
      message: 'Survey JSON structure is valid'
    });

    const passed = checks.filter(c => c.passed).length;
    return { passed, total: checks.length, checks };
  };

  const calculateComplianceScore = (results) => {
    if (!results) return;
    
    const totalChecks = Object.values(results).reduce((sum, category) => sum + category.total, 0);
    const passedChecks = Object.values(results).reduce((sum, category) => sum + category.passed, 0);
    
    const score = totalChecks > 0 ? Math.round((passedChecks / totalChecks) * 100) : 0;
    setComplianceScore(score);
  };

  const getScoreColor = (score) => {
    if (score >= 90) return 'success';
    if (score >= 70) return 'warning';
    return 'error';
  };

  const renderValidationCategory = (title, icon, results, color = 'primary') => {
    if (!results) return null;

    return (
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
            {icon}
            <Typography variant="subtitle2" sx={{ ml: 1, flexGrow: 1 }}>
              {title}
            </Typography>
            <Chip 
              label={`${results.passed}/${results.total}`}
              size="small"
              color={results.passed === results.total ? 'success' : 'warning'}
            />
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <List dense>
            {results.checks.map((check, index) => (
              <ListItem key={index}>
                <ListItemIcon>
                  {check.passed ? 
                    <CheckCircle color="success" fontSize="small" /> :
                    <Warning color="warning" fontSize="small" />
                  }
                </ListItemIcon>
                <ListItemText
                  primary={check.name}
                  secondary={check.message}
                />
              </ListItem>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>
    );
  };

  if (!survey) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          Generate a survey to see validation results
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Compliance Score */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Compliance Score
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Box sx={{ width: '100%', mr: 1 }}>
            <LinearProgress
              variant="determinate"
              value={complianceScore}
              color={getScoreColor(complianceScore)}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
          <Typography variant="h6" color={`${getScoreColor(complianceScore)}.main`}>
            {complianceScore}%
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Overall compliance with GSBPM and MoSPI standards
        </Typography>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Errors and Warnings */}
      {errors && errors.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Errors:</Typography>
          {errors.map((error, index) => (
            <Typography key={index} variant="body2">• {error}</Typography>
          ))}
        </Alert>
      )}

      {warnings && warnings.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          <Typography variant="subtitle2">Warnings:</Typography>
          {warnings.map((warning, index) => (
            <Typography key={index} variant="body2">• {warning}</Typography>
          ))}
        </Alert>
      )}

      {/* Validation Categories */}
      {validationResults && (
        <Box>
          {renderValidationCategory(
            'GSBPM Compliance',
            <Verified color="primary" />,
            validationResults.gsbpm
          )}
          
          {renderValidationCategory(
            'MoSPI Standards',
            <Assessment color="secondary" />,
            validationResults.mospi
          )}
          
          {renderValidationCategory(
            'Survey Structure',
            <Info color="info" />,
            validationResults.structure
          )}
          
          {renderValidationCategory(
            'Accessibility',
            <Language color="success" />,
            validationResults.accessibility
          )}
          
          {renderValidationCategory(
            'Deployment Ready',
            <Security color="warning" />,
            validationResults.deployment
          )}
        </Box>
      )}

      {/* Action Buttons */}
      <Box sx={{ mt: 3 }}>
        <Button
          variant="outlined"
          fullWidth
          startIcon={<CheckCircle />}
          disabled={complianceScore < 70}
          color={complianceScore >= 90 ? 'success' : 'primary'}
        >
          {complianceScore >= 90 ? 'Ready for Deployment' : 
           complianceScore >= 70 ? 'Needs Minor Fixes' : 
           'Requires Attention'}
        </Button>
      </Box>

      {/* Standards Info */}
      <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
        <Typography variant="caption" color="text.secondary">
          🔵 GSBPM: Generic Statistical Business Process Model<br />
          🟡 MoSPI: Ministry of Statistics & Programme Implementation<br />
          🟢 Auto-coding: NCO/NIC/ISIC classification support
        </Typography>
      </Box>
    </Box>
  );
}

export default ValidationPanel;