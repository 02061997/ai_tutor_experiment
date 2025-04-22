// ai_tutor_experiment/frontend/js/modules/api_client.js
// Updated for Phase 5: RAG/LLM Quiz Refactor

'use strict';

// --- Configuration ---
const API_BASE_URL = '/api/v1'; // Relative URL assumes frontend is served by the same origin

/**
 * Reusable helper function to make fetch requests to the backend API.
 * Handles common headers, JSON stringification, response checking, and error handling.
 * @param {string} endpoint - The API endpoint path (e.g., '/consent/session').
 * @param {string} [method='GET'] - The HTTP method (GET, POST, PUT, DELETE).
 * @param {object|null} [body=null] - The request body for POST/PUT requests.
 * @param {object} [headers={}] - Optional additional headers.
 * @returns {Promise<any>} - A promise that resolves with the JSON response body, or null for 204 responses.
 * @throws {Error} - Throws an error if the request fails or response status is not ok (2xx).
 */
async function fetchApi(endpoint, method = 'GET', body = null, headers = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const options = {
        method: method,
        headers: {
            'Accept': 'application/json',
            ...headers,
        },
    };

    if (body) {
        options.body = JSON.stringify(body);
        if (!options.headers['Content-Type']) {
            options.headers['Content-Type'] = 'application/json';
        }
    }

    // TODO: Add Authentication Header Injection if researcher login is implemented
    // const token = sessionStorage.getItem('authToken');
    // if (token) {
    //     options.headers['Authorization'] = `Bearer ${token}`;
    // }

    console.debug(`API Request: ${method} ${url}`, body ? JSON.stringify(body).substring(0, 100) + '...' : '');

    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            let errorBody;
            try {
                errorBody = await response.json();
                // Attempt to extract detail, fallback to statusText or generic message
                let detailMessage = "Unknown error";
                if (errorBody && errorBody.detail) {
                    // Handle cases where detail might be an object (like validation errors)
                    if (typeof errorBody.detail === 'string') {
                        detailMessage = errorBody.detail;
                    } else {
                        // Attempt to stringify or provide a summary
                        try { detailMessage = JSON.stringify(errorBody.detail); } catch { detailMessage = "Complex error object received"; }
                    }
                } else {
                    detailMessage = response.statusText || `HTTP Error ${response.status}`;
                }
                console.error(`API Error Response (${response.status}):`, errorBody);
                throw new Error(detailMessage);

            } catch (e) {
                // Handle cases where response is not JSON or json parsing fails
                console.error(`API Error Response (${response.status}): Cannot parse body. Status: ${response.statusText}`);
                throw new Error(response.statusText || `HTTP error! Status: ${response.status}`);
            }
        }

        if (response.status === 204) {
            console.debug(`API Response (${response.status}): No Content`);
            return null;
        }

        const data = await response.json();
        console.debug(`API Response (${response.status}):`, data);
        return data;

    } catch (error) {
        // Catch fetch errors (network issues) or errors thrown above
        console.error(`Network or API error during fetch to ${url}:`, error.message || error);
        // Re-throw the error message, not the entire error object sometimes
        throw new Error(error.message || 'Network or API error occurred.');
    }
}

// --- Exported API Functions ---

/**
 * Creates a new consent session.
 * Calls: POST /api/v1/consent/session
 * @param {object} consentData - Matching ConsentCreate schema.
 * @returns {Promise<object>} - Matching ConsentRead schema.
 */
export async function createConsentSession(consentData) {
    if (!consentData) throw new Error("Consent data is required.");
    // The consent endpoint should trigger RAG processing on the backend now
    return fetchApi('/consent/session', 'POST', consentData);
}

/**
 * Fetches session details.
 * Calls: GET /api/v1/consent/session/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @returns {Promise<object>} - Session details matching ConsentRead schema.
 */
export async function getSessionDetails(sessionId) {
    if (!sessionId) throw new Error("Session ID is required.");
    return fetchApi(`/consent/session/${sessionId}`);
}



// +++ NEW LLM QUIZ FUNCTIONS +++
/**
 * Gets the next LLM-generated quiz question for the session.
 * Calls: POST /api/v1/quiz/next/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @returns {Promise<object>} - Response matching GeneratedMCQForParticipant schema.
 */
export async function getNextLLMQuestion(sessionId) {
    if (!sessionId) throw new Error("Session ID is required to get the next LLM question.");
    const endpoint = `/quiz/next/${sessionId}`;
    // POST request might be suitable even if no body, or use GET if backend changes
    return fetchApi(endpoint, 'POST');
}

/**
 * Submits an answer for an LLM-generated quiz question.
 * Calls: POST /api/v1/quiz/answer_llm/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {string} mcqId - The UUID of the generated MCQ being answered.
 * @param {string} chosenLetter - The letter ('A', 'B', 'C', 'D') chosen by the user.
 * @returns {Promise<object>} - Response matching GeneratedMCQAnswerFeedback schema.
 */
export async function submitLLMAnswer(sessionId, mcqId, chosenLetter) {
    if (!sessionId) throw new Error("Session ID is required to submit LLM answer.");
    if (!mcqId) throw new Error("MCQ ID is required.");
    if (!chosenLetter || !['A', 'B', 'C', 'D'].includes(chosenLetter.toUpperCase())) {
        throw new Error("Chosen answer letter (A, B, C, or D) is required.");
    }
    const requestBody = {
        mcq_id: mcqId,
        chosen_answer_letter: chosenLetter.toUpperCase()
        // timestamp_frontend could be added here if needed by backend schema
    };
    const endpoint = `/quiz/answer_llm/${sessionId}`;
    return fetchApi(endpoint, 'POST', requestBody);
}
// +++ END NEW LLM QUIZ FUNCTIONS +++


/**
 * Logs a batch of App2 interaction events (clicks, scrolls, PDF events).
 * Calls: POST /api/v1/interaction/log/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {Array<object>} logEntries - Array matching InteractionLogCreate schema.
 * @returns {Promise<object>} - Confirmation message or created logs.
 */
export async function logInteractions(sessionId, logEntries) {
    if (!sessionId) throw new Error("Session ID is required for logging interactions.");
    if (!logEntries || logEntries.length === 0) {
        // console.warn("No App2 interaction log entries to send.");
        return Promise.resolve({ message: "No logs sent." }); // Don't throw error, just resolve
    }
    const batchData = { logs: logEntries };
    // Interaction endpoint might return 201 Created with the logs or just 200/204
    return fetchApi(`/interaction/log/${sessionId}`, 'POST', batchData);
}

/**
 * Submits survey responses (e.g., 'exit' survey).
 * Calls: POST /api/v1/survey/response/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {string} surveyType - The type of survey (e.g., 'exit').
 * @param {object} responses - An object containing question keys and answers.
 * @returns {Promise<object>} - Response matching SurveyResponseRead schema.
 */
export async function submitSurveyResponse(sessionId, surveyType, responses) {
    if (!sessionId) throw new Error("Session ID is required to submit survey.");
    if (!surveyType) throw new Error("Survey type is required.");
    if (!responses) throw new Error("Survey responses are required.");
    const surveyData = { survey_type: surveyType, responses: responses };
    return fetchApi(`/survey/response/${sessionId}`, 'POST', surveyData);
}

/**
 * Submits the collected answers for the final test.
 * Calls: POST /api/v1/final-test/submit/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {object} submissionData - Object matching FinalTestSubmission schema.
 * @returns {Promise<Array<object>>} - List of created response objects matching FinalTestResponseRead schema.
 */
export async function submitFinalTest(sessionId, submissionData) {
    if (!sessionId) throw new Error("Session ID is required to submit final test.");
    if (!submissionData || !submissionData.answers || submissionData.answers.length === 0) {
        throw new Error("Submission data with answers is required.");
    }
    return fetchApi(`/final-test/submit/${sessionId}`, 'POST', submissionData);
}

/**
 * Logs a single App1 interaction event (e.g., UserPrompt, LlmResponse).
 * Calls: POST /api/v1/app1/log/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {object} logData - Data matching App1InteractionLogCreate schema.
 * @returns {Promise<object>} - The created log entry object matching App1InteractionLogRead schema.
 */
export async function logApp1Interaction(sessionId, logData) {
    if (!sessionId) throw new Error("Session ID is required for logging App1 interaction.");
    if (!logData || !logData.event_type) throw new Error("Log data with event_type is required.");
    return fetchApi(`/app1/log/${sessionId}`, 'POST', logData);
}

/**
 * Sends a prompt to the backend App1 LLM endpoint (Groq).
 * Calls: POST /api/v1/app1/llm/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {string} promptText - The user's prompt.
 * @returns {Promise<object>} - Response object matching App1LlmResponse schema (e.g., { response_text: "..." }).
 */
export async function getApp1LlmResponse(sessionId, promptText) {
    if (!sessionId) throw new Error("Session ID is required for LLM interaction.");
    if (!promptText) throw new Error("Prompt text is required.");
    const requestBody = { prompt: promptText }; // Matches App1LlmPromptRequest schema
    return fetchApi(`/app1/llm/${sessionId}`, 'POST', requestBody);
}

/**
 * Requests an AI-generated summary for App2.
 * Calls: POST /api/v1/app2/summary
 * @param {string} textToSummarize - The text content to be summarized.
 * @returns {Promise<object>} - Response object matching SummaryResponse schema (e.g., { summary_text: "..." }).
 */
export async function getApp2Summary(participantId) {
    if (!participantId) throw new Error("Participant ID is required to get summary.");
    // Ensure template literal uses backticks ` `
    const endpoint = `/app2/summary/${participantId}`; // Correct path
    return fetchApi(endpoint, 'GET'); // Correct method
}


/**
 * Ends a participant session.
 * Calls: POST /api/v1/consent/session/{sessionId}/end?status=...
 * @param {string} sessionId - The UUID of the session.
 * @param {string} status - The final status ('Completed', 'Abandoned', 'Error').
 * @returns {Promise<object>} - Updated session details matching ConsentRead schema.
 */
export async function endSession(sessionId, status) {
    if (!sessionId) throw new Error("Session ID is required to end session.");
    if (!status) throw new Error("Final status is required.");
    const endpoint = `/consent/session/${sessionId}/end?status=${encodeURIComponent(status)}`;
    return fetchApi(endpoint, 'POST');
}