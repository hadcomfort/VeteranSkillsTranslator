// =============================================================================
//  Military Skills Translator - Frontend Logic
// =============================================================================
//
//  DESCRIPTION:
//  This script manages all client-side interactivity for the application.
//  It handles user input, fetches data from the backend API, and dynamically
//  updates the DOM with the results in a secure, performant, and
//  accessible manner.
//
//  PRINCIPLES APPLIED:
//  - Progressive Enhancement: The core content (list of occupations) is
//    available without JavaScript. This script enhances the experience by
//    adding dynamic skill loading.
//  - Accessibility (a11y): Follows ARIA patterns for asynchronous updates,
//    focus management, and live announcements.
//  - Security: Exclusively uses `.textContent` and template elements to
//    prevent Cross-Site Scripting (XSS) attacks. No `innerHTML`.
//  - Resilience: Uses an AbortController to prevent race conditions from
//    rapid user selections.
//  - Performance: Caches DOM elements, uses a DocumentFragment for rendering,
//    and employs event delegation to minimize overhead.
//
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Cache DOM Elements ---
    // Caching elements that are frequently accessed prevents repeated, costly
    // DOM lookups, leading to better performance.
    const searchInput = document.getElementById('search-input');
    const mosSelect = document.getElementById('mos-select');
    const skillsList = document.getElementById('skills-list');
    const skillsContainer = document.getElementById('skills-list-container');
    const resultsPlaceholder = document.getElementById('results-placeholder');
    const skillsHeading = document.getElementById('skills-heading');
    const skillItemTemplate = document.getElementById('skill-item-template');
    const srAnnouncer = document.getElementById('sr-announcer');
    const copyFeedback = document.getElementById('copy-feedback');

    // --- 2. AbortController for Resilient Fetching ---
    // A single AbortController is used for all fetch requests. If the user
    // selects a new MOS while a request is already in-flight, we can abort
    // the old request before starting a new one. This prevents a race condition
    // where an earlier, slower request could overwrite the results of a newer one.
    let abortController = new AbortController();

    // --- 3. Event Listeners ---
    mosSelect.addEventListener('change', handleMosSelection);

    // A single event listener on the parent list uses event delegation. This is
    // more performant than adding a listener to every single button and placeholder.
    skillsList.addEventListener('click', (event) => {
        const copyButton = event.target.closest('.skills-list__copy-btn');
        if (copyButton) {
            handleCopyClick(copyButton);
            return;
        }

        const placeholder = event.target.closest('.placeholder');
        if (placeholder) {
            handlePlaceholderClick(placeholder);
            return;
        }
    });

    searchInput.addEventListener('input', filterOccupations);


    /**
     * Filters the occupation dropdown based on user input.
     */
    function filterOccupations() {
        const searchTerm = searchInput.value.toLowerCase();
        const options = mosSelect.options;

        for (let i = 1; i < options.length; i++) { // Start at 1 to skip the placeholder
            const option = options[i];
            const optionText = option.textContent.toLowerCase();
            const shouldBeVisible = optionText.includes(searchTerm);
            option.style.display = shouldBeVisible ? '' : 'none';
        }
    }

    /**
     * Handles the 'change' event on the MOS select dropdown.
     */
    function handleMosSelection() {
        const mosCode = mosSelect.value;

        // Abort any ongoing fetch request.
        abortController.abort();
        // Create a new AbortController for the new request.
        abortController = new AbortController();

        if (mosCode) {
            fetchSkills(mosCode, abortController.signal);
        } else {
            resetSkillsList();
        }
    }

    /**
     * Fetches and renders skills for the selected MOS code.
     * @param {string} mosCode - The MOS code to fetch skills for.
     * @param {AbortSignal} signal - The signal from an AbortController to cancel the fetch.
     */
    async function fetchSkills(mosCode, signal) {
        setLoadingState(true);

        try {
            const response = await fetch(`/api/mos/${mosCode}`, { signal });

            if (!response.ok) {
                // The API returns a detailed error message, but for the user,
                // a simple message is often better. We log the details.
                const errorData = await response.json();
                console.error('API Error:', errorData);
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            renderSkills(data);
            announceToScreenReader(`${data.skills.length} skills for ${data.title} loaded.`);

        } catch (error) {
            if (error.name === 'AbortError') {
                // This is an expected error when the user makes a new selection
                // before the previous one has finished. We can safely ignore it.
                console.log('Fetch aborted.');
            } else {
                console.error('Fetch error:', error);
                displayError();
                announceToScreenReader('An error occurred while loading skills.');
            }
        } finally {
            setLoadingState(false);
        }
    }

    /**
     * Manages the UI's loading state for accessibility and user feedback.
     * @param {boolean} isLoading - Whether to enter or exit the loading state.
     */
    function setLoadingState(isLoading) {
        if (isLoading) {
            resultsPlaceholder.style.display = 'none';
            skillsList.innerHTML = ''; // Clear previous results
            skillsContainer.setAttribute('aria-busy', 'true');
            announceToScreenReader('Loading skills...');
        } else {
            skillsContainer.setAttribute('aria-busy', 'false');
        }
    }

    /**
     * Renders the fetched skills into the DOM.
     * @param {object} data - The API response data, containing a title and skills array.
     */
    function renderSkills(data) {
        skillsList.innerHTML = ''; // Ensure list is empty before rendering
        resultsPlaceholder.style.display = 'none';

        // Using a DocumentFragment is more performant for bulk DOM manipulations.
        // The browser only reflows the page once when the fragment is appended.
        const fragment = new DocumentFragment();

        data.skills.forEach(skillText => {
            const templateClone = skillItemTemplate.content.cloneNode(true);
            const textElement = templateClone.querySelector('.skills-list__text');

            // Security: Use textContent, not innerHTML, to prevent XSS.
            textElement.textContent = skillText;

            // Enhance the text by wrapping placeholders, without using innerHTML.
            highlightPlaceholder(textElement, '[Number]');

            fragment.appendChild(templateClone);
        });

        skillsList.appendChild(fragment);

        // Accessibility: Programmatically move focus to the results heading.
        // This directs screen reader users to the newly loaded content.
        skillsHeading.focus();
    }

    /**
     * Resets the skills list to its initial placeholder state.
     */
    function resetSkillsList() {
        skillsList.innerHTML = '';
        resultsPlaceholder.style.display = 'block';
    }

    /**
     * Displays an error message in the results area.
     */
    function displayError() {
        skillsList.innerHTML = '';
        resultsPlaceholder.textContent = 'Sorry, we could not load the skills. Please try again.';
        resultsPlaceholder.style.display = 'block';
    }

    /**
     * Safely finds and wraps a placeholder string (e.g., '[Number]') in a <span>
     * for styling, without using the insecure `innerHTML` property.
     * @param {HTMLElement} element - The element containing the text.
     * @param {string} placeholder - The placeholder string to wrap.
     */
    function highlightPlaceholder(element, placeholder) {
        // This function directly manipulates text nodes for security and precision.
        for (const node of element.childNodes) {
            if (node.nodeType === Node.TEXT_NODE) {
                if (node.textContent.includes(placeholder)) {
                    const parts = node.textContent.split(placeholder);
                    const newNodes = [];
                    parts.forEach((part, index) => {
                        newNodes.push(document.createTextNode(part));
                        if (index < parts.length - 1) {
                            const span = document.createElement('span');
                            span.className = 'placeholder';
                            span.textContent = placeholder;
                            newNodes.push(span);
                        }
                    });
                    element.replaceChild(createFragment(newNodes), node);
                }
            }
        }
    }

    /**
     * Helper to create a DocumentFragment from an array of nodes.
     * @param {Node[]} nodes - An array of DOM nodes.
     * @returns {DocumentFragment}
     */
    function createFragment(nodes) {
        const fragment = new DocumentFragment();
        nodes.forEach(node => fragment.appendChild(node));
        return fragment;
    }


    /**
     * Handles a click on a placeholder span, making it editable.
     * @param {HTMLElement} placeholder - The placeholder span element that was clicked.
     */
    function handlePlaceholderClick(placeholder) {
        // Create an input field to replace the span
        const input = document.createElement('input');
        input.type = 'number';
        input.className = 'placeholder-input';
        input.value = placeholder.textContent.replace(/\D/g, '') || 1; // Use existing number or default to 1
        input.style.width = `${(input.value.length + 2)}ch`; // Set width based on content

        // Replace the placeholder span with the new input field
        placeholder.replaceWith(input);
        input.focus();
        input.select();

        // Event listener to save the value when the input loses focus
        input.addEventListener('blur', () => {
            savePlaceholderValue(input);
        });

        // Event listener to save the value when 'Enter' is pressed
        input.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                input.blur(); // Trigger the blur event to save
            }
            // Adjust width dynamically as user types
            input.style.width = `${(input.value.length + 2)}ch`;
        });
    }

    /**
     * Replaces an input field with a styled span containing the new value.
     * @param {HTMLInputElement} input - The input field to be replaced.
     */
    function savePlaceholderValue(input) {
        const value = input.value.trim();
        const newPlaceholder = document.createElement('span');
        newPlaceholder.className = 'placeholder filled'; // Add 'filled' class for styling
        newPlaceholder.textContent = `[${value || 'Number'}]`; // Fallback if empty

        input.replaceWith(newPlaceholder);
    }

    /**
     * Handles the click event on a copy button.
     * @param {HTMLButtonElement} copyButton - The button that was clicked.
     */
    function handleCopyClick(copyButton) {
        const skillItem = copyButton.closest('.skills-list__item');
        const skillTextElement = skillItem.querySelector('.skills-list__text');

        // .innerText correctly reads the rendered text content, including values
        // from the updated placeholders.
        const textToCopy = skillTextElement.innerText.replace(/\s+/g, ' ').trim();

        navigator.clipboard.writeText(textToCopy).then(() => {
            showCopyFeedback('Copied to clipboard!');
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            showCopyFeedback('Failed to copy.');
        });
    }

    /**
     * Displays a temporary feedback message for the copy action.
     * @param {string} message - The message to display.
     */
    function showCopyFeedback(message) {
        copyFeedback.textContent = message;
        copyFeedback.classList.add('visible');

        // Hide the message after a short delay.
        setTimeout(() => {
            copyFeedback.classList.remove('visible');
        }, 2000);
    }

    /**
     * Sends a message to the ARIA live region for screen readers.
     * @param {string} message - The message to be announced.
     */
    function announceToScreenReader(message) {
        srAnnouncer.textContent = message;
        // Clear the text after a moment so it can be re-announced if needed.
        setTimeout(() => {
            srAnnouncer.textContent = '';
        }, 500);
    }
});
