import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import RespondentApp from './RespondentApp';
import DashboardApp from './DashboardApp';

// Check URL path to determine which app to show
const path = window.location.pathname;
let AppComponent = App;

if (path === '/respond') {
  AppComponent = RespondentApp;
} else if (path === '/dashboard') {
  AppComponent = DashboardApp;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AppComponent />
  </React.StrictMode>
);