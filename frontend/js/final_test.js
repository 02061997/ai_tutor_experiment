// frontend/js/final_test.js
// Updated version with API call

'use strict';

// Import the necessary API client function
// Make sure submitFinalTest was added to api_client.js
import * as apiClient from './modules/api_client.js';

// --- DOM References ---
const form = document.getElementById('final-test-form');
const submitButton = document.getElementById('submit-test-button');
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
        displayError("Critical Error: Session ID is missing. Cannot submit test.");
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
 * Handles the form submission event for the final test.
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
        submitButton.textContent = 'Submit Final Test';
        return;
    }

    // --- Data Collection and Structuring ---
    const formData = new FormData(form);
    const answersList = [];

    // Structure answers into the list format expected by FinalTestSubmission schema
    for (const [key, value] of formData.entries()) {
         if (key !== 'session_uuid') { // Exclude hidden session ID field
            // Assuming key is the question identifier (e.g., "q1_answer")
            // Store answer value flexibly in user_answer.value for simplicity
            // TODO: Potentially calculate time_per_question_ms if needed
            answersList.push({
                question_id: key,
                user_answer: { value: value }, // Store answer in a nested object
                time_per_question_ms: null // Placeholder for timing
            });
         }
    }

    // Final structure for the API
    const submissionData = {
        answers: answersList
    };

    console.log("Submitting Final Test Answers:", submissionData);

    // --- Actual API Call ---
    try {
        // Call the function added to api_client.js
        await apiClient.submitFinalTest(sessionId, submissionData);

        console.log("Final test submitted successfully.");

        // --- Handle Success: Redirect to next step (Exit Survey) ---
        window.location.href = `exit_survey.html?session=${sessionId}`;

    } catch (error) {
        // --- Handle Errors ---
        console.error("Failed to submit final test:", error);
        displayError(`Error: ${error.message || 'Could not submit test. Please try again.'}`);
        submitButton.disabled = false;
        submitButton.textContent = 'Submit Final Test';
    }
    // --- End API Call ---
}

// --- Initialization ---
function initFinalTest() {
    console.log("Initializing Final Test page...");
    sessionId = getSessionInfo();

    if (!sessionId) {
        if(submitButton) submitButton.disabled = true;
        return;
    }

    // Populate hidden field (optional, as we pass sessionId explicitly in API call now)
    if (sessionIdHolder) {
        sessionIdHolder.value = sessionId;
    }

    // Attach event listener to the form
    if (form) {
        form.addEventListener('submit', handleSubmit);
    } else {
        console.error("Final test form element not found!");
    }

    console.log(`Final Test page ready for session: ${sessionId}`);
}

// --- Run Initialization ---
document.addEventListener('DOMContentLoaded', initFinalTest);