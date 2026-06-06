import React from 'react';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import SurveyDesigner from './components/SurveyDesigner';

// Government-grade theme: Navy Blue + Teal + Neutral Grey
const theme = createTheme({
  palette: {
    primary:    { main: '#1a237e' },
    secondary:  { main: '#00897b' },
    error:      { main: '#c62828' },
    warning:    { main: '#e65100' },
    success:    { main: '#2e7d32' },
    background: { default: '#f5f5f5', paper: '#ffffff' },
    text:       { primary: '#212121', secondary: '#616161' },
  },
  typography: {
    fontFamily: '"Roboto", "Arial", sans-serif',
    h5: { fontWeight: 600, color: '#1a237e' },
    h6: { fontWeight: 500 },
  },
  components: {
    MuiButton: {
      styleOverrides: { root: { textTransform: 'none', borderRadius: 4 } }
    },
    MuiPaper: {
      styleOverrides: { root: { borderRadius: 6 } }
    }
  }
});

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <SurveyDesigner />
    </ThemeProvider>
  );
}
