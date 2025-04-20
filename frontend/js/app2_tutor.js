// frontend/js/app2_tutor.js
// Updated for 3-Step Flow & Correct Module Imports
'use strict';

// --- Module Imports ---
import * as apiClient from './modules/api_client.js';
import * as pdfViewer from './modules/pdf_viewer.js';
import * as pdfTracker from './modules/pdf_tracker.js';
import * as heatmapTracker from './modules/heatmap_tracker.js';
import * as quizUi from './modules/quiz_ui.js';

// **** Import specific component from pdf.mjs ****
// Path is relative to THIS file (app2_tutor.js is in js/)
import { GlobalWorkerOptions } from './libs/pdfjs/build/pdf.mjs';

// --- DOM References ---
// View Containers
const learningInterfaceView = document.getElementById('learning-interface-view');
const quizContainer = document.getElementById('quiz-container');
const recommendationsView = document.getElementById('recommendations-view');
// Learning View Elements
const assignedPaperNameElement = document.getElementById('assigned-paper-name');
const summaryContentElement = document.getElementById('summary-content');
const proceedToQuizButton = document.getElementById('proceed-to-quiz-button');
// Quiz View Elements
const showRecommendationsButton = document.getElementById('show-recommendations-button');
// Recommendations View Elements
const recommendationsListElement = document.getElementById('recommendations-list');
const reviewPaperButton = document.getElementById('review-paper-button');
const reviewQuizButton = document.getElementById('review-quiz-button');
const takeFinalTestButton = document.getElementById('take-final-test-button');

// --- Global State ---
let currentSessionId = null;
let currentAttemptId = null; // For the quiz
let assignedPaperUrl = null;
let quizResultsData = null; // Store quiz results for recommendations

// --- Configuration ---
// Path to pdf.js worker (relative to HTML, used by the worker loader)
const PDF_WORKER_SRC = 'js/libs/pdfjs/build/pdf.worker.mjs';

// --- Helper Functions ---

/**
 * Retrieves session ID from URL query parameter ?session=...
 * @returns {string|null} Session ID or null if not found.
 */
function getSessionIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session');
    if (!sessionId) {
        console.error("Session ID not found in URL.");
        document.body.innerHTML = '<h1>Error: Session ID missing. Cannot start application.</h1>';
        return null;
    }
    console.log("Retrieved Session ID:", sessionId);
    return sessionId;
}

/**
 * Shows the specified view div and hides the others.
 * @param {string} viewId - The ID of the view container div to show ('learning-interface-view', 'quiz-container', 'recommendations-view').
 */
function showView(viewId) {
    const views = [learningInterfaceView, quizContainer, recommendationsView];
    views.forEach(view => {
        if (view) { // Check if element exists
            view.style.display = (view.id === viewId) ? 'block' : 'none';
        } else {
            console.warn(`View element with ID potentially matching ${viewId} not found.`);
        }
    });
    console.log(`Switched view to: ${viewId}`);
}

// --- Initialization Function ---
async function initApp() {
    console.log("Initializing App 2 Tutor Environment...");
    currentSessionId = getSessionIdFromUrl();
    if (!currentSessionId) return;

    // **** Configure PDF.js worker using imported object ****
    // Check if the imported GlobalWorkerOptions exists
    if (typeof GlobalWorkerOptions !== 'undefined') {
        GlobalWorkerOptions.workerSrc = PDF_WORKER_SRC;
        console.log("PDF.js worker source set via GlobalWorkerOptions.");
    } else {
        // This case should ideally not happen if pdf.mjs loaded correctly as a module
        console.error("PDF.js GlobalWorkerOptions is not available. Worker path not set.");
        document.body.innerHTML = '<h1>Error: PDF Library components failed to load.</h1>';
        return; // Stop initialization if PDF.js components aren't loaded
    }
    // **** End PDF worker config ****

    try {
        // Show only the learning interface initially
        showView('learning-interface-view');

        // Fetch Initial Session Data (Placeholder - determine actual PDF URL)
        // Example: Use session details if available, otherwise default
        // try {
        //     const sessionDetails = await apiClient.getSessionDetails(currentSessionId);
        //     assignedPaperUrl = sessionDetails.assignedPaper === 'Paper1' ? '/static/pdfs/paper1.pdf' : '/static/pdfs/paper2.pdf'; // Adjust paths
        // } catch (e) {
        //     console.warn("Could not fetch session details, using default paper.", e);
             assignedPaperUrl = '/static/pdfs/chapter1.pdf'; // Default Placeholder - ADJUST PATH AS NEEDED
        // }

        if (assignedPaperNameElement) {
            assignedPaperNameElement.textContent = assignedPaperUrl.split('/').pop();
        } else {
             console.warn("Element 'assigned-paper-name' not found.");
        }


        // Initialize PDF Viewer (pdf_viewer.js now imports its own dependencies)
        // This will load and render the first page
        await pdfViewer.initPdfViewer({
            containerId: 'pdf-viewer-area', canvasId: 'pdf-canvas', textLayerId: 'text-layer',
            pdfUrl: assignedPaperUrl,
            prevButtonId: 'prev-page', nextButtonId: 'next-page',
            pageNumSpanId: 'page-num', pageCountSpanId: 'page-count',
        });
        console.log("PDF Viewer Initialized.");

        // Initialize Interaction Trackers (can start tracking learning view now)
        pdfTracker.initPdfInteractionTracker(currentSessionId, 'pdf-viewer-area', assignedPaperUrl);
        heatmapTracker.initHeatmapTracker(currentSessionId, 'pdf-viewer-area');
        console.log("Interaction Trackers Initialized.");

        // Fetch and display AI Summary (Placeholder)
        await fetchAndDisplaySummary();

        // Initialize Quiz UI module (it will be hidden initially by CSS/showView)
        quizUi.initQuizUi({
            questionContainerId: 'quiz-question-container',
            feedbackContainerId: 'quiz-feedback-container',
            submitButtonId: 'submit-answer-button',
            onAnswerSubmit: handleQuizAnswerSubmit // Pass the callback
        });
        console.log("Quiz UI Initialized (but hidden).");

        // Add event listener for the "Start Quiz" button
        proceedToQuizButton?.addEventListener('click', startQuizPhase);


    } catch (error) {
        console.error("Initialization failed:", error);
        // Use querySelector for potentially missing container
        const mainContainer = document.querySelector('.app2-main-container');
        if(mainContainer) mainContainer.innerHTML = `<h1>Application Initialization Failed</h1><p>${error.message}</p>`;
    }
}

/**
 * Fetches and displays the AI-generated summary (Placeholder).
 */
async function fetchAndDisplaySummary() {
    if (!summaryContentElement) return;
    summaryContentElement.innerHTML = '<p><i>Fetching summary from AI...</i></p>';
    try {
        // TODO: Implement backend endpoint and API client function for summary
        // const summaryResponse = await apiClient.getApp2Summary(currentSessionId, assignedPaperUrl);
        // const summaryText = summaryResponse.summary_text;

        // Placeholder:
        await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
        const summaryText = `This is a placeholder summary for ${assignedPaperUrl}. The actual summary would be generated by Gemini Flash based on the paper content. It would provide a concise overview of the main points, findings, and conclusions presented in the research paper.`;
        // End Placeholder

        // Display summary
        summaryContentElement.innerHTML = ''; // Clear loading message
        const summaryPara = document.createElement('p');
        summaryPara.style.whiteSpace = 'pre-wrap'; // Preserve line breaks
        summaryPara.textContent = summaryText;
        summaryContentElement.appendChild(summaryPara);

    } catch (error) {
        console.error("Failed to fetch or display summary:", error);
        summaryContentElement.innerHTML = `<p style="color: red;">Error loading summary: ${error.message}</p>`;
    }
}


/**
 * Handles the transition to the quiz phase.
 */
async function startQuizPhase() {
    console.log("Starting Quiz Phase...");
    showView('quiz-container'); // Show the quiz container, hide others

    // Disable button after clicking
    if(proceedToQuizButton) {
        proceedToQuizButton.disabled = true;
        proceedToQuizButton.textContent = 'Quiz in Progress...';
    }

    try {
        // Start the quiz via API
        const startResponse = await apiClient.startQuiz(currentSessionId /*, optionalQuizId */);
        if (startResponse && startResponse.attempt_id && startResponse.first_question) {
            currentAttemptId = startResponse.attempt_id;
            console.log("Quiz started via API. Attempt ID:", currentAttemptId);
            // Display the first question using the initialized Quiz UI module
            quizUi.displayQuestion(startResponse.first_question);
        } else {
            // Handle cases where the API response might be invalid
            throw new Error("Failed to start quiz or received invalid response from API.");
        }
    } catch (error) {
        console.error("Failed to start quiz phase:", error);
        quizUi.showFeedback(`Error starting quiz: ${error.message}`, true);
        // Optionally switch back to learning view or show error prominently
        showView('learning-interface-view'); // Example: Go back on error
        if(proceedToQuizButton){ // Re-enable the button if going back
            proceedToQuizButton.disabled = false;
            proceedToQuizButton.textContent = 'Start Quiz';
        }
    }
}

/**
 * Callback function passed to Quiz UI, handles answer submission result.
 * @param {object} selectedAnswer - Object like { question_id: '...', selected_option_index: 0 }
 */
async function handleQuizAnswerSubmit(selectedAnswer) {
    console.log("Orchestrator: Submitting answer:", selectedAnswer);
    if (!currentAttemptId || selectedAnswer === null) {
        console.error("Cannot submit answer: Missing attempt ID or answer data.");
        quizUi.showFeedback("Error: Could not submit answer. Invalid data.", true);
        return;
    }

    // Disable submit button while processing via Quiz UI module
    quizUi.setSubmitButtonState(false);
    quizUi.clearFeedback(); // Clear previous feedback

    try {
        // Submit answer via API client
        const response = await apiClient.submitQuizAnswer(currentAttemptId, selectedAnswer);

        // Check if the quiz is complete based on the response
        if (response.is_complete) {
            console.log("Orchestrator: Quiz Complete!", response);
            quizResultsData = response; // Store results for recommendations phase
            quizUi.displayCompletion(response); // Update UI to show completion message/final score

            // Make the "Show Recommendations" button visible and add listener
            if (showRecommendationsButton) {
                showRecommendationsButton.style.display = 'inline-block';
                showRecommendationsButton.disabled = false;
                // Use replaceWith(cloneNode(true)) to ensure only one listener is attached
                const newButton = showRecommendationsButton.cloneNode(true);
                showRecommendationsButton.parentNode.replaceChild(newButton, showRecommendationsButton);
                newButton.addEventListener('click', startRecommendationsPhase);
            }
            // Keep quiz answer submit button disabled after completion
            quizUi.setSubmitButtonState(false);

        } else if (response.next_question) {
            // If quiz not complete, display the next question
            console.log("Orchestrator: Displaying next question.");
            quizUi.displayQuestion(response.next_question); // Quiz UI should handle re-enabling submit button
        } else {
             // Handle unexpected response structure
             console.error("Orchestrator: Invalid response from submitQuizAnswer:", response);
             quizUi.showFeedback("Error: Received invalid response from server.", true);
             quizUi.setSubmitButtonState(true); // Re-enable on unexpected error
        }

    } catch (error) {
        console.error("Orchestrator: Error submitting quiz answer:", error);
        quizUi.showFeedback(`Error submitting answer: ${error.message || 'Please try again.'}`, true);
        quizUi.setSubmitButtonState(true); // Re-enable button on error
    }
}

/**
 * Handles the transition to the recommendations phase.
 */
async function startRecommendationsPhase() {
     console.log("Starting Recommendations Phase...");
     showView('recommendations-view'); // Show recommendations container

     if (!recommendationsListElement) return;
     recommendationsListElement.innerHTML = '<li><i>Loading recommendations based on quiz results...</i></li>';

     try {
         // --- Placeholder for fetching Recommendations ---
         // TODO: 1. Implement backend endpoint/service to generate recommendations based on quizResultsData (e.g., weak topics) using Gemini.
         // TODO: 2. Add function to api_client.js (e.g., getRecommendations(sessionId, attemptId))
         // TODO: 3. Call API client here:
         // const recommendationsResponse = await apiClient.getRecommendations(sessionId, currentAttemptId);
         // const recommendations = recommendationsResponse.recommendations || []; // Assuming response structure

         // Placeholder: Use weak topics directly from quiz results if available
         const recommendations = quizResultsData?.identified_weak_topics || ["No specific topics identified for review (placeholder)."];
         await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
         // --- End Placeholder ---

         // Display recommendations
         recommendationsListElement.innerHTML = ''; // Clear loading message
         if (recommendations && recommendations.length > 0 && recommendations[0] !== "No specific topics identified for review (placeholder).") {
             recommendations.forEach(topic => {
                 const li = document.createElement('li');
                 li.textContent = topic; // Consider escaping if topic names could contain HTML
                 recommendationsListElement.appendChild(li);
             });
         } else {
             recommendationsListElement.innerHTML = '<li>No specific recommendations available at this time.</li>';
         }

         // Add event listeners for navigation buttons within recommendations view
         reviewPaperButton?.addEventListener('click', () => showView('learning-interface-view'));
         reviewQuizButton?.addEventListener('click', () => showView('quiz-container')); // Note: Quiz state isn't reset here, shows completion view
         takeFinalTestButton?.addEventListener('click', () => {
             console.log("Proceeding to Final Test...");
             window.location.href = `final_test.html?session=${currentSessionId}`; // Redirect to final test page
         });

     } catch (error) {
         console.error("Failed to load or display recommendations:", error);
         recommendationsListElement.innerHTML = `<li style="color: red;">Error loading recommendations: ${error.message}</li>`;
     }
}


// --- Application Entry Point ---
document.addEventListener('DOMContentLoaded', initApp);

// --- Unload Listener ---
// Tries to send any remaining buffered interactions before the page unloads
window.addEventListener('beforeunload', () => {
    // Check if tracker modules and functions exist before calling
    if (typeof pdfTracker?.sendBufferedPdfInteractions === 'function') {
        pdfTracker.sendBufferedPdfInteractions();
    }
    if (typeof heatmapTracker?.sendBufferedHeatmapInteractions === 'function') {
        heatmapTracker.sendBufferedHeatmapInteractions();
    }
});
