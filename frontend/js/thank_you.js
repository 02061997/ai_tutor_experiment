// frontend/js/thank_you.js
'use strict';

// Import API client (we'll need a function here later to trigger download)
import * as apiClient from './modules/api_client.js';

// --- DOM References ---
const app2DataDownloadDiv = document.getElementById('app2-data-download');
const downloadDataButton = document.getElementById('download-data-button');
const downloadStatusElement = document.getElementById('download-status');

// --- State ---
let sessionId = null;
let assignedApp = null;

// --- Helper Functions ---

/**
 * Retrieves session info stored previously.
 * @returns {object|null} Object with sessionId and assignedApp, or null if not found.
 */
function getSessionInfo() {
    const id = sessionStorage.getItem('experiment_session_uuid');
    const app = sessionStorage.getItem('experiment_assigned_app');
    // No critical error if app isn't found, just won't show download
    if (!id) {
        console.error("Thank You Page: Session ID not found in sessionStorage.");
        return null;
    }
    return { sessionId: id, assignedApp: app };
}

/**
 * Handles the click event for the download data button.
 */
async function handleDownloadData() {
    if (!sessionId) {
        downloadStatusElement.textContent = 'Error: Session ID missing.';
        return;
    }

    console.log(`Attempting to download data summary for session: ${sessionId}`);
    downloadStatusElement.textContent = 'Preparing data summary...';
    downloadDataButton.disabled = true;

    // --- Placeholder for API Call & Download ---
    try {
        // TODO: 1. Define backend endpoint (e.g., GET /data-download/{session_uuid})
        //          This endpoint should query relevant data (logs, quiz state),
        //          anonymize/summarize it, and return it as a file (e.g., CSV or JSON).
        // TODO: 2. Add function to api_client.js (e.g., downloadDataSummary(sessionId))
        //          This function should handle fetching the file response (e.g., as a Blob).
        // TODO: 3. Call the API client function here:
        // const fileBlob = await apiClient.downloadDataSummary(sessionId);

        // --- Placeholder Logic ---
        await new Promise(resolve => setTimeout(resolve, 1500)); // Simulate API call
        // Simulate getting a data blob (e.g., a CSV string)
        const simulatedCsvData = `SessionID,AssignedApp,CompletedStatus\n${sessionId},${assignedApp},Completed\nInteractionCount,XX\nQuizScore,YY`;
        const fileBlob = new Blob([simulatedCsvData], { type: 'text/csv;charset=utf-8;' });
        // --- End Placeholder ---


        // Create a link element, use it to prompt download, and remove it
        const link = document.createElement("a");
        const url = URL.createObjectURL(fileBlob);
        link.setAttribute("href", url);
        // Suggest a filename for the download
        link.setAttribute("download", `session_${sessionId}_summary.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click(); // Simulate click to trigger download
        document.body.removeChild(link); // Clean up link element
        URL.revokeObjectURL(url); // Free up object URL memory

        downloadStatusElement.textContent = 'Download started successfully.';
        // Keep button disabled after successful download? Or re-enable?
        // downloadDataButton.disabled = false;


    } catch (error) {
        console.error("Failed to download data summary:", error);
        downloadStatusElement.textContent = `Error downloading data: ${error.message || 'Please try again later.'}`;
        downloadDataButton.disabled = false; // Re-enable button on error
    }
    // --- End Placeholder ---
}


// --- Initialization ---
function initThankYouPage() {
    console.log("Initializing Thank You page...");
    const sessionInfo = getSessionInfo();

    if (!sessionInfo) {
        // Maybe display a generic thank you if session is lost?
        console.warn("Could not retrieve session info for Thank You page.");
        return;
    }
    sessionId = sessionInfo.sessionId;
    assignedApp = sessionInfo.assignedApp;

    // Conditionally display the download section for App2 users
    if (assignedApp === 'App2' && app2DataDownloadDiv) {
        console.log("App2 user detected, showing data download option.");
        app2DataDownloadDiv.style.display = 'block'; // Make the section visible

        // Attach event listener to the button
        if (downloadDataButton) {
            downloadDataButton.addEventListener('click', handleDownloadData);
        } else {
             console.error("Download data button element not found!");
        }
    } else {
         console.log("Not an App2 user or download element not found, hiding download option.");
    }

     // Optional: Clear session storage now that the experiment is fully complete
     // Consider if any info is needed (e.g., showing session ID on page)
     // sessionStorage.removeItem('experiment_session_uuid');
     // sessionStorage.removeItem('experiment_assigned_app');
     // sessionStorage.removeItem('experiment_assigned_paper');

    console.log(`Thank You page ready for session: ${sessionId}`);
}

// --- Run Initialization ---
document.addEventListener('DOMContentLoaded', initThankYouPage);