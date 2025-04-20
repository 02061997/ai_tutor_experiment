// frontend/js/modules/quiz_ui.js
'use strict';

// --- Module State ---
let questionContainer = null;
let feedbackContainer = null;
let submitButton = null;
let onAnswerSubmitCallback = null; // Function provided by app2_tutor.js

let currentQuestion = null; // Store the data of the question currently displayed
let selectedAnswerIndex = null; // Store the index (0, 1, 2...) of the selected radio button

// --- Private Helper Functions ---

/**
 * Handles the click event on the submit button.
 */
function handleSubmit() {
    if (selectedAnswerIndex === null) {
        showFeedback("Please select an answer before submitting.", true);
        return;
    }
    if (!currentQuestion || !currentQuestion.question_id) {
         showFeedback("Error: Cannot submit, current question data is missing.", true);
         return;
    }

    // Prepare data in the format expected by the backend API schema (QuizAnswerInput)
    const answerData = {
        question_id: currentQuestion.question_id,
        selected_option_index: selectedAnswerIndex,
        // Optional: Add frontend timestamp if needed by backend/analysis
        // timestamp: new Date().toISOString()
    };

    // Show submitting feedback and disable button
    showFeedback("Submitting answer...");
    setSubmitButtonState(false);

    // Call the callback provided by app2_tutor.js to handle the submission logic
    if (typeof onAnswerSubmitCallback === 'function') {
        onAnswerSubmitCallback(answerData);
    } else {
         console.error("Quiz UI Error: onAnswerSubmit callback is not defined.");
         showFeedback("Internal Error: Cannot submit answer.", true);
         // Re-enable button maybe? Or leave disabled as something is wrong.
    }
}

/**
 * Handles changes in radio button selection.
 * @param {Event} event - The change event from the radio button group.
 */
function handleOptionChange(event) {
    selectedAnswerIndex = parseInt(event.target.value, 10); // Value is the option index
    setSubmitButtonState(true); // Enable submit button once an option is selected
    clearFeedback(); // Clear any previous feedback (like 'select an answer')
    console.log(`Selected option index: ${selectedAnswerIndex}`);
}

// --- Exported Functions ---

/**
 * Initializes the Quiz UI module.
 * @param {object} config - Configuration object.
 * @param {string} config.questionContainerId - ID of the div to display questions.
 * @param {string} config.feedbackContainerId - ID of the div for feedback messages.
 * @param {string} config.submitButtonId - ID of the submit answer button.
 * @param {Function} config.onAnswerSubmit - Callback function executed when the user submits an answer.
 * It receives the answer data object as an argument.
 */
export function initQuizUi(config) {
    questionContainer = document.getElementById(config.questionContainerId);
    feedbackContainer = document.getElementById(config.feedbackContainerId);
    submitButton = document.getElementById(config.submitButtonId);
    onAnswerSubmitCallback = config.onAnswerSubmit;

    if (!questionContainer || !feedbackContainer || !submitButton) {
        console.error("Quiz UI initialization failed: One or more required DOM elements not found.");
        return;
    }
     if (typeof onAnswerSubmitCallback !== 'function') {
          console.error("Quiz UI initialization failed: onAnswerSubmit callback function is required.");
          return;
     }


    console.log("Initializing Quiz UI.");

    // Attach event listener to submit button
    submitButton.addEventListener('click', handleSubmit);

    // Set initial state
    questionContainer.innerHTML = '<p>Waiting for quiz to start...</p>';
    setSubmitButtonState(false); // Initially disabled
}

/**
 * Displays a quiz question and its options.
 * Clears previous question and feedback.
 * @param {object} questionData - Object matching QuizQuestionForParticipant schema.
 * (e.g., { question_id: '...', question_text: '...', options: [...] })
 */
export function displayQuestion(questionData) {
    if (!questionContainer || !questionData) {
        console.error("Cannot display question: Container or question data missing.");
        return;
    }
    currentQuestion = questionData; // Store current question data
    selectedAnswerIndex = null; // Reset selected answer

    console.log(`Displaying Question ID: ${questionData.question_id}`);

    // Clear previous content
    questionContainer.innerHTML = '';
    clearFeedback();

    // Display question text
    const questionTextElement = document.createElement('p');
    questionTextElement.textContent = questionData.question_text;
    questionTextElement.style.fontWeight = 'bold'; // Make question text stand out
    questionContainer.appendChild(questionTextElement);

    // Display options as radio buttons
    const optionsList = document.createElement('div');
    optionsList.classList.add('quiz-options'); // Add class for styling

    questionData.options.forEach((optionText, index) => {
        const optionId = `q${questionData.question_id}_opt${index}`; // Unique ID for label/input

        const item = document.createElement('div');
        item.classList.add('quiz-option-item'); // Class for styling each option row

        const radioInput = document.createElement('input');
        radioInput.type = 'radio';
        radioInput.name = `question_${questionData.question_id}`; // Group radios for the same question
        radioInput.value = index; // The value will be the option's index
        radioInput.id = optionId;
        radioInput.addEventListener('change', handleOptionChange); // Update selection state on change

        const label = document.createElement('label');
        label.htmlFor = optionId;
        label.textContent = optionText;

        item.appendChild(radioInput);
        item.appendChild(label);
        optionsList.appendChild(item);
    });

    questionContainer.appendChild(optionsList);

    // Ensure submit button is enabled (it might have been disabled after completion)
    setSubmitButtonState(false); // Start disabled until an option is chosen
}

/**
 * Displays the quiz completion message and any final results.
 * @param {object} resultsData - Object containing completion status and potentially results
 * (matches relevant parts of QuizNextQuestionResponse schema).
 */
export function displayCompletion(resultsData) {
     if (!questionContainer || !feedbackContainer) return;
     currentQuestion = null; // No current question anymore
     selectedAnswerIndex = null;

     console.log("Displaying Quiz Completion.");

     questionContainer.innerHTML = '<h3>Quiz Complete!</h3>';

     // Display final results/feedback if available
     let resultsHtml = '<p>Thank you for completing the quiz.</p>';
     if (resultsData.final_score_percent !== undefined && resultsData.final_score_percent !== null) {
         resultsHtml += `<p>Final Score: ${resultsData.final_score_percent.toFixed(1)}%</p>`;
     }
      if (resultsData.current_theta !== undefined && resultsData.current_theta !== null) {
          resultsHtml += `<p>Estimated Ability (Theta): ${resultsData.current_theta.toFixed(3)} (SE: ${resultsData.current_se?.toFixed(3) ?? 'N/A'})</p>`;
      }
      if (resultsData.identified_weak_topics && resultsData.identified_weak_topics.length > 0) {
          resultsHtml += `<p>Areas for review: ${resultsData.identified_weak_topics.join(', ')}</p>`;
          // TODO: Potentially link these topics or trigger recommendation display
      }

      feedbackContainer.innerHTML = resultsHtml;
      feedbackContainer.style.color = 'black'; // Reset color

      setSubmitButtonState(false); // Disable submit button
      // Optional: Change button text (e.g., "Finished") or hide it
      // submitButton.textContent = "Finished";
}

/**
 * Displays a feedback message to the user (e.g., error, status).
 * @param {string} message - The message text to display.
 * @param {boolean} [isError=false] - If true, style the message as an error.
 */
export function showFeedback(message, isError = false) {
    if (!feedbackContainer) return;
    feedbackContainer.textContent = message;
    feedbackContainer.style.color = isError ? 'red' : 'gray'; // Simple styling
}

/**
 * Clears any messages from the feedback container.
 */
export function clearFeedback() {
     if (!feedbackContainer) return;
     feedbackContainer.textContent = '';
}

/**
 * Enables or disables the submit button.
 * @param {boolean} isEnabled - True to enable, false to disable.
 */
export function setSubmitButtonState(isEnabled) {
    if (!submitButton) return;
    submitButton.disabled = !isEnabled;
}