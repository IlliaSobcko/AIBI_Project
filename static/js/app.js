// AIBI Dashboard Application

class Dashboard {
    constructor() {
        this.chats = [];
        this.filters = { datePreset: '24' };
    }

    init() { console.log('[APP] Initialized'); }

    async loadChats() {
        const loading = document.getElementById('loading');
        loading.style.display = 'flex';
        try {
            const response = await api.getChats(24);
            this.chats = response.chats || [];
            console.log('[APP] Loaded ' + this.chats.length + ' chats');
            this.renderChats();
        } catch (error) {
            console.error('[APP] Error:', error);
        } finally {
            loading.style.display = 'none';
        }
    }

    renderChats() {
        const chatList = document.getElementById('chat-list');
        chatList.innerHTML = '';
        if (this.chats.length === 0) {
            chatList.innerHTML = '<p class="empty-state">No chats</p>';
            return;
        }
        this.chats.forEach(chat => {
            const div = document.createElement('div');
            div.className = 'chat-item';
            const status = chat.analyzed ? 'Replied' : 'Pending';
            div.innerHTML = '<div class="chat-header"><div class="chat-title">' + chat.chat_title + '</div><span class="badge">' + status + '</span></div>' +
                '<div class="chat-meta"><div><strong>Messages:</strong> ' + chat.message_count + '</div></div>' +
                '<div class="chat-actions">' +
                '<button class="btn btn-primary btn-small" onclick="app.analyzeChat(' + chat.chat_id + ')">Analyze</button>' +
                '<button class="btn btn-success btn-small" onclick="app.sendReply(' + chat.chat_id + ')">Send Reply</button>' +
                '<button class="btn btn-secondary btn-small" onclick="app.downloadAnalytics()">Download</button>' +
                '</div>';
            chatList.appendChild(div);
        });
    }

    async analyzeChat(chatId) {
        const loading = document.getElementById('loading');
        loading.style.display = 'flex';
        try {
            const range = DateFilter.getPresetRange(this.filters.datePreset);
            const result = await api.analyzeChat(chatId, DateFilter.formatISO(range.start), DateFilter.formatISO(range.end));
            const panel = document.getElementById('analysis-panel');
            if (panel) {
                document.getElementById('analysis-title').textContent = 'Analysis';
                document.getElementById('analysis-confidence').innerHTML = '<strong>Confidence:</strong> ' + result.confidence + '%';
                document.getElementById('analysis-content').textContent = result.report || 'No report';
                panel.style.display = 'block';
            }
            const chat = this.chats.find(c => c.chat_id === chatId);
            if (chat) { chat.analyzed = true; this.renderChats(); }
        } catch (error) {
            alert('Analysis failed: ' + error.message);
        } finally {
            loading.style.display = 'none';
        }
    }

    async sendReply(chatId) {
        const replyText = prompt('Enter reply:');
        if (!replyText) return;
        try {
            await api.sendReply(chatId, replyText);
            alert('Reply sent via Telegram!');
            this.loadChats();
        } catch (error) {
            alert('Failed: ' + error.message);
        }
    }

    async downloadAnalytics() {
        try {
            const response = await api.downloadAnalytics();
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'analytics.xlsx';
            a.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            alert('Download failed: ' + error.message);
        }
    }

    async loadKnowledgeBase(type) {
        try {
            const result = await api.getKnowledgeBase(type);
            document.getElementById('kb-content').value = result.content || '';
        } catch (error) {
            alert('Load failed: ' + error.message);
        }
    }

    async saveKnowledgeBase() {
        const type = document.getElementById('kb-file-type').value;
        const content = document.getElementById('kb-content').value;
        if (content.trim().length < 10) {
            alert('Content too short');
            return;
        }
        try {
            await api.updateKnowledgeBase(type, content);
            alert('Saved!');
        } catch (error) {
            alert('Save failed: ' + error.message);
        }
    }

    applyPreset() { this.loadChats(); }
    closeAnalysis() { const p = document.getElementById('analysis-panel'); if (p) p.style.display = 'none'; }
}

const app = new Dashboard();
window.addEventListener('DOMContentLoaded', function() {
    app.init();
    app.loadChats();
});
