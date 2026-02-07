// API Client for AIBI Web UI

class APIClient {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }

    async request(method, endpoint, body = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (body) {
                options.body = JSON.stringify(body);
            }

            const response = await fetch(`${this.baseURL}${endpoint}`, options);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error(`API Error [${method} ${endpoint}]:`, error);
            throw error;
        }
    }

    // Chat operations
    async getChats(hours = 24, startDate = null, endDate = null) {
        let url = '/chats?hours=' + hours;
        if (startDate) url += '&start_date=' + startDate;
        if (endDate) url += '&end_date=' + endDate;
        return this.request('GET', url);
    }

    async analyzeChat(chatId, startDate, endDate, forceRefresh = false) {
        return this.request('POST', '/analyze', {
            chat_id: chatId,
            start_date: startDate,
            end_date: endDate,
            force_refresh: forceRefresh
        });
    }

    // New integration endpoints
    async sendReply(chatId, replyText) {
        return this.request('POST', '/send_reply', {
            chat_id: chatId,
            reply_text: replyText
        });
    }

    async getAnalyticsReport() {
        return this.request('GET', '/analytics_report');
    }

    async downloadAnalytics() {
        const response = await fetch(`${this.baseURL}/analytics_download`);
        if (!response.ok) throw new Error('Failed to download analytics');
        return response;
    }

    async getKnowledgeBase(fileType) {
        // fileType: 'prices' or 'instructions'
        return this.request('GET', `/knowledge_base?type=${fileType}`);
    }

    async updateKnowledgeBase(fileType, content) {
        return this.request('POST', '/knowledge_base', {
            type: fileType,
            content: content
        });
    }

    // Auth endpoints
    async getAuthStatus() {
        return this.request('GET', '/auth/status');
    }
}

// Global API client instance
const api = new APIClient();
