// frontend/js/modules/heatmap_tracker.js
// Corrected Version: Added missing debounce function definition.

'use strict';

import * as apiClient from './api_client.js';

// --- Helper Functions ---

/**
 * Simple debounce function. Delays invoking func until after wait milliseconds have
 * elapsed since the last time the debounced function was invoked.
 * @param {Function} func The function to debounce.
 * @param {number} wait The number of milliseconds to delay.
 * @returns {Function} Returns the new debounced function.
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        // Store the context (`this`) and arguments
        const context = this;
        const later = () => {
            timeout = null; // Clear timeout identifier
            func.apply(context, args); // Call the original function with stored context and args
        };
        clearTimeout(timeout); // Clear the previous timeout
        timeout = setTimeout(later, wait); // Set a new timeout
    };
}

/**
 * Simple throttle function. Executes func at most once per wait milliseconds.
 * Leading edge execution.
 * @param {Function} func - Function to throttle.
 * @param {number} wait - Throttle delay in milliseconds.
 * @returns {Function} - Throttled function.
 */
function throttle(func, wait) {
    let context, args, result;
    let timeout = null;
    let previous = 0;
    const later = function() {
        previous = Date.now();
        timeout = null;
        // result = func.apply(context, args); // Don't call again on trailing edge for simple throttle
        if (!timeout) context = args = null;
    };
    return function() {
        const now = Date.now();
        if (!previous) previous = now; // Set on first call
        const remaining = wait - (now - previous);
        context = this;
        args = arguments;
        // Execute if period 'wait' has passed since last execution OR if time calculation is weird (negative remaining)
        if (remaining <= 0 || remaining > wait) {
            if (timeout) { // Clear any trailing edge timeout
                clearTimeout(timeout);
                timeout = null;
            }
            previous = now;
            result = func.apply(context, args); // Execute on leading edge
            if (!timeout) context = args = null;
        } else if (!timeout) {
            // Optional: Setup trailing edge execution if needed, but simple throttle often omits this
            // timeout = setTimeout(later, remaining);
        }
        return result;
    };
}


// --- Module State ---
let sessionId = null;
let targetElement = null; // The element to track interactions within
let targetElementId = null; // The ID of the target element

let interactionBuffer = [];
const BUFFER_SEND_DELAY = 2000; // Send logs every 2 seconds of inactivity
let bufferTimeout = null;

// Mouse move tracking state
let mouseMoveBuffer = [];
const MOUSE_MOVE_LOG_DELAY = 500; // Log collected mouse moves after 500ms of inactivity


// --- Private Helper Functions ---

/**
 * Adds an interaction event to the buffer and schedules sending.
 * @param {string} eventType - Type of event (e.g., 'click', 'mousemove_batch').
 * @param {object} payload - Event-specific data.
 */
function logInteractionEvent(eventType, payload) {
    if (!sessionId || !targetElementId) {
        console.warn("Cannot log heatmap interaction: Session ID or Target Element ID missing.");
        return;
    }

    const logEntry = {
        event_type: eventType,
        target_element_id: targetElementId,
        payload: payload,
        element_width: targetElement?.clientWidth,
        element_height: targetElement?.clientHeight,
        timestamp_frontend: new Date().toISOString() // Use ISO format string
    };

    interactionBuffer.push(logEntry);
    console.debug("Heatmap interaction added to buffer:", logEntry);

    // Reset the timer to send the buffer
    clearTimeout(bufferTimeout);
    bufferTimeout = setTimeout(sendBufferedHeatmapInteractions, BUFFER_SEND_DELAY);
}

// Debounced function to log the collected mouse move batch
let debouncedSendMouseMoveBatch = debounce(() => {
     if (mouseMoveBuffer.length > 0) {
         logInteractionEvent('mousemove_batch', {
             points: [...mouseMoveBuffer] // Send copy of buffer
         });
         mouseMoveBuffer = []; // Clear the buffer after logging it
         console.debug("Logged mousemove_batch");
     }
 }, MOUSE_MOVE_LOG_DELAY);


// --- Event Handlers ---

/**
 * Handles click events on the target element.
 * @param {MouseEvent} event
 */
function handleClick(event) {
    if (!targetElement) return;
    // Calculate coordinates relative to the target element's top-left corner
    const rect = targetElement.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Ensure coordinates are within bounds (optional, prevents logging clicks outside)
    if (x < 0 || y < 0 || x > targetElement.clientWidth || y > targetElement.clientHeight) {
        return;
    }

    console.log(`Click detected at (${x}, ${y}) relative to #${targetElementId}`);

    logInteractionEvent('click', {
        x: Math.round(x),
        y: Math.round(y),
        value: 1 // Standard value for a single click event
    });
}


/**
 * Collects mouse move coordinates and triggers the debounced logging function.
 * @param {MouseEvent} event
 */
function collectMouseMove(event) {
     if (!targetElement) return;
     // Calculate coordinates relative to the target element's top-left corner
     const rect = targetElement.getBoundingClientRect();
     const x = event.clientX - rect.left;
     const y = event.clientY - rect.top;

     // Only record if mouse is actually over the element
     if (x >= 0 && y >= 0 && x <= targetElement.clientWidth && y <= targetElement.clientHeight) {
        mouseMoveBuffer.push({ x: Math.round(x), y: Math.round(y) });
        // Trigger the debounced sending function on each relevant move
        debouncedSendMouseMoveBatch();
     }
}


// --- Public Functions ---

/**
 * Initializes the heatmap interaction tracker.
 * @param {string} currentSessionId - The participant's session UUID.
 * @param {string} trackElementId - The ID of the HTML element to track interactions within.
 */
export function initHeatmapTracker(currentSessionId, trackElementId) {
    sessionId = currentSessionId;
    targetElementId = trackElementId; // Store the ID
    targetElement = document.getElementById(trackElementId);

    if (!sessionId) {
        console.error("Heatmap Tracker: Session ID is required.");
        return;
    }
    if (!targetElement) {
        console.error(`Heatmap Tracker: Target element with ID '${trackElementId}' not found.`);
        return;
    }

    console.log(`Initializing Heatmap Interaction Tracker for session ${sessionId} on element #${trackElementId}`);

    // Attach listeners
    targetElement.addEventListener('click', handleClick);
    targetElement.addEventListener('mousemove', collectMouseMove, { passive: true });

}

/**
 * Sends the buffered interaction data to the backend.
 * Can be called manually (e.g., on page unload) or by the internal timer.
 */
export function sendBufferedHeatmapInteractions() {
    // Ensure any final pending mouse move batch is logged first
    debouncedSendMouseMoveBatch();
    clearTimeout(bufferTimeout); // Clear any pending general buffer timeout
    bufferTimeout = null;

    if (interactionBuffer.length > 0) {
        const bufferCopy = [...interactionBuffer]; // Send a copy
        interactionBuffer = []; // Clear buffer immediately
        console.log(`Sending ${bufferCopy.length} buffered heatmap interactions...`);

        apiClient.logInteractions(sessionId, bufferCopy)
            .then(response => {
                console.log("Heatmap interactions successfully logged:", response);
            })
            .catch(error => {
                console.error("Failed to log heatmap interactions:", error);
                // TODO: Implement retry logic or save failed logs locally?
            });
    } else {
        // console.debug("No heatmap interactions in buffer to send.");
    }
}
