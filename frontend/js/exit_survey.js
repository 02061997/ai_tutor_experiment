// frontend/js/exit_survey.js
'use strict';

// Import the necessary API client functions
import { submitSurveyResponse, endSession } from './modules/api_client.js';

// --- DOM References ---
const form = document.getElementById('exit-survey-form');
const submitButton = document.getElementById('submit-exit-button');
const errorMessageDiv = document.getElementById('error-message');
const sessionIdHolder = document.getElementById('session-uuid-holder');

// --- State ---
let sessionId = null;

// --- Helper Functions ---

/**
 * Retrieves session info stored previously.
 * @returns {string|null} The session ID or null if not found.
 */
function getSessionInfo() {
    const id = sessionStorage.getItem('experiment_session_uuid');
    if (!id) {
        console.error("Session ID not found in sessionStorage.");
        displayError("Critical Error: Session ID is missing. Cannot submit survey.");
        return null;
    }
    return id;
}

/**
 * Displays an error message.
 * @param {string} message - The error message to display.
 */
function displayError(message) {
    if(errorMessageDiv) {
        errorMessageDiv.textContent = message;
    } else {
        console.error("Error display element not found. Message:", message);
        alert(message); // Fallback to alert
    }
}

// --- Event Handlers ---

/**
 * Handles the form submission event for the exit survey.
 * @param {Event} event - The form submission event.
 */
async function handleSubmit(event) {
    event.preventDefault();
    errorMessageDiv.textContent = '';
    submitButton.disabled = true;
    submitButton.textContent = 'Submitting...';

    if (!sessionId) {
        displayError("Session ID is missing. Cannot submit.");
        submitButton.disabled = false;
        submitButton.textContent = 'Submit Survey and Finish';
        return;
    }

    // --- Data Collection ---
    const formData = new FormData(form);
    const surveyAnswers = {};
    // Structure answers simply as { input_name: input_value }
    for (const [key, value] of formData.entries()) {
         if (key !== 'session_uuid') { // Exclude hidden session ID field
            surveyAnswers[key] = value;
         }
    }

    console.log("Submitting Exit Survey Answers:", surveyAnswers);

    // --- API Calls ---
    try {
        // 1. Submit the survey data
        await apiClient.submitSurveyResponse(sessionId, 'exit', surveyAnswers);
        console.log("Exit survey submitted successfully.");

        // 2. Mark the overall session as completed
        await apiClient.endSession(sessionId, 'Completed');
        console.log("Session marked as completed.");

        // --- Handle Success: Redirect to Thank You page ---
        // Clear session storage maybe? Or keep for thank you page display?
        // sessionStorage.removeItem('experiment_session_uuid'); // Example cleanup
        window.location.href = `thank_you.html?session=${sessionId}`; // Redirect

    } catch (error) {
        // --- Handle Errors ---
        console.error("Failed to submit exit survey or end session:", error);
        // Provide more specific feedback if possible (e.g., distinguish survey vs endSession error)
        displayError(`Error: ${error.message || 'Could not submit survey. Please try again.'}`);
        submitButton.disabled = false;
        submitButton.textContent = 'Submit Survey and Finish';
    }
}

// --- Initialization ---
function initExitSurvey() {
    console.log("Initializing Exit Survey page...");
    sessionId = getSessionInfo();

    if (!sessionId) {
        if(submitButton) submitButton.disabled = true;
        return;
    }

    // Populate hidden field
    if (sessionIdHolder) {
        sessionIdHolder.value = sessionId;
    }

    // Attach event listener to the form
    if (form) {
        form.addEventListener('submit', handleSubmit);
    } else {
        console.error("Exit survey form element not found!");
    }

    console.log(`Exit Survey page ready for session: ${sessionId}`);
}

// --- Run Initialization ---
document.addEventListener('DOMContentLoaded', initExitSurvey);