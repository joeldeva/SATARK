/**
 * API service for SATARK.AI - Deterministic Survey Intelligence Engine
 */

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

const handleResponse = async (response) => {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorData = null;
    
    try {
      errorData = await response.json();
      errorMessage = errorData.message || errorData.detail || errorMessage;
    } catch (e) {
      // Response is not JSON, use default message
    }
    
    throw new ApiError(errorMessage, response.status, errorData);
  }
  
  return response.json();
};

export const generateSurvey = async (request) => {
  try {
    const response = await fetch(`${API_BASE_URL}/generate-survey`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: request.prompt,
        languages: request.language || ['en'],
        max_questions: request.max_questions || 15,
        domain: request.domain || null,
        include_demographics: request.include_demographics !== false
      }),
    });
    
    const result = await handleResponse(response);
    
    if (!result.success) {
      throw new Error(result.errors?.join(', ') || 'Survey generation failed');
    }
    
    return result;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Failed to generate survey: ${error.message}`);
  }
};

export const analyzeIntent = async (prompt) => {
  try {
    const response = await fetch(`${API_BASE_URL}/analyze-intent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
    });
    
    return handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Failed to analyze intent: ${error.message}`);
  }
};

export const getSystemInfo = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/system-info`);
    return handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Failed to get system info: ${error.message}`);
  }
};

export const getDomains = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/domains`);
    return handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Failed to get domains: ${error.message}`);
  }
};

export const getLanguages = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/languages`);
    return handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Failed to get languages: ${error.message}`);
  }
};

// Health check endpoint
export const healthCheck = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(response);
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new Error(`Health check failed: ${error.message}`);
  }
};