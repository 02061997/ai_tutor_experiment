// dashboard/frontend/js/main.js
'use strict';

// --- Configuration & State ---
const API_BASE_URL = '/api/v1/dashboard'; // Base URL for dashboard endpoints
let surveyChart = null; // Holds the Chart.js instance for survey results
let thetaChart = null; // Holds the Chart.js instance for theta distribution
let heatmapInstance = null; // Holds the heatmap.js instance

// --- DOM References --- (Keep existing references)
const authStatusElement = document.getElementById('auth-status');
const loginButton = document.getElementById('login-button');
const logoutButton = document.getElementById('logout-button');
const summaryStatsDiv = document.getElementById('summary-stats');
const surveyTypeSelect = document.getElementById('survey-type-select');
const surveyQuestionSelect = document.getElementById('survey-question-select');
const loadSurveyButton = document.getElementById('load-survey-button');
const surveyChartCanvas = document.getElementById('survey-chart');
const surveyDataTableDiv = document.getElementById('survey-data-table');
const quizPerfSummaryDiv = document.getElementById('quiz-perf-summary');
const quizThetaChartCanvas = document.getElementById('quiz-theta-chart');
const heatmapTargetSelect = document.getElementById('heatmap-target-select');
const loadHeatmapButton = document.getElementById('load-heatmap-button');
const heatmapContainer = document.getElementById('heatmap-canvas-container');
const pdfSelect = document.getElementById('pdf-select');
const loadPdfStatsButton = document.getElementById('load-pdf-stats-button');
const pdfStatsDisplayDiv = document.getElementById('pdf-stats-display');
const itemSelect = document.getElementById('item-select');
const loadItemStatsButton = document.getElementById('load-item-stats-button');
const itemStatsDisplayDiv = document.getElementById('item-stats-display');

// --- API Client (Simplified Local Version - Keep existing) ---
const dashboardApiClient = {
    async fetchApi(endpoint, method = 'GET', params = null) {
        let url = `${API_BASE_URL}${endpoint}`;
        if (params && method === 'GET') {
            url += '?' + new URLSearchParams(params).toString();
        }
        const options = {
            method: method,
            headers: {
                'Accept': 'application/json',
                // 'Authorization': `Bearer ${getAuthToken()}` // Placeholder
            },
        };
        console.debug(`Dashboard API Request: ${method} ${url}`);
        try {
            const response = await fetch(url, options);
            if (!response.ok) {
                let errorBody; try { errorBody = await response.json(); } catch (e) { errorBody = { detail: response.statusText }; }
                throw new Error(errorBody.detail || `HTTP error ${response.status}`);
            }
            if (response.status === 204) return null;
            const data = await response.json();
             // Basic validation: Check if expected data structure is present (can be more specific)
            if (typeof data !== 'object' || data === null) {
                throw new Error("Invalid data format received from API.");
            }
            return data;
        } catch (error) {
            console.error(`Dashboard API Error (${method} ${url}):`, error);
            showError(`API Error: ${error.message}`);
            throw error;
        }
    },
    getSummary: () => dashboardApiClient.fetchApi('/summary'),
    getSurveyResults: (surveyType, questionKey) => dashboardApiClient.fetchApi('/survey/results', 'GET', { survey_type: surveyType, question_key: questionKey }),
    getQuizPerformance: () => dashboardApiClient.fetchApi('/quiz/performance'),
    getHeatmapData: (target) => dashboardApiClient.fetchApi('/interactions/heatmap', 'GET', { target: target }),
    getPdfStats: (pdfUrl) => dashboardApiClient.fetchApi('/interactions/pdf', 'GET', { pdf_url: pdfUrl }),
    getItemAnalysis: (questionId) => dashboardApiClient.fetchApi(`/quiz/item_analysis/${questionId}`)
};


// --- UI Update Functions (Refined) ---

function showError(message, element = null) {
    console.error("Dashboard UI Error:", message);
    // Display error in a specific element if provided, otherwise use alert
    if (element) {
         element.innerHTML = `<p style="color: red;">Error: ${message}</p>`;
    } else {
        alert(`Dashboard Error: ${message}`);
    }
}

function showLoading(element) {
    if(element) {
        element.innerHTML = `<p><i>Loading data...</i></p>`;
    }
}

function displaySummaryStats(data) {
    if (!summaryStatsDiv) return;
    if (!data) {
        showError("No summary data received.", summaryStatsDiv);
        return;
    }
    summaryStatsDiv.innerHTML = `
        <p>Total Participants: <strong>${data.total_participants ?? 'N/A'}</strong></p>
        <p>Completed Sessions: <strong>${data.completed_participants ?? 'N/A'}</strong> (${data.completion_rate?.toFixed(1) ?? 'N/A'}%)</p>
        <p>Assigned App1 / App2: <strong>${data.assigned_app1_count ?? 'N/A'}</strong> / <strong>${data.assigned_app2_count ?? 'N/A'}</strong></p>
        <p>Abandoned / Error: <strong>${data.abandoned_participants ?? 'N/A'}</strong> / <strong>${data.error_participants ?? 'N/A'}</strong></p>
    `;
}

function displaySurveyResults(data) {
    if (!surveyChartCanvas) return;
    showLoading(surveyDataTableDiv); // Clear previous table while chart loads

    if (!data || !data.response_counts || Object.keys(data.response_counts).length === 0) {
         surveyChartCanvas.style.display = 'none';
         surveyDataTableDiv.innerHTML = `<p><i>No response data found for ${data?.question_key || 'selected question'} in ${data?.survey_type || 'selected survey'}.</i></p>`;
         if(surveyChart) surveyChart.destroy();
         return;
    }

    surveyChartCanvas.style.display = 'block';
    const ctx = surveyChartCanvas.getContext('2d');
    const labels = Object.keys(data.response_counts);
    const counts = Object.values(data.response_counts);

    if (surveyChart) {
        surveyChart.destroy();
    }
    try {
        surveyChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: `Counts`,
                    data: counts,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y', // Horizontal bars can be nice for category labels
                scales: { x: { beginAtZero: true, title: { display: true, text: 'Count'} } },
                responsive: true,
                maintainAspectRatio: false, // Allow chart to resize height
                plugins: {
                    title: { display: true, text: `Survey: ${data.survey_type} / Question: ${data.question_key}` },
                    legend: { display: false } // Hide legend for single dataset
                }
            }
        });
    } catch(error) {
        showError(`Failed to render survey chart: ${error.message}`, surveyChartCanvas.parentElement);
    }


    // Display data in table
    if (surveyDataTableDiv) {
        let tableHTML = '<h4>Response Counts:</h4><table><thead><tr><th>Response Option</th><th>Count</th></tr></thead><tbody>';
        if(labels.length > 0){
            for (const [response, count] of Object.entries(data.response_counts)) {
                tableHTML += `<tr><td>${escapeHtml(response)}</td><td>${count}</td></tr>`; // Escape HTML
            }
        } else {
            tableHTML += '<tr><td colspan="2">No data</td></tr>';
        }
        tableHTML += '</tbody></table>';
        surveyDataTableDiv.innerHTML = tableHTML;
    }
}

function displayQuizPerformance(data) {
    if (!quizPerfSummaryDiv || !quizThetaChartCanvas) return;

    if (!data || data.total_completed_attempts === undefined) {
         quizPerfSummaryDiv.innerHTML = "<p><i>No quiz performance data received or processed.</i></p>";
         quizThetaChartCanvas.style.display = 'none';
         if(thetaChart) thetaChart.destroy();
         return;
    }

    quizPerfSummaryDiv.innerHTML = `
        <p>Total Completed Attempts Analyzed: <strong>${data.total_completed_attempts ?? 0}</strong></p>
        <p>Average Final Theta: <strong>${data.average_final_theta?.toFixed(3) ?? 'N/A'}</strong> (Median: ${data.median_final_theta?.toFixed(3) ?? 'N/A'})</p>
        <p>Average Final SE: <strong>${data.average_final_se?.toFixed(3) ?? 'N/A'}</strong></p>
        <p>Average Items Administered: <strong>${data.average_items_administered?.toFixed(1) ?? 'N/A'}</strong></p>
    `;

    // Render histogram for theta distribution
    if (data.theta_distribution && data.theta_distribution.counts && data.theta_distribution.bin_edges && data.theta_distribution.counts.length > 0) {
        quizThetaChartCanvas.style.display = 'block';
         const ctx = quizThetaChartCanvas.getContext('2d');
         const labels = data.theta_distribution.bin_edges.slice(0, -1).map((edge, i) =>
             `${edge.toFixed(2)} to ${data.theta_distribution.bin_edges[i+1].toFixed(2)}`
         );
         const counts = data.theta_distribution.counts;

         if (thetaChart) {
             thetaChart.destroy();
         }
         try {
             thetaChart = new Chart(ctx, {
                 type: 'bar',
                 data: {
                     labels: labels,
                     datasets: [{
                         label: 'Frequency',
                         data: counts,
                         backgroundColor: 'rgba(75, 192, 192, 0.7)',
                         borderColor: 'rgba(75, 192, 192, 1)',
                         borderWidth: 1,
                         barPercentage: 1.0,
                         categoryPercentage: 1.0
                     }]
                 },
                 options: {
                     scales: { x: { grid: { display: false } }, y: { beginAtZero: true, title: { display: true, text: 'Number of Participants'} } },
                     responsive: true,
                     maintainAspectRatio: false, // Allow chart to resize height
                     plugins: { title: { display: true, text: 'Final Theta Distribution' }, legend: { display: false } }
                 }
             });
         } catch(error) {
             showError(`Failed to render theta chart: ${error.message}`, quizThetaChartCanvas.parentElement);
         }

    } else {
         quizThetaChartCanvas.style.display = 'none'; // Hide canvas if no data
         if (thetaChart) thetaChart.destroy();
         quizPerfSummaryDiv.innerHTML += "<p><i>No theta distribution data available to display.</i></p>";
    }
}

function displayHeatmap(data) {
    if (!heatmapContainer) return;
    console.log("Received heatmap data:", data);

     if (!data || !data.heatmap_data) {
         showError("No heatmap data received.", heatmapContainer);
         // Clear existing heatmap if any
         if(heatmapInstance) heatmapInstance.setData({max:0, data:[]});
         return;
     }

    // Configure heatmap.js instance
    if (!heatmapInstance || heatmapInstance.config.container !== heatmapContainer) {
        try {
             // Clear container before creating new instance
            heatmapContainer.innerHTML = '';
            heatmapInstance = h337.create({
                container: heatmapContainer,
                radius: 20, maxOpacity: .6, minOpacity: 0, blur: .75
            });
            console.log("Created new heatmap instance.");
        } catch (error) {
            showError(`Failed to create heatmap instance: ${error.message}`, heatmapContainer);
            return; // Exit if instance creation fails
        }
    }

    // Format data
    let maxVal = 0;
    const points = data.heatmap_data || [];
    points.forEach(p => { if (p.value > maxVal) maxVal = p.value; });

    const heatmapData = {
        max: maxVal || 1, // Avoid max=0
        data: points
    };

    try {
        heatmapInstance.setData(heatmapData);
        console.log(`Set heatmap data: ${points.length} points, max value ${maxVal}`);
    } catch (error) {
         showError(`Failed to set heatmap data: ${error.message}`, heatmapContainer);
    }
}

function displayPdfStats(data) {
     if (!pdfStatsDisplayDiv) return;
      if (!data || data.message?.includes("No interaction data found")) {
         pdfStatsDisplayDiv.innerHTML = `<p><i>No interaction data found for ${data?.pdf_url || 'selected PDF'}.</i></p>`;
         return;
     }
     // Display the aggregated stats nicely formatted
     // Replace JSON dump with structured HTML
     let content = `<h4>Stats for ${escapeHtml(data.pdf_url)}</h4>`;
     content += `<p>Total Interactions Logged: <strong>${data.total_interactions_logged ?? 'N/A'}</strong></p>`;

     if (data.event_type_counts) {
         content += '<h5>Event Counts:</h5><ul>';
         for (const [event, count] of Object.entries(data.event_type_counts)) {
              content += `<li>${escapeHtml(event)}: ${count}</li>`;
         }
         content += '</ul>';
     }
      if (data.top_text_selections && data.top_text_selections.length > 0) {
         content += '<h5>Top Text Selections:</h5><ol>';
         data.top_text_selections.forEach(item => {
              content += `<li>"${escapeHtml(item.text)}" (${item.count} times)</li>`;
         });
         content += '</ol>';
     }
      // Add placeholders/display for other complex stats when service provides them
      if (data.avg_time_per_page) { content += `<p>Avg Time/Page: (See data)</p>`; } // TODO: Format better
      if (data.scroll_depth_histogram) { content += `<p>Scroll Depth: (See data)</p>`; } // TODO: Format better
      if (data.zoom_actions_count !== undefined) { content += `<p>Zoom Actions: ${data.zoom_actions_count}</p>`; }

     content += `${data.message ? `<p><i>Note: ${escapeHtml(data.message)}</i></p>` : ''}`;
     pdfStatsDisplayDiv.innerHTML = content;
}

function displayItemStats(data) {
     if (!itemStatsDisplayDiv) return;
     if (!data || data.total_administrations === undefined) {
          itemStatsDisplayDiv.innerHTML = `<p><i>No analysis data found for question ${data?.question_id || ''}.</i></p>`;
         return;
     }
     itemStatsDisplayDiv.innerHTML = `
          <h4>Analysis for Question ${escapeHtml(data.question_id)}</h4>
          <p>Total Administrations: <strong>${data.total_administrations ?? 'N/A'}</strong></p>
          <p>Correct Responses: <strong>${data.correct_response_count ?? 'N/A'}</strong></p>
          <p>Difficulty (P-value): <strong>${data.p_value?.toFixed(3) ?? 'N/A'}</strong></p>
          ${data.message ? `<p><i>Note: ${escapeHtml(data.message)}</i></p>` : ''}
     `;
}

// Simple HTML escaping helper
function escapeHtml(unsafe) {
    if (!unsafe || typeof unsafe !== 'string') return unsafe;
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}


// --- Event Handlers (Keep existing handlers) ---
async function handleLoadSurvey() {
     const surveyType = surveyTypeSelect?.value;
     const questionKey = surveyQuestionSelect?.value;
     if (!surveyType || !questionKey) { showError("Please select both a survey type and a question key."); return; }
     console.log(`Loading survey results for ${surveyType} / ${questionKey}...`);
     loadSurveyButton.disabled = true;
     showLoading(surveyDataTableDiv); // Show loading in table area
     if (surveyChart) surveyChart.destroy(); // Clear previous chart
     surveyChartCanvas.style.display = 'none'; // Hide canvas during load

     try {
         const data = await dashboardApiClient.getSurveyResults(surveyType, questionKey);
         displaySurveyResults(data);
     } catch (error) { /* Handled in fetchApi, error shown via showError */ }
     finally { loadSurveyButton.disabled = false; }
}

async function handleLoadHeatmap() {
     const target = heatmapTargetSelect?.value;
     if (!target) { showError("Please select a target element for the heatmap."); return; }
     console.log(`Loading heatmap data for ${target}...`);
     loadHeatmapButton.disabled = true;
     showLoading(heatmapContainer); // Show loading message in container

     try {
          const data = await dashboardApiClient.getHeatmapData(target);
          displayHeatmap(data); // Will replace loading message
     } catch (error) { /* Handled in fetchApi */ }
     finally { loadHeatmapButton.disabled = false; }
}

async function handleLoadPdfStats() {
     const pdfUrl = pdfSelect?.value;
     if (!pdfUrl) { showError("Please select a PDF file."); return; }
     console.log(`Loading PDF stats for ${pdfUrl}...`);
     loadPdfStatsButton.disabled = true;
     showLoading(pdfStatsDisplayDiv);

     try {
         const data = await dashboardApiClient.getPdfStats(pdfUrl);
         displayPdfStats(data);
     } catch (error) { /* Handled in fetchApi */ }
     finally { loadPdfStatsButton.disabled = false; }
}

async function handleLoadItemStats() {
     const questionId = itemSelect?.value;
     if (!questionId) { showError("Please select a Question ID."); return; }
     console.log(`Loading item analysis for ${questionId}...`);
     loadItemStatsButton.disabled = true;
     showLoading(itemStatsDisplayDiv);

     try {
         const data = await dashboardApiClient.getItemAnalysis(questionId);
         displayItemStats(data);
     } catch (error) { /* Handled in fetchApi */ }
     finally { loadItemStatsButton.disabled = false; }
}

// --- Initialization ---
async function initDashboard() {
    console.log("Initializing Dashboard...");
    showLoading(summaryStatsDiv); // Show loading initially

    // TODO: Implement actual authentication check and token retrieval
    const isLoggedIn = false; // Placeholder - Replace with real check
    // const authToken = getAuthToken(); // Replace with function to get token

    if (isLoggedIn) {
        authStatusElement.textContent = 'Logged In';
        logoutButton.style.display = 'inline-block';
        loginButton.style.display = 'none';
    } else {
         authStatusElement.textContent = 'Not Logged In';
         // loginButton.style.display = 'inline-block';
         logoutButton.style.display = 'none';
         console.warn("Dashboard: User not logged in (Placeholder). API calls might fail.");
         showError("Please log in to view dashboard data. (Auth not implemented)", summaryStatsDiv);
         // Disable controls if not logged in
         loadSurveyButton.disabled = true;
         loadHeatmapButton.disabled = true;
         loadPdfStatsButton.disabled = true;
         loadItemStatsButton.disabled = true;
         return; // Stop initialization if not logged in
    }

    // Attach event listeners
    loadSurveyButton?.addEventListener('click', handleLoadSurvey);
    loadHeatmapButton?.addEventListener('click', handleLoadHeatmap);
    loadPdfStatsButton?.addEventListener('click', handleLoadPdfStats);
    loadItemStatsButton?.addEventListener('click', handleLoadItemStats);

    // TODO: Populate select dropdowns dynamically (survey questions, heatmap targets, pdfs, item ids)
    // Requires API endpoints or hardcoded lists for now.

    // Fetch initial summary data and quiz performance on load
    try {
         const [summaryData, quizPerfData] = await Promise.all([
              dashboardApiClient.getSummary(),
              dashboardApiClient.getQuizPerformance()
         ]);
         displaySummaryStats(summaryData);
         displayQuizPerformance(quizPerfData);
    } catch (error) {
         console.error("Failed to load initial dashboard data:", error);
         // Error shown by API client or specific display functions
         showError("Failed to load initial dashboard data.", summaryStatsDiv); // Show general error
    }

    console.log("Dashboard Initialized.");
}

// --- Run Initialization ---
document.addEventListener('DOMContentLoaded', initDashboard);