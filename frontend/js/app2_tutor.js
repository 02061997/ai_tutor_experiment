/**
 * @fileoverview Main script for the App2 Tutor interface (PDF + Summary + LLM Quiz).
 */

'use strict';

// --- Module Imports ---
import {
    // API Client functions
    getSessionDetails, // Keep if needed for session info
    getApp2Summary,    // Function to fetch summary from backend
    getNextLLMQuestion,// Function to get next quiz question
    submitLLMAnswer,   // Function to submit quiz answer
    logInteractions    // Function to log interaction data
} from './modules/api_client.js';
import * as pdfViewer from './modules/pdf_viewer.js'; // Import PDF viewer functions
import * as pdfTracker from './modules/pdf_tracker.js'; // Import PDF tracker functions
import * as heatmapTracker from './modules/heatmap_tracker.js'; // Import heatmap tracker functions
import { QuizUI } from './modules/quiz_ui.js'; // Import QuizUI class
import { GlobalWorkerOptions } from './libs/pdfjs/build/pdf.mjs'; // Import from pdf.js library

// --- DOM References ---
// Main Containers
const pdfAndSummaryContainer = document.getElementById('pdf-summary-container');
const quizContainer = document.getElementById('quiz-container'); // Keep existing ID

// PDF & Summary Elements
const assignedPaperNameElement = document.getElementById('assigned-paper-name');
const pdfViewerContainerId = 'pdf-viewer-area';
const summaryContentElement = document.getElementById('summary-content');
const startQuizButton = document.getElementById('start-quiz-btn');

// Final Navigation Button
const finishTaskButton = document.getElementById('finish-task-btn');

// --- Global State ---
let participantId = null; // Use session ID as participant ID for API calls
let currentMcqId = null;
let assignedPaperUrl = null;
let isQuizActive = false;
let quizUi = null; // Instance of QuizUI

// --- Configuration ---
const PDF_WORKER_SRC = '/js/libs/pdfjs/build/pdf.worker.mjs'; // Ensure path is correct
const QUIZ_CONTAINER_SELECTOR = '#quiz-section'; // Selector for QuizUI target

// --- Helper Functions ---

function getParticipantIdFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('session'); // Treat session ID as the participant identifier here
    if (!id) {
        console.error("Session ID not found in URL.");
        document.body.innerHTML = `<div class="container error-container"><h1>Error: Session ID Missing</h1><p>Cannot start the application. Please ensure you followed the correct link.</p></div>`;
        return null;
    }
    console.log("Retrieved Session ID (used as participantId):", id);
    return id;
}

function showSection(sectionId) {
    // Assumes pdf-summary-container and quiz-container cover all main views
    const pdfView = document.getElementById('pdf-summary-container');
    const quizView = document.getElementById('quiz-container'); // Use the correct ID for the quiz view container
    // Add other view containers here if needed (e.g., recommendations)
    const recommendationsView = document.getElementById('recommendations-view');

    if (pdfView) pdfView.style.display = (sectionId === 'pdf-summary-container') ? '' : 'none';
    if (quizView) quizView.style.display = (sectionId === 'quiz-container') ? '' : 'none';
    if (recommendationsView) recommendationsView.style.display = (sectionId === 'recommendations-view') ? '' : 'none';

    console.log(`Showing section: ${sectionId}`);
}


// --- Initialization Function ---
async function initializeApp2Tutor() {
    // --- ADDED DEBUG LOG ---
    console.log("DEBUG: initializeApp2Tutor started.");
    // -----------------------
    participantId = getParticipantIdFromUrl();
    if (!participantId) return;

    showSection('pdf-summary-container'); // Show PDF/Summary first
    // quizContainer is initially hidden via HTML style="display: none;"

    if (startQuizButton) startQuizButton.disabled = true; // Start disabled
    if (finishTaskButton) finishTaskButton.style.display = 'none';

    if (typeof GlobalWorkerOptions !== 'undefined') {
        GlobalWorkerOptions.workerSrc = PDF_WORKER_SRC;
        console.log("PDF.js worker source set.");
    } else {
        console.error("PDF.js GlobalWorkerOptions is not available. PDF viewer may fail.");
        if(summaryContentElement) summaryContentElement.innerHTML = `<p class="error">Critical Error: PDF library component failed to load.</p>`;
        return;
    }

    try {
        // --- Get Assigned Paper URL (Example: use default or fetch from session) ---
        assignedPaperUrl = '/static/pdfs/chapter1.pdf'; // Default PDF path for Paper1
        // TODO: Add logic to determine Paper2 path if needed based on session details
        if (assignedPaperNameElement) {
            assignedPaperNameElement.textContent = assignedPaperUrl.split('/').pop() || 'Assigned Research Paper';
        }

        // --- Initialize PDF Viewer ---
        await pdfViewer.initPdfViewer({
            containerId: pdfViewerContainerId, canvasId: 'pdf-canvas', textLayerId: 'text-layer',
            prevButtonId: 'prev-page', nextButtonId: 'next-page',
            pageNumSpanId: 'page-num', pageCountSpanId: 'page-count',
            pdfUrl: assignedPaperUrl
        });
        console.log("PDF Viewer Initialized.");

        // --- Initialize Interaction Trackers ---
        pdfTracker.initPdfInteractionTracker(participantId, pdfViewerContainerId, assignedPaperUrl);
        heatmapTracker.initHeatmapTracker(participantId, pdfViewerContainerId);
        console.log("Interaction Trackers Initialized.");

        // --- Fetch and Display Summary (Calls actual API now) ---
        await fetchAndDisplaySummary(); // Enable quiz button inside on success

        // --- Initialize Quiz UI ---
        // Ensure the HTML has <div id="quiz-section">...</div> inside #quiz-container
        quizUi = new QuizUI(QUIZ_CONTAINER_SELECTOR, handleQuizAnswerSubmit);
        console.log("Quiz UI Initialized."); // Log moved after instantiation

        // --- Add Event Listeners ---
        startQuizButton?.addEventListener('click', startQuizPhase);
        finishTaskButton?.addEventListener('click', navigateToFinalTest);

    } catch (error) {
        console.error("Initialization failed:", error);
        const mainContainer = document.querySelector('.app2-main-container') || document.body;
        mainContainer.innerHTML = `<div class="container error-container"><h1>Application Initialization Failed</h1><p>${error.message}</p><p>Please try refreshing the page or contact support.</p></div>`;
    }
}

/**
 * Fetches the AI-generated structured summary from the backend and displays it.
 * Enables the "Start Quiz" button on success.
 */
async function fetchAndDisplaySummary() {
    // --- ADDED DEBUG LOG ---
    console.log("DEBUG: fetchAndDisplaySummary started.");
    // -----------------------
    if (!summaryContentElement) {
        console.error("Summary content element not found.");
        return; // Exit if container doesn't exist
    }
    summaryContentElement.innerHTML = '<p><i>Generating structured summary from AI... Please wait.</i></p>';
    if (startQuizButton) startQuizButton.disabled = true; // Ensure button is disabled

    try {
        // --- ADDED DEBUG LOG ---
        console.log(`DEBUG: Attempting to call getApp2Summary for session: ${participantId}`);
        // -----------------------
        const summaryResponse = await getApp2Summary(participantId); // Calls GET /api/v1/app2/summary/{session_id}

        // --- ADDED DEBUG LOG ---
        console.log('DEBUG: Data received by fetchAndDisplaySummary:', summaryResponse);
        // -----------------------

        // Check if the response has the 'summary' key and it's an array
        if (!summaryResponse || !Array.isArray(summaryResponse.summary) || summaryResponse.summary.length === 0) {
            if (summaryResponse && summaryResponse.error) {
                throw new Error(`Server error fetching summary: ${summaryResponse.error}`);
            } else if (summaryResponse && summaryResponse.detail) {
                throw new Error(`Server error fetching summary: ${summaryResponse.detail}`);
            } else {
                console.error("Received summary data:", summaryResponse);
                throw new Error("Received empty or invalid structured summary data from server.");
            }
        }

        // Clear loading message
        summaryContentElement.innerHTML = '';

        // Iterate through the structured summary array and display it
        summaryResponse.summary.forEach(section => {
            if (!section || !section.title) return;

            const titleElement = document.createElement('h3');
            titleElement.textContent = section.title;
            titleElement.style.marginTop = '1em';
            summaryContentElement.appendChild(titleElement);

            if (typeof section.content === 'string') {
                const contentPara = document.createElement('p');
                contentPara.style.whiteSpace = 'pre-wrap';
                contentPara.textContent = section.content || "(No content)";
                summaryContentElement.appendChild(contentPara);
            } else if (typeof section.content === 'object' && section.content !== null) {
                const subList = document.createElement('ul');
                subList.style.listStylePosition = 'inside';
                for (const subTitle in section.content) {
                    if (Object.hasOwnProperty.call(section.content, subTitle)) {
                        const listItem = document.createElement('li');
                        const subContent = section.content[subTitle] || "(No content)";
                        listItem.innerHTML = `<strong>${subTitle}:</strong> `;
                        listItem.appendChild(document.createTextNode(subContent));
                        listItem.style.whiteSpace = 'pre-wrap';
                        listItem.style.marginLeft = '1em';
                        subList.appendChild(listItem);
                    }
                }
                summaryContentElement.appendChild(subList);
            } else {
                const errorPara = document.createElement('p');
                errorPara.textContent = "(Invalid content format for this section)";
                errorPara.style.fontStyle = 'italic';
                summaryContentElement.appendChild(errorPara);
            }
        });

        console.log("Structured summary displayed successfully.");

        // Enable quiz button only after summary is successfully displayed
        if (startQuizButton) {
            startQuizButton.disabled = false;
            console.log("Start Quiz button enabled.");
        }

    } catch (error) {
        console.error("Failed to fetch or display summary:", error);
        summaryContentElement.innerHTML = `<p class="error" style="color: red;">Error loading summary: ${error.message}</p>`;
        if (startQuizButton) {
            startQuizButton.disabled = true;
            console.log("Start Quiz button kept disabled due to summary error.");
        }
    }
}


/**
 * Handles the transition to the quiz phase and fetches the FIRST question.
 */
async function startQuizPhase() {
    console.log("DEBUG: startQuizPhase function called!");
    console.log("Starting Quiz Phase...");
    if (!quizUi || !participantId) {
        console.error("Quiz UI or Participant ID not available.");
        alert("Error: Cannot start quiz. Please refresh.")
        return;
    }

    showSection('quiz-container'); // Show the quiz container view

    if (startQuizButton) {
        startQuizButton.disabled = true;
        startQuizButton.textContent = 'Quiz Started';
    }
    if (finishTaskButton) finishTaskButton.style.display = 'none';

    isQuizActive = true;
    quizUi.reset();
    quizUi.showLoading();

    try {
        console.log(`DEBUG: Calling getNextLLMQuestion for participant: ${participantId}`);
        const firstQuestionData = await getNextLLMQuestion(participantId); // API Call
        console.log("DEBUG: Received response from getNextLLMQuestion:", firstQuestionData);
        quizUi.hideLoading();

        if (firstQuestionData && firstQuestionData.mcq_id) {
            currentMcqId = firstQuestionData.mcq_id;
            console.log("First LLM question received. MCQ ID:", currentMcqId);
            quizUi.showQuestion(firstQuestionData);
        } else if (firstQuestionData?.quiz_complete) {
            console.log("Backend indicated quiz is already complete or no questions available.");
            handleQuizCompletion(firstQuestionData.error); // Pass potential error message
        } else {
            if (firstQuestionData && firstQuestionData.error) {
                throw new Error(`Server error getting first question: ${firstQuestionData.error}`);
            } else {
                throw new Error("Failed to get first question: Received invalid data structure.");
            }
        }
    } catch (error) {
        console.error("Failed to start quiz phase / get first question:", error);
        quizUi.hideLoading();
        quizUi.showError(`Error starting quiz: ${error.message}. Please try refreshing the page.`);
        isQuizActive = false;
    }
}

/**
 * Callback function passed to QuizUI instance. Handles answer submission.
 * @param {string} selectedAnswerLetter - The letter ('A', 'B', 'C', or 'D') selected by the user.
 */
async function handleQuizAnswerSubmit(selectedAnswerLetter) { // Parameter is the letter now
    // Parameter name updated for clarity, assuming QuizUI calls this with the letter 'A'/'B'/'C'/'D'
    console.log(`DEBUG: handleQuizAnswerSubmit called with answer letter: ${selectedAnswerLetter}`);
    if (!isQuizActive || !participantId || !currentMcqId || !selectedAnswerLetter) {
        console.error("Cannot submit answer: Quiz not active or missing data.");
        quizUi.showError("Error: Could not submit answer. Invalid state.", true);
        return;
    }

    try {
        console.log(`DEBUG: Calling submitLLMAnswer for participant ${participantId}, mcq ${currentMcqId}, answer ${selectedAnswerLetter}`);
        // Pass the letter to the API client function
        const feedbackResponse = await submitLLMAnswer(participantId, currentMcqId, selectedAnswerLetter);
        console.log("DEBUG: Received feedback response:", feedbackResponse);

        if (feedbackResponse) {
            if (typeof feedbackResponse.is_correct === 'undefined' || typeof feedbackResponse.correct_answer_letter === 'undefined') {
                throw new Error("Invalid feedback response structure from server.");
            }

            // Need correct answer TEXT for display, look it up based on letter
            const correctLetter = feedbackResponse.correct_answer_letter;
            // TODO: Get the options from the current question data stored somewhere accessible
            // Or modify the backend to return the correct answer text in the feedback response
            const correctAnswerText = `[Correct option text for ${correctLetter}]`; // Placeholder - Needs fixing

            quizUi.showFeedback(
                feedbackResponse.is_correct,
                correctAnswerText, // Pass the TEXT here
                feedbackResponse.explanation
            );

            if (feedbackResponse.quiz_complete === true) {
                console.log("Quiz completed according to backend feedback.");
                handleQuizCompletion(); // Call completion handler
            } else {
                // Fetch the next question after a short delay
                const NEXT_QUESTION_DELAY = 1500;
                console.log(`Fetching next question in ${NEXT_QUESTION_DELAY}ms...`);
                await new Promise(resolve => setTimeout(resolve, NEXT_QUESTION_DELAY));
                fetchNextQuestion(); // Fetch next question
            }
        } else {
            throw new Error("Received null or invalid feedback response from server.");
        }

    } catch (error) {
        console.error("Error submitting answer:", error);
        quizUi.showError(`Error submitting answer: ${error.message || 'Please try again.'}`, true);
    }
}


/**
 * Fetches and displays the next quiz question.
 */
async function fetchNextQuestion() {
    if (!isQuizActive) return;
    quizUi.showLoading();

    try {
        console.log(`DEBUG: Calling getNextLLMQuestion for next question for participant: ${participantId}`);
        const nextQuestionData = await getNextLLMQuestion(participantId); // API Call
        console.log("DEBUG: Received response for next question:", nextQuestionData);
        quizUi.hideLoading();

        if (nextQuestionData && nextQuestionData.mcq_id) {
            currentMcqId = nextQuestionData.mcq_id;
            console.log("Next LLM question received. MCQ ID:", currentMcqId);
            quizUi.showQuestion(nextQuestionData);
        } else if (nextQuestionData?.quiz_complete === true) {
            console.log("Received completion signal while fetching next question.");
            handleQuizCompletion(nextQuestionData.error); // Pass potential error
        } else {
            if (nextQuestionData && nextQuestionData.error) {
                throw new Error(`Server error getting next question: ${nextQuestionData.error}`);
            }
            console.warn("Received potentially invalid response or no more questions. Assuming quiz complete.");
            handleQuizCompletion("No more questions available or invalid response."); // Assume completion
        }
    } catch(error) {
        console.error("Failed to fetch next question:", error);
        quizUi.hideLoading();
        quizUi.showError(`Error fetching next question: ${error.message}.`);
        handleQuizCompletion(error.message); // Assume completion on error
    }
}


/**
 * Handles the UI changes when the quiz is marked as complete.
 * @param {string} [errorMessage=null] Optional error message if completion was due to an error.
 */
function handleQuizCompletion(errorMessage = null) {
    console.log("Handling quiz completion...");
    isQuizActive = false;
    currentMcqId = null;
    let completionMsg = "Quiz finished! You can now proceed to the final test.";
    if(errorMessage) {
        completionMsg = `Quiz ended due to an error: ${errorMessage}. Please proceed to the final test.`;
        // Optionally display this using quizUi.showError as well/instead
    }
    quizUi.showCompletionMessage(completionMsg);

    if (finishTaskButton) {
        finishTaskButton.style.display = ''; // Show the button
        finishTaskButton.disabled = false;
    }
    // Hide the start quiz button if it's somehow still visible
    if(startQuizButton) startQuizButton.style.display = 'none';
}

/**
 * Navigates the user to the final test page.
 */
function navigateToFinalTest() {
    console.log("Proceeding to Final Test...");
    if (!participantId) {
        console.error("Cannot navigate to final test: Participant ID missing.");
        alert("An error occurred. Cannot proceed to the final test.");
        return;
    }
    sendBufferedData(); // Send any remaining interaction data before navigating
    window.location.href = `/final_test.html?session=${participantId}`; // Use session ID for navigation
}

/**
 * Sends any buffered interaction data before page unload or navigation.
 */
function sendBufferedData() {
    console.log("Attempting to send buffered interaction data...");
    try {
        if (typeof pdfTracker.sendBufferedPdfInteractions === 'function') {
            pdfTracker.sendBufferedPdfInteractions();
            console.log("Called sendBufferedPdfInteractions.");
        } else {
            console.warn("sendBufferedPdfInteractions function not available from pdf_tracker module.");
        }
        if (typeof heatmapTracker.sendBufferedHeatmapInteractions === 'function') {
            heatmapTracker.sendBufferedHeatmapInteractions();
            console.log("Called sendBufferedHeatmapInteractions.");
        } else {
            console.warn("sendBufferedHeatmapInteractions function not available from heatmap_tracker module.");
        }
    } catch (error) {
        console.error("Error sending buffered data:", error);
    }
}


// --- Application Entry Point ---
document.addEventListener('DOMContentLoaded', initializeApp2Tutor);

// --- Unload Listener ---
window.addEventListener('beforeunload', sendBufferedData);