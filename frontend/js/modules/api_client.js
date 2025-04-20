// ai_tutor_experiment/frontend/js/modules/api_client.js
// Complete version including App1 LLM function.

'use strict';

// --- Configuration ---
const API_BASE_URL = '/api/v1'; // Relative URL assumes frontend is served by the same origin

/**
 * Reusable helper function to make fetch requests to the backend API.
 * Handles common headers, JSON stringification, response checking, and error handling.
 * @param {string} endpoint - The API endpoint path (e.g., '/quiz/start/session-id').
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

    // TODO: Add Authorization header if authentication is implemented
    // const token = sessionStorage.getItem('authToken');
    // if (token) {
    //     options.headers['Authorization'] = `Bearer ${token}`;
    // }

    console.debug(`API Request: ${method} ${url}`, body ? options.body : '');

    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            let errorBody;
            try { errorBody = await response.json(); } catch (e) { errorBody = { detail: response.statusText || `HTTP Error ${response.status}` }; }
            console.error(`API Error Response (${response.status}):`, errorBody);
            throw new Error(errorBody.detail || `HTTP error! Status: ${response.status}`);
        }
        if (response.status === 204) {
            console.debug(`API Response (${response.status}): No Content`);
            return null;
        }
        const data = await response.json();
        console.debug(`API Response (${response.status}):`, data);
        return data;
    } catch (error) {
        console.error(`Network or API error during fetch to ${url}:`, error);
        throw error;
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

/**
 * Starts a new quiz attempt for App2.
 * Calls: POST /api/v1/quiz/start/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {string|null} [quizId=null] - Optional quiz identifier.
 * @returns {Promise<object>} - Response matching QuizStartResponse schema.
 */
export async function startQuiz(sessionId, quizId = null) {
    if (!sessionId) throw new Error("Session ID is required to start quiz.");
    let endpoint = `/quiz/start/${sessionId}`;
    if (quizId) {
        endpoint += `?quiz_id=${encodeURIComponent(quizId)}`;
    }
    return fetchApi(endpoint, 'POST');
}

/**
 * Submits an answer for the App2 adaptive quiz.
 * Calls: POST /api/v1/quiz/answer/{attemptId}
 * @param {string} attemptId - The UUID of the quiz attempt.
 * @param {object} answerData - Data matching QuizAnswerInput schema.
 * @returns {Promise<object>} - Response matching QuizNextQuestionResponse schema.
 */
export async function submitQuizAnswer(attemptId, answerData) {
    if (!attemptId) throw new Error("Attempt ID is required to submit answer.");
    if (!answerData) throw new Error("Answer data is required.");
    return fetchApi(`/quiz/answer/${attemptId}`, 'POST', answerData);
}

/**
 * Logs a batch of App2 interaction events (clicks, scrolls, PDF events).
 * Calls: POST /api/v1/interaction/log/{sessionId}
 * @param {string} sessionId - The UUID of the session.
 * @param {Array<object>} logEntries - Array matching InteractionLogCreate schema.
 * @returns {Promise<object>} - Confirmation message from the backend.
 */
export async function logInteractions(sessionId, logEntries) {
    if (!sessionId) throw new Error("Session ID is required for logging interactions.");
    if (!logEntries || logEntries.length === 0) {
        console.warn("No App2 interaction log entries to send.");
        return Promise.resolve({ message: "No logs sent." });
    }
    const batchData = { logs: logEntries };
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


// --- Functions still needed / Placeholders ---

// TODO: Add function to handle researcher login (POST /api/v1/auth/token)
// export async function loginResearcher(username, password) { ... }

// TODO: Add function for App2 data download trigger (e.g., GET /api/v1/data-download/{session_uuid})
// export async function downloadDataSummary(sessionId) { ... }

