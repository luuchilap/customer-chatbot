class ChatBot {
    constructor() {
        this.apiUrl = 'http://localhost:8000';
        this.sessionId = this.generateSessionId();
        this.customerName = 'Guest';
        
        this.initializeElements();
        this.bindEvents();
        this.showNameModal();
        this.checkServerStatus();
    }

    generateSessionId() {
        return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    initializeElements() {
        this.messagesContainer = document.getElementById('messagesContainer');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusDot = this.statusIndicator.querySelector('.status-dot');
        this.statusText = this.statusIndicator.querySelector('.status-text');
        this.customerNameDisplay = document.getElementById('customerName');
        this.charCount = document.getElementById('charCount');
        this.nameModal = document.getElementById('nameModal');
        this.nameInput = document.getElementById('nameInput');
        this.saveNameBtn = document.getElementById('saveNameBtn');
        this.skipNameBtn = document.getElementById('skipNameBtn');
        this.thinkingIndicator = document.getElementById('thinkingIndicator');
    }

    bindEvents() {
        // Message input events
        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
            this.toggleSendButton();
        });

        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Button events
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.resetBtn.addEventListener('click', () => this.resetConversation());

        // Name modal events
        this.saveNameBtn.addEventListener('click', () => this.saveName());
        this.skipNameBtn.addEventListener('click', () => this.skipName());
        this.nameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.saveName();
            }
        });

        // Prevent modal close on background click
        this.nameModal.addEventListener('click', (e) => {
            if (e.target === this.nameModal) {
                e.preventDefault();
            }
        });
    }

    updateCharCount() {
        const length = this.messageInput.value.length;
        this.charCount.textContent = length;
        
        if (length > 450) {
            this.charCount.style.color = '#e53e3e';
        } else if (length > 400) {
            this.charCount.style.color = '#dd6b20';
        } else {
            this.charCount.style.color = '#718096';
        }
    }

    toggleSendButton() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText;
    }

    showNameModal() {
        this.nameModal.style.display = 'flex';
        setTimeout(() => this.nameInput.focus(), 100);
    }

    saveName() {
        const name = this.nameInput.value.trim();
        if (name && name.length > 0) {
            this.customerName = name;
            this.customerNameDisplay.textContent = name;
        }
        this.hideNameModal();
    }

    skipName() {
        this.hideNameModal();
    }

    hideNameModal() {
        this.nameModal.style.display = 'none';
        setTimeout(() => this.messageInput.focus(), 100);
    }

    updateStatus(status, text) {
        this.statusDot.className = `status-dot ${status}`;
        this.statusText.textContent = text;
    }

    async checkServerStatus() {
        try {
            this.updateStatus('connecting', 'Connecting...');
            const response = await fetch(`${this.apiUrl}/health`);
            
            if (response.ok) {
                const data = await response.json();
                this.updateStatus('', 'Connected');
                console.log('Server status:', data);
            } else {
                throw new Error('Server responded with error');
            }
        } catch (error) {
            console.error('Server connection failed:', error);
            this.updateStatus('error', 'Connection failed');
            this.showError('Unable to connect to server. Please check if the server is running.');
        }
    }

    showLoading() {
        // Show subtle thinking indicator
        this.thinkingIndicator.classList.add('show');
        this.sendBtn.disabled = true;
        this.messageInput.disabled = true;
    }

    hideLoading() {
        // Hide thinking indicator
        this.thinkingIndicator.classList.remove('show');
        this.sendBtn.disabled = false;
        this.messageInput.disabled = false;
        this.toggleSendButton();
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message) return;

        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        this.messageInput.value = '';
        this.updateCharCount();
        this.toggleSendButton();

        // Show loading indicator
        this.showLoading();

        try {
            const response = await fetch(`${this.apiUrl}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    customer_name: this.customerName,
                    session_id: this.sessionId
                })
            });

            this.hideLoading(); // Hide loading before adding bot message

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }

            // Add bot response to chat
            this.addMessage(data.response, 'bot');
            
        } catch (error) {
            console.error('Chat error:', error);
            this.hideLoading();
            this.addMessage(
                "I'm sorry, I encountered an error processing your request. Please try again.", 
                'bot',
                true
            );
        } finally {
            this.messageInput.focus();
        }
    }

    addMessage(content, sender, isError = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;

        if (sender === 'bot') {
            const avatar = document.createElement('div');
            avatar.className = 'bot-avatar';
            avatar.textContent = isError ? '⚠️' : '🤖';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            if (isError) {
                contentDiv.classList.add('error-message');
            }
            
            contentDiv.innerHTML = this.formatMessage(content);

            messageDiv.appendChild(avatar);
            messageDiv.appendChild(contentDiv);
        } else {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;

            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.textContent = this.customerName.charAt(0).toUpperCase();

            messageDiv.appendChild(contentDiv);
            messageDiv.appendChild(avatar);
        }

        const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMessage && sender === 'user') {
            welcomeMessage.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => welcomeMessage.remove(), 300);
        }

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();

        // Check if the new message contains a chart and attach events
        const chartContainer = messageDiv.querySelector('.vertical-chart-container');
        if (chartContainer) {
            this.attachChartEvents(chartContainer);
        }
    }

    formatMessage(message) {
        let potentialJson = message.trim();
        if (potentialJson.startsWith('```json')) {
            potentialJson = potentialJson.substring(7, potentialJson.length - 3).trim();
        } else if (potentialJson.startsWith('```')) {
            potentialJson = potentialJson.substring(3, potentialJson.length - 3).trim();
        }

        try {
            const chartData = JSON.parse(potentialJson);
            if (chartData.type === 'bar_chart') {
                return this.renderBarChart(chartData);
            }
        } catch (e) {
            // Not a JSON, so format as markdown
        }

        let formatted = message;
    
        const tableRegex = /^\|(.+)\r?\n\|( *[-:]+[-| :]*)\r?\n((?:\|.*(?:\r?\n|$))*)/gm;
        formatted = formatted.replace(tableRegex, (match, headerContent, separator, bodyRows) => {
            const headers = headerContent.split('|').map(h => h.trim()).filter(Boolean);
            if (headers.length === 0) return match;

            let table = '<table class="chat-table">';
            
            table += '<thead><tr>';
            headers.forEach(header => table += `<th>${header}</th>`);
            table += '</tr></thead>';
            
            table += '<tbody>';
            const rows = bodyRows.trim().split('\n').filter(r => r.trim());
            rows.forEach(row => {
                table += '<tr>';
                const cells = row.split('|').slice(1, -1).map(c => c.trim());
                if (cells.length === headers.length) {
                    cells.forEach(cell => table += `<td>${cell}</td>`);
                }
            });
            table += '</tbody></table>';
            
            return table;
        });
    
        const imageRegex = /!\[(.*?)\]\((.*?)\)/g;
        formatted = formatted.replace(imageRegex, '<img src="$2" alt="$1" class="chat-image">');
        
        return formatted
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    renderBarChart(chartData) {
        const labels = chartData.data.labels;
        const data = chartData.data.datasets[0].data;
    
        if (data.length === 0) {
            return `<p>I couldn't find any prices for the requested items.</p>`;
        }
    
        const maxValue = Math.max(...data);
        const topValue = Math.ceil(maxValue / 10) * 10;
        const numGridLines = 5;
        const colors = ['#f59e0b', '#3b82f6', '#ef4444', '#f97316', '#8b5cf6'];
    
        let yAxisHtml = '<div class="chart-y-axis">';
        for (let i = numGridLines; i >= 0; i--) {
            const value = Math.round((topValue / numGridLines) * i);
            yAxisHtml += `<span>$${value}</span>`;
        }
        yAxisHtml += '</div>';
    
        let barsHtml = `<div class="chart-grid" style="--num-items: ${labels.length}">`;
        for (let i = 0; i < numGridLines; i++) {
            barsHtml += '<div class="chart-grid-line"></div>';
        }
        labels.forEach((label, index) => {
            const value = data[index];
            const heightPercentage = topValue > 0 ? (value / topValue) * 100 : 0;
            const color = colors[index % colors.length];
            barsHtml += `
                <div class="chart-bar-wrapper">
                    <div class="chart-tooltip">${label}: $${value}</div>
                    <div class="chart-bar" style="height: ${heightPercentage}%; background-color: ${color};"></div>
                </div>
            `;
        });
        barsHtml += '</div>';
    
        let xAxisHtml = `<div class="chart-x-axis" style="--num-items: ${labels.length}">`;
        labels.forEach(label => {
            xAxisHtml += `<span>${label}</span>`;
        });
        xAxisHtml += '</div>';
    
        let notFoundHtml = '';
        if (chartData.not_found && chartData.not_found.length > 0) {
            notFoundHtml = `<p class="not-found-message">Could not find prices for: ${chartData.not_found.join(', ')}</p>`;
        }
    
        return `
            <div class="vertical-chart-container">
                <div class="chart-body">
                    ${yAxisHtml}
                    <div class="chart-main">
                        ${barsHtml}
                        ${xAxisHtml}
                    </div>
                </div>
                ${notFoundHtml}
            </div>
        `;
    }

    attachChartEvents(chartContainer) {
        const wrappers = chartContainer.querySelectorAll('.chart-bar-wrapper');
        wrappers.forEach(wrapper => {
            const tooltip = wrapper.querySelector('.chart-tooltip');
            wrapper.addEventListener('mousemove', (e) => {
                tooltip.style.left = `${e.pageX + 15}px`;
                tooltip.style.top = `${e.pageY + 15}px`;
            });
            wrapper.addEventListener('mouseenter', () => {
                tooltip.classList.add('visible');
            });
            wrapper.addEventListener('mouseleave', () => {
                tooltip.classList.remove('visible');
            });
        });
    }

    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }

    async resetConversation() {
        if (!confirm('Are you sure you want to reset the conversation?')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiUrl}/chat/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });

            if (response.ok) {
                const messages = this.messagesContainer.querySelectorAll('.message');
                messages.forEach(msg => {
                    if (!msg.classList.contains('welcome-message')) {
                        msg.remove();
                    }
                });

                const welcomeMessage = this.messagesContainer.querySelector('.welcome-message');
                if (!welcomeMessage) {
                    location.reload();
                } else {
                    welcomeMessage.style.display = 'flex';
                }

                this.addMessage("Conversation reset! How can I help you?", 'bot');
            } else {
                throw new Error('Failed to reset conversation');
            }
        } catch (error) {
            console.error('Reset error:', error);
            this.showError('Failed to reset conversation. Please try again.');
        }
    }

    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        this.messagesContainer.insertBefore(errorDiv, this.messagesContainer.firstChild);
        
        setTimeout(() => {
            errorDiv.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => errorDiv.remove(), 300);
        }, 5000);
    }
}

const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-10px); }
    }
    
    code {
        background: #f1f5f9;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
        font-size: 0.9em;
    }
`;
document.head.appendChild(style);

document.addEventListener('DOMContentLoaded', () => {
    window.chatBot = new ChatBot();
});

document.addEventListener('visibilitychange', () => {
    if (!document.hidden && window.chatBot) {
        window.chatBot.checkServerStatus();
    }
});