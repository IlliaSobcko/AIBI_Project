// AIBI Dashboard Application

class Dashboard {
    constructor() {
        this.chats = [];
        this.filters = { datePreset: '24' };
        this.currentAnalysis = null;
        this.selectedChatId = null;
    }

    init() {
        console.log('[APP] Dashboard Initialized');
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Handle custom date range toggle
        const datePreset = document.getElementById('date-preset');
        if (datePreset) {
            datePreset.addEventListener('change', (e) => {
                const customDates = document.getElementById('custom-dates');
                if (e.target.value === 'custom' && customDates) {
                    customDates.style.display = 'flex';
                    customDates.style.gap = '1rem';
                    customDates.style.alignItems = 'center';
                } else if (customDates) {
                    customDates.style.display = 'none';
                }
                this.filters.datePreset = e.target.value;
            });
        }
    }

    showLoading(show = true) {
        const loading = document.getElementById('loading');
        if (loading) {
            if (show) {
                loading.classList.add('active');
            } else {
                loading.classList.remove('active');
            }
        }
    }

    setButtonLoading(buttonId, loading = true) {
        const btn = document.getElementById(buttonId);
        if (btn) {
            btn.disabled = loading;
            const span = btn.querySelector('span');
            if (span) {
                if (loading) {
                    span.innerHTML = '<span class="spinner-small"></span> ' + span.textContent;
                } else {
                    span.innerHTML = span.textContent.replace(/.*spinner-small.*/, '').trim();
                }
            }
        }
    }

    async loadGeneralStats() {
        try {
            const stats = await api.getGeneralStats();
            document.getElementById('stat-total').textContent = stats.total_reports || 0;
            document.getElementById('stat-wins').textContent = stats.win_count || 0;
            document.getElementById('stat-losses').textContent = stats.loss_count || 0;
            document.getElementById('stat-pending').textContent = stats.unknown_count || 0;
            document.getElementById('stat-revenue').textContent = '$' + (stats.total_revenue || 0).toLocaleString('en-US', { minimumFractionDigits: 0 });
            document.getElementById('stat-confidence').textContent = (stats.average_confidence || 0) + '%';
            console.log('[APP] Stats loaded:', stats);
        } catch (error) {
            console.error('[APP] Failed to load stats:', error);
        }
    }

    async loadChats() {
        this.showLoading(true);
        this.setButtonLoading('apply-btn', true);
        this.setButtonLoading('refresh-btn', true);
        try {
            const range = DateFilter.getPresetRange(this.filters.datePreset);
            const response = await api.getChats(
                null,
                DateFilter.formatISO(range.start),
                DateFilter.formatISO(range.end)
            );
            this.chats = response.chats || [];
            console.log('[APP] Loaded ' + this.chats.length + ' chats');
            this.renderChats();
        } catch (error) {
            console.error('[APP] Error loading chats:', error);
            this.showErrorMessage('Failed to load chats: ' + error.message);
        } finally {
            this.showLoading(false);
            this.setButtonLoading('apply-btn', false);
            this.setButtonLoading('refresh-btn', false);
        }
    }

    renderChats() {
        const chatList = document.getElementById('chat-list');
        chatList.innerHTML = '';
        if (this.chats.length === 0) {
            chatList.innerHTML = '<p class="empty-state">No chats found. Try adjusting the date filter.</p>';
            return;
        }
        this.chats.forEach((chat, index) => {
            const div = document.createElement('div');
            div.className = 'chat-item';
            if (chat.chat_id === this.selectedChatId) {
                div.classList.add('active');
            }
            const status = chat.analyzed ? 'Replied' : 'Pending';
            const badgeClass = chat.analyzed ? 'badge' : 'badge pending';
            div.innerHTML =
                '<div class="chat-header">' +
                    '<div class="chat-title">' + this.escapeHtml(chat.chat_title) + '</div>' +
                    '<span class="' + badgeClass + '">' + status + '</span>' +
                '</div>' +
                '<div class="chat-meta">' +
                    '<div><strong>Messages:</strong> ' + chat.message_count + '</div>' +
                    '<div><strong>Type:</strong> ' + (chat.chat_type || 'user') + '</div>' +
                '</div>' +
                '<div class="chat-actions">' +
                    '<button class="btn btn-primary btn-small" onclick="app.analyzeChat(' + chat.chat_id + ')" title="Analyze chat">Analyze</button>' +
                    '<button class="btn btn-success btn-small" onclick="app.sendReply(' + chat.chat_id + ')" title="Send reply via Telegram">Send Reply</button>' +
                    '<button class="btn btn-secondary btn-small" onclick="app.downloadAnalytics()" title="Download analytics">Download</button>' +
                '</div>';
            div.addEventListener('click', () => this.selectChat(chat));
            chatList.appendChild(div);
        });
    }

    selectChat(chat) {
        this.selectedChatId = chat.chat_id;
        this.renderChats();
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showErrorMessage(message) {
        const panel = document.getElementById('analysis-content');
        if (panel) {
            panel.innerHTML = '<div class="analysis-empty"><p style="color: var(--danger-color);">❌ ' + this.escapeHtml(message) + '</p></div>';
        }
    }

    async analyzeChat(chatId) {
        this.showLoading(true);
        try {
            const range = DateFilter.getPresetRange(this.filters.datePreset);
            // Force refresh to get fresh data
            const result = await api.analyzeChat(
                chatId,
                DateFilter.formatISO(range.start),
                DateFilter.formatISO(range.end),
                true // force_refresh = true to bypass cache
            );

            // Store current analysis
            this.currentAnalysis = result;

            // Display analysis immediately
            this.displayAnalysis(result);

            // Update UI
            const chat = this.chats.find(c => c.chat_id === chatId);
            if (chat) {
                chat.analyzed = true;
                this.renderChats();
            }

            console.log('[APP] Analysis complete for chat', chatId);
        } catch (error) {
            console.error('[APP] Analysis error:', error);
            this.showErrorMessage('Analysis failed: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    displayAnalysis(result) {
        const panel = document.getElementById('analysis-panel');
        const contentDiv = document.getElementById('analysis-content');

        if (panel && contentDiv) {
            // Build the analysis display
            let html = '<div class="analysis-header">' +
                '<h3>Chat Analysis</h3>' +
                '</div>' +
                '<div class="analysis-meta">' +
                '<span><strong>Confidence:</strong> ' + (result.confidence || 0) + '%</span>' +
                '<span><strong>Status:</strong> ' + (result.from_cache ? 'Cached' : 'Fresh') + '</span>' +
                '</div>' +
                '<div class="analysis-content">' +
                this.escapeHtml(result.report || 'No analysis available') +
                '</div>';

            contentDiv.innerHTML = html;
        }
    }

    async sendReply(chatId) {
        const replyText = prompt('Enter reply message to send via Telegram:');
        if (!replyText || !replyText.trim()) return;

        this.showLoading(true);
        try {
            const result = await api.sendReply(chatId, replyText.trim());
            console.log('[APP] Reply sent:', result);
            this.showErrorMessage('✓ Reply sent successfully via Telegram!');
        } catch (error) {
            console.error('[APP] Send reply error:', error);
            this.showErrorMessage('Failed to send reply: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async downloadAnalytics() {
        this.showLoading(true);
        try {
            const response = await api.downloadAnalytics();
            if (!response.ok) {
                throw new Error('Download failed with status ' + response.status);
            }
            const blob = await response.blob();
            if (blob.type === 'application/json') {
                const text = await blob.text();
                throw new Error('Server returned JSON error: ' + text);
            }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'analytics_' + new Date().toISOString().split('T')[0] + '.xlsx';
            a.click();
            URL.revokeObjectURL(url);
            console.log('[APP] Analytics downloaded');
        } catch (error) {
            console.error('[APP] Download error:', error);
            this.showErrorMessage('Download failed: ' + error.message);
        } finally {
            this.showLoading(false);
        }
    }

    async loadKnowledgeBase(type) {
        try {
            const result = await api.getKnowledgeBase(type);
            document.getElementById('kb-content').value = result.content || '';
            console.log('[APP] Knowledge base loaded:', type);
        } catch (error) {
            console.error('[APP] Load KB error:', error);
            alert('Failed to load knowledge base: ' + error.message);
        }
    }

    async saveKnowledgeBase() {
        const type = document.getElementById('kb-file-type').value;
        const content = document.getElementById('kb-content').value;
        if (content.trim().length < 10) {
            alert('Content must be at least 10 characters');
            return;
        }

        this.setButtonLoading('kb-save-btn', true);
        try {
            await api.updateKnowledgeBase(type, content);
            alert('Knowledge base saved successfully!');
            this.closeKnowledgeModal();
            console.log('[APP] Knowledge base saved:', type);
        } catch (error) {
            console.error('[APP] Save KB error:', error);
            alert('Failed to save knowledge base: ' + error.message);
        } finally {
            this.setButtonLoading('kb-save-btn', false);
        }
    }

    addKnowledgeBaseButton() {
        const filterSection = document.querySelector('.filter-controls');
        if (filterSection && !document.getElementById('kb-manager-btn')) {
            const kb_btn = document.createElement('button');
            kb_btn.id = 'kb-manager-btn';
            kb_btn.className = 'btn btn-secondary';
            kb_btn.textContent = '📚 Knowledge Base';
            kb_btn.onclick = () => {
                const modal = document.getElementById('knowledge-modal');
                if (modal) {
                    modal.classList.add('active');
                    this.loadKnowledgeBase('prices');
                }
            };
            filterSection.appendChild(kb_btn);
        }
    }

    applyPreset() {
        this.filters.datePreset = document.getElementById('date-preset').value;
        this.loadChats();
    }

    closeKnowledgeModal() {
        const modal = document.getElementById('knowledge-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }
}

const app = new Dashboard();
