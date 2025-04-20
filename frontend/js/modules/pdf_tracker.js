// frontend/js/modules/pdf_tracker.js
'use strict';

import * as apiClient from './api_client.js';
// Import function from pdf_viewer to get current page number
// Assuming pdf_viewer.js exports this function
import { getCurrentPageNumber } from './pdf_viewer.js';

// --- Module State ---
let sessionId = null;
let pdfUrl = null;
let targetElement = null; // The main scrollable container (#pdf-viewer-area)
let textLayerElement = null; // The text layer div (#text-layer)

let interactionBuffer = [];
const BUFFER_SEND_DELAY = 1500; // Send logs every 1.5 seconds of inactivity
let bufferTimeout = null;

// State for specific tracking
let lastScrollTimestamp = 0;
let lastScrollPercent = 0;
const SCROLL_DEBOUNCE_DELAY = 500; // Only log scroll if paused for 500ms

let lastSelectionTimestamp = 0;
const SELECTION_DEBOUNCE_DELAY = 1000; // Log selection if paused for 1s

// --- Helper Functions ---

/**
 * Simple debounce function.
 * @param {Function} func - Function to debounce.
 * @param {number} wait - Debounce delay in milliseconds.
 * @returns {Function} - Debounced function.
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Adds an interaction event to the buffer and schedules sending.
 * @param {string} eventType - Type of event (e.g., 'pdf_scroll', 'pdf_text_select').
 * @param {object} payload - Event-specific data.
 */
function logInteractionEvent(eventType, payload) {
    if (!sessionId || !pdfUrl) {
        console.warn("Cannot log interaction: Session ID or PDF URL missing.");
        return;
    }

    const logEntry = {
        event_type: eventType,
        pdf_url: pdfUrl,
        payload: payload,
        element_width: targetElement?.clientWidth,
        element_height: targetElement?.clientHeight,
        timestamp_frontend: new Date() // Add frontend timestamp
    };

    interactionBuffer.push(logEntry);
    console.debug("Interaction added to buffer:", logEntry);

    // Reset the timer to send the buffer
    clearTimeout(bufferTimeout);
    bufferTimeout = setTimeout(sendBufferedPdfInteractions, BUFFER_SEND_DELAY);
}

// --- Event Handlers ---

/**
 * Handles scroll events on the target PDF container.
 * Debounced to avoid excessive logging.
 */
const handleScroll = debounce(() => {
    if (!targetElement) return;

    const scrollTop = targetElement.scrollTop;
    const scrollHeight = targetElement.scrollHeight;
    const clientHeight = targetElement.clientHeight;

    // Avoid division by zero if element not scrollable
    if (scrollHeight <= clientHeight) {
        lastScrollPercent = 0; // Or 100 if considered fully scrolled? Let's use 0.
    } else {
        lastScrollPercent = Math.min(1.0, scrollTop / (scrollHeight - clientHeight)).toFixed(4); // Calculate scroll percentage
    }

    const currentPage = getCurrentPageNumber(); // Get current page from viewer module

    console.log(`Scroll detected: Page ${currentPage}, Depth ${lastScrollPercent * 100}%`);
    logInteractionEvent('pdf_scroll', {
        page_number: currentPage,
        scroll_depth_percent: parseFloat(lastScrollPercent)
    });
    lastScrollTimestamp = Date.now();
}, SCROLL_DEBOUNCE_DELAY);


/**
 * Handles text selection events (mouseup after selection).
 * Debounced to capture the final selection.
 */
const handleTextSelection = debounce(() => {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText.length > 0 && textLayerElement && textLayerElement.contains(selection.anchorNode)) {
         // Check if selection is within our text layer
        const currentPage = getCurrentPageNumber();
        console.log(`Text selected: Page ${currentPage}, Text: "${selectedText}"`);

        // --- Coordinate Calculation (Complex/Approximate) ---
        let coords = null;
        try {
            const range = selection.getRangeAt(0);
            const rect = range.getBoundingClientRect(); // Coords relative to viewport
            const containerRect = textLayerElement.getBoundingClientRect(); // Text layer coords relative to viewport

            // Calculate coords relative to the text layer container
            coords = {
                 x: rect.left - containerRect.left,
                 y: rect.top - containerRect.top,
                 width: rect.width,
                 height: rect.height
            };
            // Note: These coordinates might need further transformation
            // if the text layer itself scrolls or scales within its parent.
        } catch (e) {
            console.warn("Could not get selection coordinates:", e);
        }
        // --- End Coordinate Calculation ---

        logInteractionEvent('pdf_text_select', {
             page_number: currentPage,
             selected_text: selectedText,
             selection_coordinates: coords // Can be null if calculation failed
        });
        lastSelectionTimestamp = Date.now();
         // Clear selection after logging? Optional.
         // window.getSelection().removeAllRanges();
    }
}, SELECTION_DEBOUNCE_DELAY);

// --- Integration Points (Requires pdf_viewer.js to trigger these) ---

/**
 * Placeholder function to be called when the page changes in pdf_viewer.js
 * (e.g., via a custom event listener or direct call).
 * @param {number} newPageNum - The new page number being displayed.
 * @param {number} oldPageNum - The previous page number.
 * @param {number} durationMs - Time spent on the old page (calculated by caller).
 */
export function logPageView(newPageNum, oldPageNum, durationMs) {
    console.log(`Page view logged: Switched from ${oldPageNum} to ${newPageNum} after ${durationMs}ms`);
    if (oldPageNum && durationMs > 0) {
         // Log duration for the page just left
         logInteractionEvent('pdf_page_view_duration', {
              page_number: oldPageNum,
              duration_ms: Math.round(durationMs)
         });
    }
     // Log viewing the new page (duration comes later)
     logInteractionEvent('pdf_page_view_start', {
          page_number: newPageNum
     });
}

/**
 * Placeholder function to be called when zoom changes in pdf_viewer.js.
 * @param {number} newZoomLevel - The new zoom level.
 */
export function logZoomChange(newZoomLevel) {
    const currentPage = getCurrentPageNumber();
    console.log(`Zoom logged: Page ${currentPage}, Level ${newZoomLevel}`);
    logInteractionEvent('pdf_zoom', {
        page_number: currentPage,
        zoom_level: newZoomLevel
    });
}


// --- Public Functions ---

/**
 * Initializes the PDF interaction tracker.
 * @param {string} currentSessionId - The participant's session UUID.
 * @param {string} targetElementId - The ID of the main PDF container element to track scrolls on.
 * @param {string} loadedPdfUrl - The URL of the PDF being viewed.
 */
export function initPdfInteractionTracker(currentSessionId, targetElementId, loadedPdfUrl) {
    sessionId = currentSessionId;
    pdfUrl = loadedPdfUrl;
    targetElement = document.getElementById(targetElementId);
    // Assuming text layer ID is consistent ('text-layer' from pdf_viewer.js)
    textLayerElement = document.getElementById('text-layer');

    if (!sessionId) {
        console.error("PDF Tracker: Session ID is required.");
        return;
    }
    if (!targetElement) {
        console.error(`PDF Tracker: Target element with ID '${targetElementId}' not found.`);
        return;
    }
     if (!textLayerElement) {
        console.error(`PDF Tracker: Text layer element with ID 'text-layer' not found.`);
        // Text selection tracking won't work
    }

    console.log(`Initializing PDF Interaction Tracker for session ${sessionId} on element #${targetElementId}`);

    // Attach listeners
    targetElement.addEventListener('scroll', handleScroll, { passive: true });
    // Listen for mouseup on the document or text layer to detect end of selection
    document.addEventListener('mouseup', handleTextSelection); // Using document might be more reliable

    // --- TODO: Integration with pdf_viewer.js for Page/Zoom Changes ---
    // Example using custom events (pdf_viewer.js would need to dispatch these):
    // targetElement.addEventListener('pdfpagechanged', (event) => {
    //     logPageView(event.detail.newPageNum, event.detail.oldPageNum, event.detail.durationMs);
    // });
    // targetElement.addEventListener('pdfzoomchanged', (event) => {
    //     logZoomChange(event.detail.newZoomLevel);
    // });
    // Alternatively, pdf_viewer.js could directly call logPageView/logZoomChange after importing this module.
    console.warn("PDF Tracker: Page view and zoom tracking require integration with pdf_viewer.js event dispatching or direct calls.");

}

/**
 * Sends the buffered interaction data to the backend.
 * Can be called manually (e.g., on page unload) or by the internal timer.
 */
export function sendBufferedPdfInteractions() {
    clearTimeout(bufferTimeout); // Clear any pending timeout
    bufferTimeout = null;

    if (interactionBuffer.length > 0) {
        const bufferCopy = [...interactionBuffer]; // Send a copy
        interactionBuffer = []; // Clear buffer immediately
        console.log(`Sending ${bufferCopy.length} buffered PDF interactions...`);

        apiClient.logInteractions(sessionId, bufferCopy)
            .then(response => {
                console.log("PDF interactions successfully logged:", response);
            })
            .catch(error => {
                console.error("Failed to log PDF interactions:", error);
                // TODO: Implement retry logic or save failed logs locally?
                // For simplicity, we just log the error here.
                // Consider re-adding failed logs to the buffer? (Risk of infinite loop if server error persists)
                // interactionBuffer = [...bufferCopy, ...interactionBuffer]; // Example: Put logs back (use with caution)
            });
    } else {
        // console.debug("No PDF interactions in buffer to send.");
    }
}