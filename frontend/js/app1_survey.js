// frontend/js/app1_survey.js
'use strict';

// Import the necessary API client function
import { createConsentSession } from './modules/api_client.js';

// Get references to form elements
const form = document.getElementById('consent-survey-form');
const submitButton = document.getElementById('submit-button');
const consentCheckbox = document.getElementById('consent');
const errorMessageDiv = document.getElementById('error-message');

/**
 * Handles the form submission event.
 * @param {Event} event - The form submission event.
 */
async function handleSubmit(event) {
    event.preventDefault(); // Prevent default HTML form submission
    errorMessageDiv.textContent = ''; // Clear previous errors
    submitButton.disabled = true; // Disable button during submission
    submitButton.textContent = 'Submitting...';

    // --- Consent Check ---
    if (!consentCheckbox.checked) {
        errorMessageDiv.textContent = 'You must consent to participate before proceeding.';
        submitButton.disabled = false;
        submitButton.textContent = 'Submit and Start';
        return;
    }

    // --- Data Extraction and Structuring ---
    const formData = new FormData(form);
    const consentData = {
        demographics: {},
        baseline_data: {}
    };

    // Iterate through form data and structure it for the API
    for (const [key, value] of formData.entries()) {
        if (key === 'consent') continue; // Skip the consent checkbox itself

        // Assign to correct sub-object based on input name
        if (['full_name','age', 'gender', 'education', 'field_of_study', 'primary_language'].includes(key)) {
            consentData.demographics[key] = value;
        } else if (['llm_experience', 'topic_familiarity'].includes(key)) {
            // Ensure numeric scale values are sent as numbers if appropriate
            // (Backend schema expects Any, so string is okay, but number might be cleaner)
            const numValue = parseInt(value, 10);
            consentData.baseline_data[key] = isNaN(numValue) ? value : numValue;
        }
        // Add handling for other fields if form grows
    }

    console.log("Submitting consent data:", consentData);

    // --- API Call ---
    try {
        const response = await createConsentSession(consentData);
        console.log("Session creation successful:", response);

        // --- Handle Success ---
        if (response && response.session_uuid && response.assigned_app) {
            // Store session ID for later use (e.g., in App1 task or App2)
            // sessionStorage is cleared when the browser tab closes
            // localStorage persists until cleared manually
            sessionStorage.setItem('experiment_session_uuid', response.session_uuid);
            sessionStorage.setItem('experiment_assigned_app', response.assigned_app);
            sessionStorage.setItem('experiment_assigned_paper', response.assigned_paper);


            // Redirect based on assigned app
            if (response.assigned_app === 'App1') {
                // Redirect to the App1 task interface page
                window.location.href = `/app1_task.html?session=${response.session_uuid}`;
                // alert(`Assigned to App1 (Session: ${response.session_uuid}). Redirecting... (App1 Task page not yet implemented)`); // Removed/Commented Out
                // form.innerHTML = `...`; // Removed/Commented Out

            } else if (response.assigned_app === 'App2') {
                // Redirect to the App2 tutoring interface, passing session ID
                window.location.href = `/app2_tutor.html?session=${response.session_uuid}`;
            } else {
                 // Should not happen based on backend logic
                errorMessageDiv.textContent = 'Error: Invalid application assignment received from server.';
                submitButton.disabled = false;
                submitButton.textContent = 'Submit and Start';
            }
        } else {
            throw new Error("Invalid response received from server during session creation.");
        }

    } catch (error) {
        // --- Handle Errors ---
        console.error("Failed to create session:", error);
        errorMessageDiv.textContent = `Error: ${error.message || 'Could not submit form. Please try again.'}`;
        submitButton.disabled = false;
        submitButton.textContent = 'Submit and Start';
    }
}

// Attach event listener to the form
if (form) {
    form.addEventListener('submit', handleSubmit);
} else {
    console.error("Consent form element not found!");
}