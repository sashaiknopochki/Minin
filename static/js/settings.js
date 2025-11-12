/**
 * Settings page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settings-form');
    const primaryLanguageSelect = document.getElementById('primary-language');

    // Load available languages
    loadLanguagesForSettings();

    // Load current user settings
    loadUserSettings();

    // Form submission
    if (settingsForm) {
        settingsForm.addEventListener('submit', saveSettings);
    }
});

/**
 * Load available languages for settings
 */
async function loadLanguagesForSettings() {
    try {
        const response = await apiRequest('/languages');
        const select = document.getElementById('primary-language');

        // TODO: Populate language select options
    } catch (error) {
        showNotification('Failed to load languages', 'error');
    }
}

/**
 * Load current user settings
 */
async function loadUserSettings() {
    try {
        const response = await apiRequest('/user');
        // TODO: Populate form with current settings
    } catch (error) {
        showNotification('Failed to load settings', 'error');
    }
}

/**
 * Save user settings
 */
async function saveSettings(event) {
    event.preventDefault();

    const primaryLanguageId = document.getElementById('primary-language').value;
    const quizFrequency = document.getElementById('quiz-frequency').value;

    try {
        await apiRequest('/user/settings', {
            method: 'PUT',
            body: JSON.stringify({
                primary_language_id: primaryLanguageId,
                quiz_frequency: quizFrequency,
            }),
        });

        showNotification('Settings saved successfully', 'success');
    } catch (error) {
        showNotification('Failed to save settings', 'error');
    }
}
