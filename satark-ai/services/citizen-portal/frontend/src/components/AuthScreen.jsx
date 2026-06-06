/**
 * Authentication Screen - OTP Verification
 */

import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8004';

const AuthScreen = ({ onAuthSuccess, language }) => {
  const [step, setStep] = useState('mobile'); // 'mobile' or 'otp'
  const [mobileNumber, setMobileNumber] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [otpSent, setOtpSent] = useState(false);

  // Initiate OTP mutation
  const initiateMutation = useMutation({
    mutationFn: async (mobile) => {
      const response = await axios.post(`${API_BASE_URL}/auth/initiate`, {
        mobile_number: mobile,
        language: language
      });
      return response.data;
    },
    onSuccess: (data) => {
      setOtpSent(true);
      setStep('otp');
      setError('');
      // Show OTP in development (remove in production)
      alert(`OTP sent! (Dev mode: ${data.otp})`);
    },
    onError: (error) => {
      setError(error.response?.data?.detail || 'Failed to send OTP');
    }
  });

  // Verify OTP mutation
  const verifyMutation = useMutation({
    mutationFn: async ({ mobile, otp }) => {
      const response = await axios.post(`${API_BASE_URL}/auth/verify`, {
        mobile_number: mobile,
        otp: otp
      });
      return response.data;
    },
    onSuccess: (data) => {
      onAuthSuccess(data.token, data.user);
    },
    onError: (error) => {
      setError(error.response?.data?.detail || 'Invalid OTP');
    }
  });

  const handleSendOTP = (e) => {
    e.preventDefault();
    setError('');
    
    // Validate mobile number
    if (!/^[6-9]\d{9}$/.test(mobileNumber)) {
      setError('Please enter a valid 10-digit mobile number');
      return;
    }
    
    initiateMutation.mutate(mobileNumber);
  };

  const handleVerifyOTP = (e) => {
    e.preventDefault();
    setError('');
    
    // Validate OTP
    if (!/^\d{6}$/.test(otp)) {
      setError('Please enter a valid 6-digit OTP');
      return;
    }
    
    verifyMutation.mutate({ mobile: mobileNumber, otp });
  };

  const handleResendOTP = () => {
    setOtp('');
    setError('');
    initiateMutation.mutate(mobileNumber);
  };

  return (
    <div className="max-w-md mx-auto mt-16">
      <div className="bg-white rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-8 py-6">
          <h2 className="text-2xl font-bold text-white text-center">
            {step === 'mobile' ? 'Citizen Login' : 'Verify OTP'}
          </h2>
          <p className="text-blue-100 text-center mt-2 text-sm">
            {step === 'mobile' 
              ? 'Enter your mobile number to receive OTP'
              : `OTP sent to +91 ${mobileNumber}`
            }
          </p>
        </div>

        {/* Form */}
        <div className="px-8 py-8">
          {step === 'mobile' ? (
            <form onSubmit={handleSendOTP} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Mobile Number
                </label>
                <div className="relative">
                  <span className="absolute left-4 top-3.5 text-gray-500">+91</span>
                  <input
                    type="tel"
                    value={mobileNumber}
                    onChange={(e) => setMobileNumber(e.target.value)}
                    placeholder="9876543210"
                    maxLength="10"
                    className="w-full pl-14 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-lg"
                    required
                  />
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  We'll send you a 6-digit OTP for verification
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={initiateMutation.isPending}
                className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold py-3 px-6 rounded-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {initiateMutation.isPending ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Sending OTP...
                  </span>
                ) : (
                  'Send OTP'
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOTP} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Enter OTP
                </label>
                <input
                  type="text"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  maxLength="6"
                  className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all text-center text-2xl tracking-widest font-mono"
                  required
                  autoFocus
                />
                <p className="text-xs text-gray-500 mt-2 text-center">
                  OTP expires in 10 minutes
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={verifyMutation.isPending}
                className="w-full bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white font-semibold py-3 px-6 rounded-lg transition-all transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
              >
                {verifyMutation.isPending ? (
                  <span className="flex items-center justify-center">
                    <svg className="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Verifying...
                  </span>
                ) : (
                  'Verify & Continue'
                )}
              </button>

              <div className="flex items-center justify-between text-sm">
                <button
                  type="button"
                  onClick={() => setStep('mobile')}
                  className="text-blue-600 hover:text-blue-700 font-medium"
                >
                  ← Change Number
                </button>
                <button
                  type="button"
                  onClick={handleResendOTP}
                  disabled={initiateMutation.isPending}
                  className="text-blue-600 hover:text-blue-700 font-medium disabled:opacity-50"
                >
                  Resend OTP
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-8 py-4 border-t">
          <div className="flex items-center justify-center space-x-2 text-xs text-gray-600">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
            </svg>
            <span>Secure authentication via OTP</span>
          </div>
          <p className="text-center text-xs text-gray-500 mt-2">
            Your data is encrypted and protected
          </p>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-3 gap-4 mt-8">
        <div className="bg-white rounded-lg p-4 shadow text-center">
          <div className="text-2xl mb-2">🔒</div>
          <p className="text-xs font-medium text-gray-700">Secure</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow text-center">
          <div className="text-2xl mb-2">🌐</div>
          <p className="text-xs font-medium text-gray-700">Multilingual</p>
        </div>
        <div className="bg-white rounded-lg p-4 shadow text-center">
          <div className="text-2xl mb-2">⚡</div>
          <p className="text-xs font-medium text-gray-700">Fast</p>
        </div>
      </div>
    </div>
  );
};

export default AuthScreen;
