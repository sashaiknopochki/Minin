/**
 * Translation page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const languagesContainer = document.getElementById('languages-container');
    const addLanguageBtn = document.getElementById('add-language-btn');

    // Load available languages
    loadLanguages();

    // Add language button click handler
    if (addLanguageBtn) {
        addLanguageBtn.addEventListener('click', addLanguageField);
    }

    // Load search history
    loadSearchHistory();
});

/**
 * Load available languages from API
 */
async function loadLanguages() {
    try {
        const response = await apiRequest('/languages');
        // TODO: Populate language fields
    } catch (error) {
        showNotification('Failed to load languages', 'error');
    }
}

/**
 * Add a new language input field
 */
function addLanguageField() {
    // TODO: Implement add language field
}

/**
 * Handle translation on input change
 */
async function handleTranslation(event) {
    // TODO: Implement translation on input
}

/**
 * Load and display search history
 */
async function loadSearchHistory() {
    try {
        const response = await apiRequest('/search-history');
        // TODO: Display search history
    } catch (error) {
        console.error('Failed to load search history:', error);
    }
}

/**
 * Delete a phrase from history
 */
async function deletePhrase(phraseId) {
    try {
        await apiRequest(`/phrases/${phraseId}`, {
            method: 'DELETE',
        });
        showNotification('Phrase deleted', 'success');
        loadSearchHistory(); // Reload history
    } catch (error) {
        showNotification('Failed to delete phrase', 'error');
    }
}
