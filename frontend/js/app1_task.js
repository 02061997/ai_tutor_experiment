// ai_tutor_experiment/frontend/js/app1_task.js
// Simplified version: No PDF Viewer, just chat + download link

'use strict';

// --- Module Imports ---
import * as apiClient from './modules/api_client.js';
// Remove PDF Viewer imports
// import * as pdfViewer from './modules/pdf_viewer.js';
// import { GlobalWorkerOptions } from './libs/pdfjs/build/pdf.mjs';

// --- DOM References ---
// Paper Info/Download
const assignedPaperNameElement = document.getElementById('assigned-paper-name');
const pdfDownloadLink = document.getElementById('pdf-download-link'); // Added download link ID
// Chat Interface
const chatMessagesElement = document.getElementById('chat-messages');
const chatInputElement = document.getElementById('chat-input');
const chatSubmitButton = document.getElementById('chat-submit');
// Navigation
const proceedButton = document.getElementById('proceed-button');
// Error Display
const errorMessageDiv = document.getElementById('app1-error-message');

// --- State ---
let sessionId = null;
let assignedPaper = null; // e.g., "Paper1", "Paper2"
let assignedPaperUrl = null; // e.g., "/static/pdfs/chapter1.pdf"

// --- Configuration ---
// Mapping from assigned paper ID to actual PDF file URL
const PDF_FILE_MAP = {
    "Paper1": "/static/pdfs/chapter1.pdf", // Adjust these paths as needed
    "Paper2": "/static/pdfs/chapter2.pdf",   // Add other papers if necessary
};

// --- Helper Functions ---

function getSessionInfo() {
    const id = sessionStorage.getItem('experiment_session_uuid');
    const paper = sessionStorage.getItem('experiment_assigned_paper');
    if (!id) {
        console.error("Session ID not found in sessionStorage.");
        displayError("Critical Error: Session ID is missing. Cannot continue.");
        return null;
    }
    if (!paper) {
        console.warn("Assigned Paper not found in sessionStorage.");
        // Proceed but download link might fail
    }
    return { sessionId: id, assignedPaper: paper || null };
}

function displayError(message) {
    if (errorMessageDiv) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.style.display = 'block';
    }
    console.error(message);
}

function addChatMessage(text, type) {
    if (!chatMessagesElement) return;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${type}-message`);
    const sanitizedText = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
    messageDiv.innerHTML = sanitizedText.replace(/\n/g, '<br>');
    chatMessagesElement.appendChild(messageDiv);
    chatMessagesElement.scrollTop = chatMessagesElement.scrollHeight;
}

// --- PDF Download Link Setup ---
function setupDownloadLink() {
    if (!assignedPaper) {
        displayError("Cannot set download link: Assigned paper is unknown.");
        if(pdfDownloadLink) pdfDownloadLink.style.display = 'none'; // Hide link if no paper
        return;
    }
    assignedPaperUrl = PDF_FILE_MAP[assignedPaper];
    if (!assignedPaperUrl) {
        displayError(`Cannot set download link: No file path configured for paper "${assignedPaper}". Check PDF_FILE_MAP.`);
        if(pdfDownloadLink) pdfDownloadLink.style.display = 'none'; // Hide link if no path
        return;
    }

    if (assignedPaperNameElement) { assignedPaperNameElement.textContent = assignedPaper; }

    if (pdfDownloadLink) {
        pdfDownloadLink.href = assignedPaperUrl;
        // Set the download attribute to suggest a filename
        const filename = assignedPaperUrl.split('/').pop();
        pdfDownloadLink.download = filename || `paper_${assignedPaper}.pdf`;
        pdfDownloadLink.style.display = 'inline'; // Ensure link is visible
        console.log(`Download link set for ${assignedPaper} to ${assignedPaperUrl}`);
    } else {
        console.error("Download link element not found.");
    }
}

// --- Event Handlers ---

async function handleChatSubmit() {
    const userPrompt = chatInputElement.value.trim();
    if (!userPrompt || !sessionId) return;

    addChatMessage(userPrompt, 'user');
    chatInputElement.value = '';
    chatSubmitButton.disabled = true;
    const thinkingMsg = addChatMessage("...", 'llm');

    // Log User Prompt
    const userLogData = { event_type: 'UserPrompt', prompt_text: userPrompt };
    apiClient.logApp1Interaction(sessionId, userLogData)
        .then(log => console.log("User prompt logged:", log.log_id))
        .catch(err => { console.error("Failed to log user prompt:", err); displayError("Warning: Could not log prompt."); });

    // Call Backend
    try {
        // NOTE: This backend call doesn't automatically have paper context yet!
        // Backend app1_service.py needs modification to use RAG based on sessionId.
        const llmResponse = await apiClient.getApp1LlmResponse(sessionId, userPrompt);
        const llmResponseText = llmResponse.response_text;

        if(chatMessagesElement.lastChild && chatMessagesElement.lastChild.textContent === "...") {
            chatMessagesElement.removeChild(chatMessagesElement.lastChild);
        }
        addChatMessage(llmResponseText, 'llm');

        // Log LLM Response
        const llmLogData = { event_type: 'LlmResponse', prompt_text: userPrompt, response_text: llmResponseText };
        apiClient.logApp1Interaction(sessionId, llmLogData)
            .then(log => console.log("LLM response logged:", log.log_id))
            .catch(err => { console.error("Failed to log LLM response:", err); displayError("Warning: Could not log response."); });

    } catch (error) {
        console.error("Error during chat interaction:", error);
        if(chatMessagesElement.lastChild && chatMessagesElement.lastChild.textContent === "...") {
            chatMessagesElement.removeChild(chatMessagesElement.lastChild);
        }
        addChatMessage(`Error: ${error.message}`, 'system');
        // Log Error Event
        const errorLogData = { event_type: 'Error', prompt_text: userPrompt, error_details: error.message || 'Unknown chat interaction error' };
        apiClient.logApp1Interaction(sessionId, errorLogData)
            .then(log => console.log("Error event logged:", log.log_id))
            .catch(err => console.error("Failed to log error event:", err));
    } finally {
        chatSubmitButton.disabled = false;
        chatInputElement.focus();
    }
}

function handleProceed() {
    console.log("Proceed button clicked.");
    proceedButton.disabled = true;
    proceedButton.textContent = "Proceeding...";

    // TODO: Implement API call to log task end time
    console.warn("Placeholder: Task end time not logged. Proceeding directly.");
    window.location.href = `final_test.html?session=${sessionId}`;
}

// --- Initialization ---
function initApp1Task() { // Changed to sync function as PDF init is removed
    console.log("Initializing App 1 Task Environment (Chat Only)...");
    const sessionInfo = getSessionInfo();
    if (!sessionInfo) { return; }
    sessionId = sessionInfo.sessionId;
    assignedPaper = sessionInfo.assignedPaper;

    // Setup download link based on assigned paper
    setupDownloadLink();

    // Setup chat
    addChatMessage("You can ask the AI assistant questions about the paper. Use the download link if you want to view the PDF directly.", 'system');

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