# SATARK Citizen Mobile App — Developer Integration Guide

This guide describes how to run, connect, and integrate the SATARK Citizen Mobile App prototype (`apps/citizen/`) with the SATARK FastAPI Backend (`apps/api/`).

---

## 1. File Structure

The citizen app is designed as a lightweight, high-performance, mobile-first static app:
- **`index.html`**: Contains the semantic HTML5 layout for all 5 screens (Home, Surveys, History, Alerts, Profile) with inline SVG icons and a modern bottom navigation bar.
- **`styles.css`**: Implementing a premium, clean design system with custom CSS properties, responsive padding/typography, and transitions.
- **`app.js`**: Handles screen navigation logic, search/filters, click actions, and holds mock data arrays (`SURVEYS`, `HISTORY`, `ALERTS`).

Because it is built on vanilla web standards, **there is no build or compiling step required** for the citizen app! It runs directly in any browser.

---

## 2. Running Locally

To run the citizen app:
1. Serve the `apps/citizen` directory with any static HTTP server. For example:
   ```bash
   # Using Node (served by default on port 3002)
   npx serve -l 3002 apps/citizen
   
   # Or using Python 3
   cd apps/citizen
   python -m http.server 3002
   ```
2. Open `http://localhost:3002` in your browser.
3. Open Developer Tools and choose the mobile emulator layout (e.g., iPhone or Android view) for the best experience.

---

## 3. Recommended FastAPI Integration Flow

To make the app fully dynamic, you should hook up the mock data in `app.js` to the live FastAPI backend running at `http://localhost:8001`.

### A. Authentication
Endpoints in the backend require a JWT Bearer token in the `Authorization` header.
- **Action**: Add a simple pin/credential entry on the profile screen (or a separate login page) that hits:
  - **Endpoint**: `POST http://localhost:8001/api/auth/login`
  - **Payload**: `{"username": "sdrd", "password": "design123"}` (or any other seeding roles from the README).
  - **Response**: Store the returned `token` in `localStorage` under `satark_token`.

### B. Fetching Active Surveys
Instead of the static `SURVEYS` array in `app.js`, fetch surveys from the backend:
- **Endpoint**: `GET http://localhost:8001/api/surveys?status=published`
- **Headers**: `{"Authorization": "Bearer <token>"}`
- **Integration**:
  ```javascript
  async function fetchSurveys() {
    try {
      const response = await fetch('http://localhost:8001/api/surveys', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('satark_token')}`
        }
      });
      const data = await response.json();
      
      // Map the backend structure to our UI structure
      SURVEYS.length = 0; // Clear mock data
      data.surveys.forEach(s => {
        SURVEYS.push({
          id: s.id,
          title: s.title?.en || s.id,
          code: s.id,
          ministry: s.metadata?.organization || 'MoSPI',
          status: s.status === 'published' ? 'active' : s.status,
          duration: s.metadata?.duration || '10 min',
          deadline: s.metadata?.deadline || 'Open'
        });
      });
      
      renderSurveys();
    } catch (err) {
      console.error("Failed to fetch surveys:", err);
    }
  }
  ```

### C. Taking a Survey & Submitting Responses
When a citizen taps an active survey card:
1. Render a modal or screen overlay listing the questions inside the survey (`s.nodes` contains the questions array).
2. Gather responses in a key-value format (e.g., `{"q_age": "28", "q_occupation": "Software Engineer"}`).
3. Submit the answers back to the database:
   - **Endpoint**: `POST http://localhost:8001/api/surveys/{survey_id}/responses`
   - **Headers**:
     - `Content-Type: application/json`
     - `Authorization: Bearer <token>`
   - **Payload**:
     ```json
     {
       "householdId": "HH-CIT-1234",
       "respondent_id": "citizen_user",
       "answers": {
         "Q_AGE": "28",
         "Q_OCCUPATION": "NCO-2015-2111"
       },
       "channel": "web",
       "durationSeconds": 120
     }
     ```
   - **Integration Example**:
     ```javascript
     async function submitSurveyAnswers(surveyId, answers) {
       const response = await fetch(`http://localhost:8001/api/surveys/${surveyId}/responses`, {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
           'Authorization': `Bearer ${localStorage.getItem('satark_token')}`
         },
         body: JSON.stringify({
           householdId: 'HH-USER',
           respondent_id: 'citizen_user',
           answers: answers,
           channel: 'citizen-app',
           durationSeconds: 90
         })
       });
       const result = await response.json();
       if (result.success) {
         alert(`Response Recorded! Acknowledgement ID: ${result.response_id}`);
         // Refresh history page
       }
     }
     ```

### D. Fetching History and Alerts
- **History**: Display completed surveys using responses associated with the user by calling `GET http://localhost:8001/api/responses` (filtered by user/household).
- **Alerts**: Listen for real-time notifications by connecting to the server-sent events or notifications endpoint if desired, or query `GET http://localhost:8001/api/alerts` (if implemented).

---

## 4. How to share with your friend
1. Zip the `apps/citizen/` folder containing `index.html`, `styles.css`, `app.js`, and this `INTEGRATION.md`.
2. Share the zip file with your friend.
3. Your friend can unzip it and run the simple serve command (`npx serve`) to begin writing the integration code.
