// Smart Swap Platform Interactive JS

document.addEventListener('DOMContentLoaded', function () {
    // Ensure all raw POST forms include the CSRF token
    const csrfMetaTag = document.querySelector('meta[name="csrf-token"]');
    if (csrfMetaTag) {
        const csrfTokenVal = csrfMetaTag.getAttribute('content');
        document.querySelectorAll('form').forEach(form => {
            if ((form.method || '').toUpperCase() === 'POST' && !form.querySelector('input[name="csrf_token"]')) {
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'csrf_token';
                hiddenInput.value = csrfTokenVal;
                form.appendChild(hiddenInput);
            }
        });
    }

    // Theme toggle handling
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    const themeIcon = document.getElementById('theme-icon');
    const savedTheme = localStorage.getItem('smartswap_theme') || 'light';
    
    document.documentElement.setAttribute('data-bs-theme', savedTheme);
    updateThemeIcon(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-bs-theme', newTheme);
            localStorage.setItem('smartswap_theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }

    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill fs-6 text-warning';
        } else {
            themeIcon.className = 'bi bi-moon-stars fs-6';
        }
    }

    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alert alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });

    // Unread count polling for logged in users
    const unreadMsgBadge = document.getElementById('navbar-unread-messages');
    const unreadNotifBadge = document.getElementById('navbar-unread-notifications');

    function updateUnreadCounts() {
        if (!unreadMsgBadge && !unreadNotifBadge) return;

        fetch('/api/unread-count')
            .then(res => res.json())
            .then(data => {
                if (unreadMsgBadge) {
                    if (data.unread_messages > 0) {
                        unreadMsgBadge.textContent = data.unread_messages;
                        unreadMsgBadge.classList.remove('d-none');
                    } else {
                        unreadMsgBadge.classList.add('d-none');
                    }
                }
                if (unreadNotifBadge) {
                    if (data.unread_notifications > 0) {
                        unreadNotifBadge.textContent = data.unread_notifications;
                        unreadNotifBadge.classList.remove('d-none');
                    } else {
                        unreadNotifBadge.classList.add('d-none');
                    }
                }
            })
            .catch(err => {
                // Silently ignore network hiccup during polling
            });
    }

    if (unreadMsgBadge || unreadNotifBadge) {
        // Poll every 12 seconds
        setInterval(updateUnreadCounts, 12000);
    }

    // Chat functionality (if on chat page)
    const chatContainer = document.getElementById('chat-messages-scroll');
    const chatForm = document.getElementById('ajax-chat-form');
    const chatInput = document.getElementById('chat-input');
    const partnerIdInput = document.getElementById('active-partner-id');

    if (chatContainer) {
        // Scroll to bottom of chat
        chatContainer.scrollTop = chatContainer.scrollHeight;

        let lastMessageId = parseInt(chatContainer.dataset.lastMessageId || '0');
        const partnerId = partnerIdInput ? partnerIdInput.value : null;

        if (partnerId) {
            // Function to fetch new messages
            function pollNewMessages() {
                fetch(`/api/messages/${partnerId}?since_id=${lastMessageId}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.success && data.messages.length > 0) {
                            data.messages.forEach(msg => {
                                appendMessage(msg);
                                if (msg.id > lastMessageId) {
                                    lastMessageId = msg.id;
                                }
                            });
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    })
                    .catch(e => console.error(e));
            }

            // Poll every 3 seconds for active chat
            const chatInterval = setInterval(pollNewMessages, 3000);

            // Handle AJAX sending of messages
            if (chatForm && chatInput) {
                chatForm.addEventListener('submit', function (e) {
                    e.preventDefault();
                    const content = chatInput.value.trim();
                    if (!content) return;

                    chatInput.disabled = true;

                    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
                    const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

                    fetch(`/api/messages/${partnerId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ content: content })
                    })
                    .then(res => res.json())
                    .then(data => {
                        chatInput.disabled = false;
                        if (data.success && data.message) {
                            appendMessage(data.message);
                            if (data.message.id > lastMessageId) {
                                lastMessageId = data.message.id;
                            }
                            chatInput.value = '';
                            chatInput.focus();
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    })
                    .catch(err => {
                        chatInput.disabled = false;
                        console.error('Failed to send message:', err);
                    });
                });
            }
        }
    }

    function appendMessage(msg) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${msg.is_mine ? 'mine' : 'theirs'}`;
        bubble.innerHTML = `
            <div>${escapeHtml(msg.content)}</div>
            <div class="chat-time">${escapeHtml(msg.created_at)}</div>
        `;
        chatContainer.appendChild(bubble);
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});

// Quick demo login fill helper
function fillLogin(username, password) {
    const userInput = document.getElementById('username_or_email');
    const passInput = document.getElementById('password');
    if (userInput && passInput) {
        userInput.value = username;
        passInput.value = password;
    }
}
