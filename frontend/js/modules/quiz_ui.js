/**
 * @fileoverview Manages the Quiz UI elements and interactions for App2.
 */

export class QuizUI {
    /**
     * Initializes the QuizUI component.
     * @param {string} containerSelector - The CSS selector for the main quiz container element (#quiz-section).
     * @param {function} submitAnswerCallback - The function to call when an answer is submitted.
     * It receives the selected answer letter ('A', 'B', 'C', or 'D').
     */
    constructor(containerSelector, submitAnswerCallback) {
        this.container = document.querySelector(containerSelector);
        if (!this.container) {
            // This error should not appear if the HTML is correct now
            console.error(`QuizUI Error: Container element "${containerSelector}" not found.`);
            alert(`Critical Frontend Error: Quiz container "${containerSelector}" is missing in the HTML.`);
            return;
        }

        // --- Find Core Quiz Elements within the container ---
        this.quizContent = this.container.querySelector('.quiz-content');
        this.questionContainer = this.container.querySelector('.question-container');
        this.questionTextElement = this.container.querySelector('.quiz-question-text');
        this.optionsContainer = this.container.querySelector('.quiz-options');
        this.submitButton = this.container.querySelector('.submit-quiz-answer-btn');
        this.feedbackElement = this.container.querySelector('.quiz-feedback');

        // --- UI State Elements ---
        this.loadingIndicator = this.container.querySelector('.loading-indicator');
        this.completionMessageElement = this.container.querySelector('.quiz-completion-message');
        this.errorMessageContainer = this.container.querySelector('.error-message-container');

        // --- Check if all essential elements were found ---
        if (!this.quizContent || !this.questionContainer || !this.questionTextElement || !this.optionsContainer || !this.submitButton || !this.feedbackElement || !this.loadingIndicator || !this.completionMessageElement || !this.errorMessageContainer) {
            console.error("QuizUI Error: One or more essential child elements (.quiz-content, .question-container, .quiz-question-text, .quiz-options, .submit-quiz-answer-btn, .quiz-feedback, .loading-indicator, .quiz-completion-message, .error-message-container) not found within the container:", containerSelector);
            // Optionally display an error to the user within the container
            if(this.container) this.container.innerHTML = `<p class="error" style="color: red; font-weight: bold;">Quiz UI failed to initialize correctly. Required HTML structure is missing.</p>`;
            return; // Stop initialization
        }

        this.submitAnswerCallback = submitAnswerCallback;
        this.currentQuestionData = null; // Store the current question data

        // --- Initial State ---
        this._hideElement(this.loadingIndicator);
        this._hideElement(this.feedbackElement);
        this._hideElement(this.completionMessageElement);
        this._hideElement(this.errorMessageContainer);
        // Hide content initially, show it when a question is loaded
        this._hideElement(this.quizContent);

        // --- Event Listeners ---
        this.submitButton.addEventListener('click', () => this._handleSubmit());

        console.log("QuizUI initialized successfully.");
    }

    // --- CORRECTED showQuestion Method ---
    /**
     * Displays a quiz question and its options.
     * @param {object} questionData - The question data object from the backend.
     * Expected format: { mcq_id: string, question: string, options: string[], ... }
     */
    showQuestion(questionData) {
        // Add Debug Log
        console.log("DEBUG: quizUi.showQuestion executing with data:", questionData);
        console.log("🛠 raw questionData payload:", questionData);

        // Validate incoming data structure (uses .question_text and .options) // <-- UPDATED CHECK
        if (!questionData || typeof questionData.question !== 'string' || !Array.isArray(questionData.options) || !this.questionTextElement || !this.optionsContainer) {
            console.error("QuizUI Error: Cannot show question, invalid data structure received or required elements missing.", {
                hasQuestionText: !!questionData?.question, // <-- UPDATED CHECK (optional change for clarity)
                hasOptions: Array.isArray(questionData?.options),
                hasTextElement: !!this.questionTextElement,
                hasOptionsContainer: !!this.optionsContainer
            });
            this.showError("Failed to display the quiz question due to invalid data from server.");
            // Keep content hidden if data is bad
            this._hideElement(this.quizContent);
            this._hideElement(this.loadingIndicator);
            this._showElement(this.errorMessageContainer); // Show error message area
            return;
        }

        this.currentQuestionData = questionData; // Store current data if needed later
        this._hideElement(this.errorMessageContainer); // Hide previous errors
        this._hideElement(this.feedbackElement);
        this._hideElement(this.completionMessageElement);

        // Display the question text using .question_text // <-- UPDATED ASSIGNMENT
        this.questionTextElement.textContent = questionData.question; // Use .question_text field
        this.optionsContainer.innerHTML = ''; // Clear previous options

        // Create and append radio buttons for options
        questionData.options.forEach((optionText, index) => {
            if (typeof optionText !== 'string') {
                console.warn(`QuizUI Warning: Option at index ${index} is not a string:`, optionText);
                optionText = String(optionText); // Attempt conversion
            }
            const li = document.createElement('li');
            const input = document.createElement('input');
            const label = document.createElement('label');
            // Use question ID in uniqueId to ensure label 'for' works correctly if multiple quizzes were on page
            const uniqueId = `option_${questionData.mcq_id}_${index}`;

            input.type = 'radio';
            input.name = `quizOption_${questionData.mcq_id}`; // Unique name per question prevents cross-selection
            input.value = String.fromCharCode(65 + index); // Value is 'A', 'B', 'C', 'D'
            input.id = uniqueId;

            label.htmlFor = uniqueId;
            label.textContent = optionText; // Display the actual option text

            li.appendChild(input);
            li.appendChild(label);
            this.optionsContainer.appendChild(li);
        });

        this._enableSubmitButton();
        // Ensure main content area is visible now
        this._showElement(this.quizContent);
        // Keep loading hidden
        this._hideElement(this.loadingIndicator);

        console.log("QuizUI: Question displayed successfully.");
    }

    // --- CORRECTED _handleSubmit Method ---
    /**
     * Handles the submission of an answer.
     * Calls the callback with the selected letter ('A', 'B', 'C', 'D').
     * @private
     */
    _handleSubmit() {
        // Find the checked radio button within the options container
        const selectedOptionInput = this.optionsContainer.querySelector('input[type="radio"]:checked');

        if (selectedOptionInput) {
            const selectedLetter = selectedOptionInput.value; // Get the value ('A'/'B'/'C'/'D')
            console.log(`QuizUI: Submit button clicked. Selected Letter: ${selectedLetter}`);
            this._disableSubmitButton();
            this._hideElement(this.feedbackElement); // Hide old feedback

            // Ensure the callback function exists before calling it
            if (this.submitAnswerCallback && typeof this.submitAnswerCallback === 'function') {
                this.submitAnswerCallback(selectedLetter); // Pass the LETTER ('A'/'B'/'C'/'D') to the callback
            } else {
                console.error("QuizUI Error: submitAnswerCallback is not defined or not a function!");
                this.showError("Error submitting answer (callback missing).", true);
                this._enableSubmitButton(); // Re-enable if callback fails
            }
        } else {
            // No option selected
            this.showError("Please select an answer before submitting.", true); // Show temporary error
        }
    }


    /**
     * Shows feedback after an answer has been submitted and evaluated.
     * @param {boolean} isCorrect - Whether the submitted answer was correct.
     * @param {string} correctAnswerText - The actual text of the correct answer option.
     * @param {string} [explanation] - An optional explanation.
     */
    showFeedback(isCorrect, correctAnswerText, explanation = '') {
        if (!this.feedbackElement) return;
        this._showElement(this.feedbackElement); // Make feedback area visible

        let feedbackHTML = '';
        if (isCorrect) {
            feedbackHTML = '<p class="correct"><strong>Correct!</strong></p>';
            this.feedbackElement.classList.remove('incorrect');
            this.feedbackElement.classList.add('correct');
        } else {
            // Show the correct answer text
            feedbackHTML = `<p class="incorrect"><strong>Incorrect.</strong> The correct answer was: ${correctAnswerText || '[Answer unavailable]'}</p>`;
            this.feedbackElement.classList.remove('correct');
            this.feedbackElement.classList.add('incorrect');
        }

        if (explanation) {
            feedbackHTML += `<p class="explanation">${explanation}</p>`;
        }

        this.feedbackElement.innerHTML = feedbackHTML;
        // Re-enable submit button AFTER showing feedback, allowing user to change answer? Or wait for next question?
        // Let's assume flow proceeds to next question or completion, keep button disabled.
        // If you want users to retry, you might enable it here.
    }

    /**
     * Resets parts of the UI for the next question.
     */
    resetForNextQuestion() {
        this._hideElement(this.feedbackElement);
        this.feedbackElement.className = 'quiz-feedback'; // Reset feedback style classes
        if(this.optionsContainer) this.optionsContainer.innerHTML = '';
        if(this.questionTextElement) this.questionTextElement.textContent = '';
        // Keep submit button disabled until new options are loaded by showQuestion
        this._disableSubmitButton();
    }

    /**
     * Shows a completion message when the quiz is finished.
     * @param {string} message - The message to display.
     */
    showCompletionMessage(message) {
        if (this.completionMessageElement) {
            this.completionMessageElement.textContent = message;
            this._hideElement(this.quizContent); // Hide question/options area
            this._hideElement(this.feedbackElement); // Hide feedback
            this._hideElement(this.errorMessageContainer); // Hide errors
            this._hideElement(this.loadingIndicator); // Hide loading
            this._showElement(this.completionMessageElement); // Show completion message
        }
    }

    /**
     * Shows the loading indicator and hides the main quiz content.
     */
    showLoading() {
        console.log("QuizUI: Showing loading indicator...");
        if (this.quizContent) this._hideElement(this.quizContent);
        if (this.feedbackElement) this._hideElement(this.feedbackElement); // Hide feedback while loading
        if (this.errorMessageContainer) this._hideElement(this.errorMessageContainer);
        if (this.completionMessageElement) this._hideElement(this.completionMessageElement); // Hide completion msg
        if (this.loadingIndicator) this._showElement(this.loadingIndicator);
    }

    /**
     * Hides the loading indicator. Called before showing question/error/completion.
     */
    hideLoading() {
        console.log("QuizUI: Hiding loading indicator...");
        if (this.loadingIndicator) this._hideElement(this.loadingIndicator);
    }

    /**
     * Displays an error message in the designated container.
     * Hides other primary content areas.
     * @param {string} message - The error message to display.
     * @param {boolean} [temporary=false] - If true, hide the message after a delay.
     */
    showError(message, temporary = false) {
        if (this.errorMessageContainer) {
            this.errorMessageContainer.textContent = message;
            this._showElement(this.errorMessageContainer); // Show error
            this._hideElement(this.loadingIndicator); // Hide loading
            this._hideElement(this.quizContent); // Hide main quiz content
            this._hideElement(this.feedbackElement); // Hide feedback
            this._hideElement(this.completionMessageElement); // Hide completion

            if (temporary) {
                setTimeout(() => {
                    // Only hide if it hasn't been replaced by another message/state
                    if(this.errorMessageContainer.textContent === message) {
                        this._hideElement(this.errorMessageContainer);
                    }
                }, 3500); // Hide after 3.5 seconds
            }
        } else {
            console.error("QuizUI Error Display Failed (No Container):", message);
        }
    }


    // --- Helper Methods ---
    _disableSubmitButton() {
        if (this.submitButton) this.submitButton.disabled = true;
    }
    _enableSubmitButton() {
        if (this.submitButton) this.submitButton.disabled = false;
    }
    _showElement(element) {
        if (element) element.style.display = ''; // Use default display
    }
    _hideElement(element) {
        if (element) element.style.display = 'none';
    }

    /**
     * Resets the entire quiz UI to its initial state (e.g., before starting).
     */
    reset() {
        console.log("QuizUI: Resetting UI.");
        this.resetForNextQuestion(); // Clears feedback, options, question text
        this._hideElement(this.completionMessageElement);
        this._hideElement(this.errorMessageContainer);
        this._hideElement(this.loadingIndicator);
        // Keep quiz content hidden until showQuestion is called
        this._hideElement(this.quizContent);
        this.currentQuestionData = null;
    }
}