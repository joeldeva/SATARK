/**
 * Validation Alert Component
 */

import React from 'react';

const ValidationAlert = ({ type, messages }) => {
  const isError = type === 'error';
  
  const bgColor = isError ? 'bg-red-50' : 'bg-yellow-50';
  const borderColor = isError ? 'border-red-500' : 'border-yellow-500';
  const textColor = isError ? 'text-red-700' : 'text-yellow-700';
  const iconColor = isError ? 'text-red-600' : 'text-yellow-600';
  
  return (
    <div className={`${bgColor} border-l-4 ${borderColor} p-4 rounded-lg mb-6 shadow-md`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          {isError ? (
            <svg className={`h-6 w-6 ${iconColor}`} fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className={`h-6 w-6 ${iconColor}`} fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          )}
        </div>
        <div className="ml-4 flex-1">
          <h3 className={`text-sm font-semibold ${textColor}`}>
            {isError ? 'Validation Errors' : 'Warnings'}
          </h3>
          <ul className={`mt-2 text-sm ${textColor} list-disc list-inside space-y-1`}>
            {messages.map((msg, index) => (
              <li key={index}>
                {msg.question_id && <span className="font-medium">{msg.question_id}: </span>}
                {msg.error || msg.warning || msg.message}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default ValidationAlert;
