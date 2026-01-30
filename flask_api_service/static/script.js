document.addEventListener('DOMContentLoaded', () => {
    const inputField = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const chatMessages = document.getElementById('chat-messages');

    // Focus input on load
    inputField.focus();

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);
    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const query = inputField.value.trim();
        if (!query) return;

        // Add user message
        addMessage(query, 'user');
        inputField.value = '';

        // Add loading state
        const loadingId = addLoadingMessage();

        // Send to API
        fetch('/handle_user_query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // Add guest header for dev mode bypass
                'X-Guest-User': 'true'
            },
            body: JSON.stringify({
                query: query,
                // You might need to generate or store a session/chat ID
                chat_id: "bc9f871c-6f26-44cc-853c-8ac98209e37a"
            })
        })
            .then(response => response.json())
            .then(data => {
                // Remove loading
                removeMessage(loadingId);

                // Process response
                handleResponse(data);
            })
            .catch(error => {
                removeMessage(loadingId);
                addMessage("Sorry, something went wrong. Please try again.", 'bot', true);
                console.error('Error:', error);
            });
    }

    function addMessage(text, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;

        const avatarDiv = document.createElement('div');
        avatarDiv.className = `avatar-${sender}`;
        avatarDiv.innerHTML = sender === 'bot'
            ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M12 22V12"/><path d="M12 12a5 5 0 0 0 5-5H7a5 5 0 0 0 5 5z"/><path d="M8 22H5a2 2 0 0 1-2-2v-4a5 5 0 0 1 5-5h8a5 5 0 0 1 5 5v4a2 2 0 0 1-2 2h-3"/></svg>`
            : 'U'; // Simple text for user or an icon

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        if (isError) contentDiv.style.borderColor = 'var(--error)';

        contentDiv.innerHTML = `<p>${escapeHtml(text)}</p>`;

        messageDiv.appendChild(sender === 'bot' ? avatarDiv : contentDiv);
        messageDiv.appendChild(sender === 'bot' ? contentDiv : avatarDiv);

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        return messageDiv;
    }

    function addLoadingMessage() {
        const id = 'loading-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.id = id;
        messageDiv.className = 'message bot-message';

        messageDiv.innerHTML = `
            <div class="avatar-bot">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M12 22V12"/><path d="M12 12a5 5 0 0 0 5-5H7a5 5 0 0 0 5 5z"/><path d="M8 22H5a2 2 0 0 1-2-2v-4a5 5 0 0 1 5-5h8a5 5 0 0 1 5 5v4a2 2 0 0 1-2 2h-3"/></svg>
            </div>
            <div class="message-content">
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;

        chatMessages.appendChild(messageDiv);
        scrollToBottom();
        return id;
    }

    function removeMessage(id) {
        const element = document.getElementById(id);
        if (element) element.remove();
    }

    function handleResponse(data) {
        // Expected format based on create_response_json in utils.py
        // { text: "...", data: [...], status: true/false, ... }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        const avatarDiv = document.createElement('div');
        avatarDiv.className = 'avatar-bot';
        avatarDiv.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a2 2 0 0 1 2 2v2a2 2 0 0 1-2 2 2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><path d="M12 22V12"/><path d="M12 12a5 5 0 0 0 5-5H7a5 5 0 0 0 5 5z"/><path d="M8 22H5a2 2 0 0 1-2-2v-4a5 5 0 0 1 5-5h8a5 5 0 0 1 5 5v4a2 2 0 0 1-2 2h-3"/></svg>`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        // 1. Main Text
        let html = `<p>${formatText(data.text || data.message || "Here is the information you requested.")}</p>`;

        // 2. Data Visualization (Card/Table/List)
        if (data.data) {
            if (Array.isArray(data.data) && data.data.length > 0) {
                // Check if it looks like a card-able item (has image, name, etc.)
                const sample = data.data[0];
                if (sample.image && sample.name) {
                    html += renderCards(data.data);
                } else {
                    html += renderTable(data.data);
                }
            } else if (typeof data.data === 'object') {
                html += renderObject(data.data);
            }
        }

        contentDiv.innerHTML = html;

        messageDiv.appendChild(avatarDiv);
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();
    }

    function formatText(text) {
        // Simple markdown-like formatting
        return text.replace(/\n/g, '<br>');
    }

    function renderCards(items) {
        if (!items || items.length === 0) return '';

        let html = '<div class="cards-container">';

        items.forEach(item => {
            const image = item.image || 'https://via.placeholder.com/300x200?text=No+Image';
            const name = item.name || 'Unknown';
            const price = item.price_per_night ? `$${item.price_per_night}/night` : '';
            const rating = item.rating ? `⭐ ${item.rating}` : '';
            const location = item.location ? `📍 ${item.location}` : '';

            html += `
            <div class="card">
                <div class="card-image" style="background-image: url('${image}')"></div>
                <div class="card-content">
                    <div class="card-header">
                        <h3 class="card-title">${name}</h3>
                        <span class="card-rating">${rating}</span>
                    </div>
                    <p class="card-location">${location}</p>
                    <p class="card-price">${price}</p>
                    
                    ${item.amenities ? renderTags(item.amenities) : ''}
                </div>
            </div>`;
        });

        html += '</div>';
        return html;
    }

    function renderTags(tags) {
        if (!Array.isArray(tags)) return '';
        return `<div class="card-tags">
            ${tags.slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('')}
            ${tags.length > 3 ? `<span class="tag">+${tags.length - 3}</span>` : ''}
        </div>`;
    }

    function renderTable(items) {
        if (!items || items.length === 0) return '';

        // Collect all keys
        const headers = Array.from(new Set(items.flatMap(Object.keys)));

        let html = '<div style="overflow-x:auto;"><table class="json-table"><thead><tr>';
        headers.forEach(h => html += `<th>${capitalize(h)}</th>`);
        html += '</tr></thead><tbody>';

        items.forEach(item => {
            html += '<tr>';
            headers.forEach(h => {
                let val = item[h];
                if (typeof val === 'object') val = JSON.stringify(val);
                html += `<td>${val !== undefined ? val : ''}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        return html;
    }

    function renderObject(obj) {
        // Render single object as key-value list
        let html = '<table class="json-table"><tbody>';
        for (const [key, value] of Object.entries(obj)) {
            let val = value;
            if (typeof val === 'object') val = JSON.stringify(val);
            html += `<tr><td class="json-key">${capitalize(key)}</td><td class="json-value">${val}</td></tr>`;
        }
        html += '</tbody></table>';
        return html;
    }

    function capitalize(str) {
        return str.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    // Expose for chips
    window.sendQuickMessage = (text) => {
        inputField.value = text;
        sendMessage();
    };
});
