/**
 * Survey Screen - Adaptive Questionnaire with Voice Input
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import VoiceInput from './VoiceInput';
import ValidationAlert from './ValidationAlert';
import ProgressBar from './ProgressBar';

const API_BASE_URL = 'http://localhost:8004';

const SurveyScreen = ({ token, user, surveyId, language }) => {
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [responses, setResponses] = useState({});
  const [prefillData, setPrefillData] = useState(null);
  const [validationErrors, setValidationErrors] = useState([]);
  const [validationWarnings, setValidationWarnings] = useState([]);

  // Fetch prefill data
  const { data: prefillResponse } = useQuery({
    queryKey: ['prefill', surveyId],
    queryFn: async () => {
      const response = await axios.get(
        `${API_BASE_URL}/survey/${surveyId}/prefill`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return response.data;
    },
    onSuccess: (data) => {
      setPrefillData(data.prefill_data);
    }
  });

  // Fetch survey questions
  const { data: surveyData, isLoading } = useQuery({
    queryKey: ['survey', surveyId, language],
    queryFn: async () => {
      const response = await axios.get(
        `${API_BASE_URL}/survey/${surveyId}?language=${language}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return response.data;
    }
  });

  // Submit survey mutation
  const submitMutation = useMutation({
    mutationFn: async (data) => {
      const response = await axios.post(
        `${API_BASE_URL}/survey/${surveyId}/submit`,
        data,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      return response.data;
    },
    onSuccess: (data) => {
      if (data.success) {
        alert('Survey submitted successfully! Thank you for your participation.');
        // Reset or redirect
      } else {
        setValidationErrors(data.validation.errors);
        setValidationWarnings(data.validation.warnings);
      }
    },
    onError: (error) => {
      alert('Failed to submit survey. Please try again.');
    }
  });

  const questions = surveyData?.questions || [];
  const currentQuestion = questions[currentQuestionIndex];
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;

  const handleResponse = (questionId, value) => {
    setResponses(prev => ({
      ...prev,
      [questionId]: value
    }));
    setValidationErrors([]);
    setValidationWarnings([]);
  };

  const handleNext = () => {
    // Check if current question is answered
    if (currentQuestion.required && !responses[currentQuestion.question_id]) {
      alert('Please answer this question before proceeding');
      return;
    }

    // Check dependencies
    if (currentQuestion.depends_on) {
      const [depQuestionId, depValue] = Object.entries(currentQuestion.depends_on)[0];
      if (responses[depQuestionId] !== depValue) {
        // Skip this question
        if (currentQuestionIndex < questions.length - 1) {
          setCurrentQuestionIndex(prev => prev + 1);
        }
        return;
      }
    }

    if (currentQuestionIndex < questions.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
    } else {
      handleSubmit();
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleSubmit = () => {
    const responseArray = Object.entries(responses).map(([question_id, value]) => ({
      question_id,
      value
    }));

    submitMutation.mutate({
      survey_id: surveyId,
      responses: responseArray,
      location: prefillData?.location,
      metadata: {
        language,
        device: 'web',
        user_agent: navigator.userAgent
      }
    });
  };

  const handleVoiceInput = (transcription) => {
    handleResponse(currentQuestion.question_id, transcription);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading survey...</p>
        </div>
      </div>
    );
  }

  if (!currentQuestion) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-600">No questions available</p>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Progress Bar */}
      <ProgressBar progress={progress} />

      {/* Pre-fill Info Card */}
      {prefillData && currentQuestionIndex === 0 && (
        <div className="bg-gradient-to-r from-green-50 to-blue-50 border-l-4 border-green-500 p-6 rounded-lg mb-6 shadow-md">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-6 w-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-4 flex-1">
              <h3 className="text-lg font-semibold text-gray-900">Welcome {prefillData.name}!</h3>
              <p className="text-sm text-gray-700 mt-2">
                We've pre-filled some information to save your time:
              </p>
              <div className="grid grid-cols-2 gap-4 mt-4">
                <div>
                  <p className="text-xs text-gray-600">Location</p>
                  <p className="font-medium text-gray-900">{prefillData.district}, {prefillData.state}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600">Age Group</p>
                  <p className="font-medium text-gray-900">{prefillData.age_band}</p>
                </div>
                {prefillData.schemes_eligible && prefillData.schemes_eligible.length > 0 && (
                  <div className="col-span-2">
                    <p className="text-xs text-gray-600">Eligible Schemes</p>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {prefillData.schemes_eligible.map(scheme => (
                        <span key={scheme} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                          {scheme}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Validation Alerts */}
      {validationErrors.length > 0 && (
        <ValidationAlert type="error" messages={validationErrors} />
      )}
      {validationWarnings.length > 0 && (
        <ValidationAlert type="warning" messages={validationWarnings} />
      )}

      {/* Question Card */}
      <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Question Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-blue-200 text-sm font-medium">
              Question {currentQuestionIndex + 1} of {questions.length}
            </span>
            <span className="px-3 py-1 bg-blue-800 rounded-full text-xs text-white">
              {currentQuestion.category}
            </span>
          </div>
          <h2 className="text-2xl font-bold text-white">
            {currentQuestion.text}
          </h2>
          {currentQuestion.required && (
            <span className="text-orange-300 text-sm mt-2 inline-block">* Required</span>
          )}
        </div>

        {/* Question Body */}
        <div className="px-8 py-8">
          {/* Single Choice */}
          {currentQuestion.type === 'single_choice' && (
            <div className="space-y-3">
              {currentQuestion.options.map((option, index) => (
                <button
                  key={index}
                  onClick={() => handleResponse(currentQuestion.question_id, option)}
                  className={`w-full text-left px-6 py-4 rounded-lg border-2 transition-all transform hover:scale-102 ${
                    responses[currentQuestion.question_id] === option
                      ? 'border-blue-600 bg-blue-50 shadow-md'
                      : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center">
                    <div className={`w-5 h-5 rounded-full border-2 mr-4 flex items-center justify-center ${
                      responses[currentQuestion.question_id] === option
                        ? 'border-blue-600 bg-blue-600'
                        : 'border-gray-400'
                    }`}>
                      {responses[currentQuestion.question_id] === option && (
                        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                    <span className="font-medium text-gray-900">{option}</span>
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Text Input */}
          {currentQuestion.type === 'text' && (
            <div>
              <textarea
                value={responses[currentQuestion.question_id] || ''}
                onChange={(e) => handleResponse(currentQuestion.question_id, e.target.value)}
                placeholder="Type your answer here..."
                rows="4"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all resize-none"
              />
            </div>
          )}

          {/* Number Input */}
          {currentQuestion.type === 'number' && (
            <div>
              <input
                type="number"
                value={responses[currentQuestion.question_id] || ''}
                onChange={(e) => handleResponse(currentQuestion.question_id, e.target.value)}
                placeholder="Enter number"
                className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-lg"
              />
            </div>
          )}

          {/* Voice Input */}
          <div className="mt-6">
            <VoiceInput
              onTranscription={handleVoiceInput}
              language={language}
              token={token}
            />
          </div>
        </div>

        {/* Navigation */}
        <div className="bg-gray-50 px-8 py-6 border-t flex items-center justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentQuestionIndex === 0}
            className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Previous
          </button>

          <div className="text-sm text-gray-600">
            {surveyData?.estimated_time_minutes && (
              <span>Est. time: {Math.ceil(surveyData.estimated_time_minutes)} min</span>
            )}
          </div>

          <button
            onClick={handleNext}
            disabled={submitMutation.isPending}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {currentQuestionIndex === questions.length - 1 ? (
              submitMutation.isPending ? 'Submitting...' : 'Submit Survey'
            ) : (
              'Next →'
            )}
          </button>
        </div>
      </div>

      {/* Help Text */}
      <div className="mt-6 text-center text-sm text-gray-600">
        <p>Need help? Call our helpline: <span className="font-semibold text-blue-600">1800-XXX-XXXX</span></p>
      </div>
    </div>
  );
};

export default SurveyScreen;
