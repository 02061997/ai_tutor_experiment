// ai_tutor_experiment/frontend/js/app1_task.js
// Updated version with actual LLM API call and logging

'use strict';

// Import API client functions needed
import * as apiClient from './modules/api_client.js';

// --- DOM References ---
const paperDisplayArea = document.getElementById('paper-display-area');
const paperContentElement = document.getElementById('paper-content');
const assignedPaperNameElement = document.getElementById('assigned-paper-name');
const chatMessagesElement = document.getElementById('chat-messages');
const chatInputElement = document.getElementById('chat-input');
const chatSubmitButton = document.getElementById('chat-submit');
const proceedButton = document.getElementById('proceed-button');

// --- State ---
let sessionId = null;
let assignedPaper = null;

// --- Helper Functions ---

/**
 * Retrieves session info stored during the initial survey step.
 * @returns {object|null} Object with sessionId and assignedPaper, or null if not found.
 */
function getSessionInfo() {
    const id = sessionStorage.getItem('experiment_session_uuid');
    const paper = sessionStorage.getItem('experiment_assigned_paper');
    if (!id) {
        console.error("Session ID not found in sessionStorage.");
        displayError("Critical Error: Session ID is missing. Cannot continue.");
        return null;
    }
     if (!paper) {
        console.error("Assigned Paper not found in sessionStorage.");
        displayError("Warning: Assigned paper information missing.");
    }
    return { sessionId: id, assignedPaper: paper || "Unknown" };
}

/**
 * Displays an error message prominently.
 * @param {string} message - The error message to display.
 */
function displayError(message) {
    let errorDiv = document.getElementById('app1-error-message');
    if (!errorDiv) {
        errorDiv = document.createElement('div');
        errorDiv.id = 'app1-error-message';
        errorDiv.style.color = 'red'; errorDiv.style.fontWeight = 'bold';
        errorDiv.style.padding = '10px'; errorDiv.style.border = '1px solid red';
        errorDiv.style.marginTop = '10px';
        document.querySelector('.app1-container')?.prepend(errorDiv);
    }
    errorDiv.textContent = message;
}

/**
 * Adds a message to the chat display area.
 * @param {string} text - The message text.
 * @param {string} type - 'user', 'llm', or 'system'.
 */
function addChatMessage(text, type) {
    if (!chatMessagesElement) return;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${type}-message`);
    // Basic sanitization (replace potential HTML tags) to prevent XSS if displaying LLM response directly
    // For more robust sanitization, consider a library like DOMPurify.
    const sanitizedText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    messageDiv.innerHTML = sanitizedText.replace(/\n/g, '<br>'); // Display newlines correctly
    // messageDiv.textContent = text; // Use textContent if no newline formatting is needed

    chatMessagesElement.appendChild(messageDiv);
    // Scroll to the bottom
    chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
}

// --- Event Handlers ---

/**
 * Handles submission of chat input.
 */
async function handleChatSubmit() {
    const userPrompt = chatInputElement.value.trim();
    if (!userPrompt || !sessionId) return; // Ignore empty prompts or if session invalid

    addChatMessage(userPrompt, 'user');
    chatInputElement.value = ''; // Clear input field
    chatSubmitButton.disabled = true; // Disable while processing
    addChatMessage("...", 'llm'); // Thinking indicator

    // --- Log User Prompt ---
    const userLogData = { event_type: 'UserPrompt', prompt_text: userPrompt };
    apiClient.logApp1Interaction(sessionId, userLogData)
        .then(log => console.log("User prompt logged:", log.log_id))
        .catch(err => console.error("Failed to log user prompt:", err)); // Log error but continue

    // --- Call Backend for LLM Response ---
    try {
        // Call the new API client function
        const llmResponse = await apiClient.getApp1LlmResponse(sessionId, userPrompt);
        const llmResponseText = llmResponse.response_text; // Extract text from response schema

        // Remove "thinking" indicator and add actual response
        chatMessagesElement.removeChild(chatMessagesElement.lastChild); // Remove the "..."
        addChatMessage(llmResponseText, 'llm');

        // --- Log LLM Response ---
        // TODO: Get actual token counts and timings from backend if implemented there
        const llmLogData = {
            event_type: 'LlmResponse',
            prompt_text: userPrompt, // Log prompt again for context with response
            response_text: llmResponseText
            // token_count_prompt: llmResponse.token_usage?.prompt_tokens, // Example if backend included usage
            // token_count_response: llmResponse.token_usage?.completion_tokens,
            // llm_response_time_ms: llmResponse.timing?.response_time_ms
        };
        apiClient.logApp1Interaction(sessionId, llmLogData)
            .then(log => console.log("LLM response logged:", log.log_id))
            .catch(err => console.error("Failed to log LLM response:", err)); // Log error but continue

    } catch (error) {
        console.error("Error during chat interaction:", error);
        // Remove "thinking" indicator before showing error
        if(chatMessagesElement.lastChild && chatMessagesElement.lastChild.textContent === "...") {
             chatMessagesElement.removeChild(chatMessagesElement.lastChild);
        }
        addChatMessage(`Error: Could not get response. ${error.message}`, 'system');
         // --- Log Error Event ---
         const errorLogData = {
             event_type: 'Error',
             prompt_text: userPrompt, // Log the prompt that caused the error
             error_details: error.message || 'Unknown chat interaction error'
            };
         apiClient.logApp1Interaction(sessionId, errorLogData)
             .then(log => console.log("Error event logged:", log.log_id))
             .catch(err => console.error("Failed to log error event:", err));
    } finally {
        chatSubmitButton.disabled = false; // Re-enable button
        chatInputElement.focus(); // Put focus back in input
    }
    // --- End LLM Interaction ---
}

/**
 * Handles click on the proceed button.
 */
function handleProceed() {
    console.log("Proceed button clicked.");
    proceedButton.disabled = true;
    proceedButton.textContent = "Proceeding...";

    // TODO: Record App1 task end time (via API call - requires endpoint).
    console.log("Placeholder: Recorded App1 task end time.");

    // Redirect to the next step (Final Test page).
    window.location.href = `final_test.html?session=${sessionId}`;
}


// --- Initialization ---
function initApp1Task() {
    console.log("Initializing App 1 Task Environment...");
    const sessionInfo = getSessionInfo();
    if (!sessionInfo) { return; } // Stop if session info is missing
    sessionId = sessionInfo.sessionId;
    assignedPaper = sessionInfo.assignedPaper;

    if (assignedPaperNameElement) { assignedPaperNameElement.textContent = assignedPaper || "Not specified"; }
    // TODO: Load actual paper content into #paper-content
    if (paperContentElement) { paperContentElement.innerHTML = `<p><i>Placeholder for content of paper: ${assignedPaper}</i></p>`; }

    addChatMessage("You can ask the AI assistant questions about the paper presented.", 'system');

    // Attach event listeners
    if (chatSubmitButton) { chatSubmitButton.addEventListener('click', handleChatSubmit); }
    if (chatInputElement) {
        chatInputElement.addEventListener('keydown', (event) => {
            if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleChatSubmit(); }
        });
    }
    if (proceedButton) { proceedButton.addEventListener('click', handleProceed); }

    console.log(`App 1 Task Initialized for Session: ${sessionId}, Paper: ${assignedPaper}`);
}

// --- Run Initialization ---
document.addEventListener('DOMContentLoaded', initApp1Task);
