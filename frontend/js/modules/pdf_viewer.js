// frontend/js/modules/pdf_viewer.js
// Corrected Version: Imports default export and named export from pdf.mjs

// Test Save

'use strict';

// **** Import default export AND named getDocument ****
// The default export is often the main library object in UMD-style modules converted to ES modules.
// Path is relative TO THIS FILE (pdf_viewer.js is inside modules/)

import { getDocument } from '../libs/pdfjs/build/pdf.mjs';

// --- Module State ---
let pdfDoc = null; // Holds the loaded PDF document object
let pageNum = 1; // Current page number being displayed
let pageRendering = false; // Flag to indicate if a page is currently rendering
let pageNumPending = null; // Holds the page number requested while another was rendering
const initialScale = 1.0; // Start at 100% scale
let currentScale = initialScale; // Current zoom level
const MIN_SCALE = 0.25; // Minimum zoom level
const MAX_SCALE = 3.0; // Maximum zoom level
const ZOOM_INCREMENT = 0.25; // How much to zoom in/out per click

// DOM Element references (will be set in initPdfViewer)
let pdfContainer = null;
let canvas = null;
let textLayerDiv = null;
let pageNumSpan = null;
let pageCountSpan = null;
let prevButton = null;
let nextButton = null;
let zoomInButton = null; // Zoom button reference
let zoomOutButton = null; // Zoom button reference

/**
 * Renders a specific page of the PDF onto the canvas and renders its text layer.
 * @param {number} num - The page number to render.
 */
async function renderPage(num) {
    pageRendering = true;
    document.getElementById('loading-indicator')?.remove();

    // Add loading indicator (ensure CSS for #loading-indicator exists)
    const loadingIndicator = document.createElement('div');
    loadingIndicator.id = 'loading-indicator';
    loadingIndicator.textContent = 'Loading page...';
    pdfContainer?.prepend(loadingIndicator); // Add indicator to container

    try {
        // Ensure pdfDoc is loaded before proceeding
        if (!pdfDoc) {
            console.error("pdfDoc is not loaded, cannot render page.");
            throw new Error("PDF document not loaded.");
        }
        const page = await pdfDoc.getPage(num);
        console.log(`Rendering page ${num} at scale ${currentScale}`);
        const viewport = page.getViewport({ scale: currentScale });

        // Prepare canvas
        if (canvas) {
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            const renderContext = { canvasContext: context, viewport: viewport };
            // Use await directly on the promise returned by page.render
            await page.render(renderContext).promise;
            console.log(`Page ${num} canvas rendered`);
        } else {
            console.error("Canvas element not found during renderPage");
        }

        // Prepare and render text layer
        if (textLayerDiv) {
            textLayerDiv.innerHTML = ''; // Clear previous text layer content more reliably
            textLayerDiv.style.width = `${canvas.width}px`;
            textLayerDiv.style.height = `${canvas.height}px`;
            await renderTextLayerInternal(page, viewport); // Render new text layer
        } else {
             console.error("Text layer element not found during renderPage");
        }

    } catch (error) {
        console.error(`Error rendering page ${num}:`, error);
        // Display error in the container if possible
        if(pdfContainer) pdfContainer.innerHTML = `<p style='color:red;'>Error rendering page: ${error.message}.</p>`;

    } finally {
        pageRendering = false;
        document.getElementById('loading-indicator')?.remove(); // Remove indicator regardless of error
        if (pageNumPending !== null) {
            // If another page was requested while rendering, render it now
            const pendingNum = pageNumPending;
            pageNumPending = null; // Clear pending before recursive call
            renderPage(pendingNum);
        } else {
            // Only update UI and dispatch event if no pending page (avoids duplicate events)
            updateUiState();
            dispatchPageChangeEvent(); // Dispatch event only if no pending render
        }
    }
}

/**
 * Internal function to render the text layer using the imported library object.
 * @param {PDFPageProxy} page - The PDF.js page object.
 * @param {PageViewport} viewport - The viewport used for rendering.
 */
async function renderTextLayerInternal(page, viewport) {
     try {
        const textContent = await page.getTextContent();
        // Use the imported pdfjsLib object which should contain renderTextLayer
        // Check if pdfjsLib and its renderTextLayer method exist
        if (typeof pdfjsLib !== 'undefined' && typeof pdfjsLib.renderTextLayer === 'function') {
             const textLayerTask = pdfjsLib.renderTextLayer({
                textContentSource: textContent,
                container: textLayerDiv, // The HTML div designated for the text layer
                viewport: viewport,
                // enhanceTextSelection: true, // Optional: Can improve text selection behavior
            });
            // Await the promise if the renderTextLayer version returns one
            if (textLayerTask && typeof textLayerTask.promise === 'object') {
                 await textLayerTask.promise;
            }
            console.log(`Page ${page.pageNumber} text layer rendered`);
        } else {
             // Log error if function still not found (might indicate issue with PDF.js build/version)
             console.error("pdfjsLib.renderTextLayer function is not available.");
        }
    } catch (error) {
         console.error(`Error rendering text layer for page ${page.pageNumber}:`, error);
    }
}


/**
 * If another page rendering in progress, waits until the rendering is
 * finished. Otherwise, renders the requested page immediately.
 * @param {number} num - Page number to render.
 */
function queueRenderPage(num) {
    if (pageRendering) {
        pageNumPending = num;
         console.log(`Queueing page ${num} render`);
    } else {
        renderPage(num);
    }
}

/**
 * Updates the page number display and button states (nav and zoom).
 */
function updateUiState() {
     // Use optional chaining for safety in case elements aren't found
     if (!pdfDoc || !pageNumSpan || !prevButton || !nextButton || !zoomInButton || !zoomOutButton) {
        console.warn("One or more UI elements missing in updateUiState");
        return;
     }
     pageNumSpan.textContent = pageNum;
     prevButton.disabled = (pageNum <= 1);
     nextButton.disabled = (pageNum >= pdfDoc.numPages);
     // Disable zoom buttons at limits
     zoomOutButton.disabled = (currentScale <= MIN_SCALE);
     zoomInButton.disabled = (currentScale >= MAX_SCALE);
     console.log(`UI updated for page ${pageNum}, scale ${currentScale}`);
}

/** Dispatch page change event helper */
function dispatchPageChangeEvent() {
     if (pdfContainer && pdfDoc) {
        try {
            const event = new CustomEvent('pdfpagechanged', {
                detail: { currentPage: pageNum, totalPages: pdfDoc.numPages }
            });
            pdfContainer.dispatchEvent(event);
            console.log(`Dispatched pdfpagechanged event: page ${pageNum}`);
        } catch(e) { console.error("Error dispatching pdfpagechanged event:", e); }
    }
}

/** Dispatch zoom change event helper */
function dispatchZoomEvent() {
    if (pdfContainer) {
        try {
            const event = new CustomEvent('pdfzoomchanged', {
                detail: { newScale: currentScale }
            });
            pdfContainer.dispatchEvent(event);
            console.log(`Dispatched pdfzoomchanged event: scale ${currentScale}`);
        } catch(e) { console.error("Error dispatching pdfzoomchanged event:", e); }
    }
}


/** Navigation handlers */
function onPrevPage() {
    if (pageNum <= 1) return;
    pageNum--;
    queueRenderPage(pageNum);
}
function onNextPage() {
    if (!pdfDoc || pageNum >= pdfDoc.numPages) return;
    pageNum++;
    queueRenderPage(pageNum);
}

/** Zoom handlers */
function zoomIn() {
    if (currentScale >= MAX_SCALE) return;
    currentScale = Math.min(MAX_SCALE, currentScale + ZOOM_INCREMENT); // Ensure we don't exceed max
    console.log("Zooming In to:", currentScale);
    renderPage(pageNum); // Re-render current page at new scale
    dispatchZoomEvent(); // Dispatch event after zoom
}

function zoomOut() {
    if (currentScale <= MIN_SCALE) return;
    currentScale = Math.max(MIN_SCALE, currentScale - ZOOM_INCREMENT); // Ensure we don't go below min
    console.log("Zooming Out to:", currentScale);
    renderPage(pageNum); // Re-render current page at new scale
    dispatchZoomEvent(); // Dispatch event after zoom
}


/**
 * Initializes the PDF viewer. Gets DOM elements, adds listeners, loads PDF.
 * @param {object} config - Configuration object.
 */
export async function initPdfViewer(config) {
    console.log("Initializing PDF Viewer with config:", config);

    // Get DOM elements
    pdfContainer = document.getElementById(config.containerId);
    canvas = document.getElementById(config.canvasId);
    textLayerDiv = document.getElementById(config.textLayerId);
    pageNumSpan = document.getElementById(config.pageNumSpanId);
    pageCountSpan = document.getElementById(config.pageCountSpanId);
    prevButton = document.getElementById(config.prevButtonId);
    nextButton = document.getElementById(config.nextButtonId);
    // Get zoom buttons using IDs from HTML
    zoomInButton = document.getElementById('zoom-in-button');
    zoomOutButton = document.getElementById('zoom-out-button');


    // Check if all essential elements were found
    if (!pdfContainer || !canvas || !textLayerDiv || !pageNumSpan || !pageCountSpan || !prevButton || !nextButton || !zoomInButton || !zoomOutButton) {
        console.error("PDF Viewer initialization failed: One or more required DOM elements not found (including zoom buttons).");
        if(pdfContainer) pdfContainer.innerHTML = "<p style='color:red;'>Error: PDF viewer UI elements missing.</p>";
        return; // Stop initialization if UI elements are missing
    }

    // Add event listeners for navigation and zoom
    prevButton.addEventListener('click', onPrevPage);
    nextButton.addEventListener('click', onNextPage);
    zoomInButton.addEventListener('click', zoomIn);
    zoomOutButton.addEventListener('click', zoomOut);

    // Use the imported getDocument function (named import)
    if (typeof getDocument !== 'function') {
        console.error("PDF.js getDocument function not imported correctly.");
        if(pdfContainer) pdfContainer.innerHTML = "<p style='color:red;'>Error: Core PDF library function (getDocument) failed to load.</p>";
        throw new Error("PDF.js getDocument is required but not imported correctly.");
    }
     // Check if the default import pdfjsLib is available for renderTextLayer
     if (typeof pdfjsLib === 'undefined') {
         console.warn("PDF.js default export (pdfjsLib) not found. Text layer might not work.");
         // Don't throw error here, maybe text layer isn't critical failure
     }


    try {
        // Asynchronously download PDF using imported getDocument function
        const loadingTask = getDocument(config.pdfUrl);
        pdfDoc = await loadingTask.promise;
        console.log('PDF loaded successfully:', pdfDoc);
        if(pageCountSpan) pageCountSpan.textContent = pdfDoc.numPages;

        // Initial render of the first page
        pageNum = 1; // Reset page number
        currentScale = initialScale; // Reset scale on new PDF load
        await renderPage(pageNum); // Render the first page

    } catch (error) {
        // Handle PDF loading errors
        console.error('Error loading PDF:', error);
        if(pdfContainer) pdfContainer.innerHTML = `<p style='color:red;'>Error loading PDF: ${error.message}. Check file path and network.</p>`;
        throw error; // Re-throw error to be caught by initApp in app2_tutor.js
    }
}

/**
 * Function to get the current page number (might be useful for trackers)
 * @returns {number} The current page number being displayed.
 */
export function getCurrentPageNumber() {
    return pageNum;
}

/**
 * Function to get the current scale (might be useful for trackers)
 * @returns {number} The current zoom scale.
 */
export function getCurrentScale() {
    return currentScale;
}

