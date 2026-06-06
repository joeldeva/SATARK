/**
 * SATARK.AI - Citizen Survey Interface
 * Main React Application
 */

import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AuthScreen from './components/AuthScreen';
import SurveyScreen from './components/SurveyScreen';
import LanguageSelector from './components/LanguageSelector';
import ProgressBar from './components/ProgressBar';
import './App.css';

const queryClient = new QueryClient();

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [language, setLanguage] = useState('en');
  const [surveyId, setSurveyId] = useState('PLFS_2026_001');

  useEffect(() => {
    // Check for existing token in localStorage
    const storedToken = localStorage.getItem('satark_token');
    const storedUser = localStorage.getItem('satark_user');
    
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      setIsAuthenticated(true);
    }
  }, []);

  const handleAuthSuccess = (authToken, userData) => {
    setToken(authToken);
    setUser(userData);
    setIsAuthenticated(true);
    
    // Store in localStorage
    localStorage.setItem('satark_token', authToken);
    localStorage.setItem('satark_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setToken(null);
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('satark_token');
    localStorage.removeItem('satark_user');
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-orange-50">
        {/* Header */}
        <header className="bg-gradient-to-r from-blue-900 to-blue-800 text-white shadow-lg">
          <div className="container mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center">
                  <span className="text-2xl font-bold">सत</span>
                </div>
                <div>
                  <h1 className="text-2xl font-bold">SATARK.AI</h1>
                  <p className="text-sm text-blue-200">सतर्क - National Survey Platform</p>
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <LanguageSelector 
                  language={language} 
                  onChange={setLanguage}
                  disabled={!isAuthenticated}
                />
                
                {isAuthenticated && user && (
                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <p className="text-sm font-medium">{user.name}</p>
                      <p className="text-xs text-blue-200">{user.district}, {user.state}</p>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm font-medium transition-colors"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="container mx-auto px-4 py-8">
          {!isAuthenticated ? (
            <AuthScreen 
              onAuthSuccess={handleAuthSuccess}
              language={language}
            />
          ) : (
            <SurveyScreen
              token={token}
              user={user}
              surveyId={surveyId}
              language={language}
            />
          )}
        </main>

        {/* Footer */}
        <footer className="bg-gray-800 text-white mt-16">
          <div className="container mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm">© 2026 Ministry of Statistics and Programme Implementation</p>
                <p className="text-xs text-gray-400 mt-1">Government of India</p>
              </div>
              <div className="flex items-center space-x-6 text-sm">
                <a href="#" className="hover:text-orange-400 transition-colors">Privacy Policy</a>
                <a href="#" className="hover:text-orange-400 transition-colors">Terms of Service</a>
                <a href="#" className="hover:text-orange-400 transition-colors">Help</a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </QueryClientProvider>
  );
}

export default App;
