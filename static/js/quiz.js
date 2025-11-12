/**
 * Quiz page functionality
 */

let currentQuiz = null;

document.addEventListener('DOMContentLoaded', function() {
    const quizContainer = document.getElementById('quiz-container');

    // Load next quiz question
    loadNextQuiz();
});

/**
 * Load the next quiz question
 */
async function loadNextQuiz() {
    try {
        const response = await apiRequest('/quiz/next');
        currentQuiz = response;
        // TODO: Display quiz question
    } catch (error) {
        showNotification('Failed to load quiz', 'error');
    }
}

/**
 * Submit quiz answer
 */
async function submitAnswer(answer) {
    if (!currentQuiz) return;

    try {
        const response = await apiRequest('/quiz/answer', {
            method: 'POST',
            body: JSON.stringify({
                quiz_id: currentQuiz.id,
                answer: answer,
            }),
        });

        // TODO: Display results
        if (response.is_correct) {
            showNotification('Correct answer!', 'success');
        } else {
            showNotification('Incorrect answer. Try again!', 'warning');
        }

        // Load next quiz after delay
        setTimeout(loadNextQuiz, 2000);
    } catch (error) {
        showNotification('Failed to submit answer', 'error');
    }
}

/**
 * Skip current quiz question
 */
function skipQuiz() {
    loadNextQuiz();
}
