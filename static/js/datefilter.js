// Date Filter Helper for AIBI Dashboard

class DateFilter {
    static getPresetRange(preset) {
        const now = new Date();
        const end = now;
        let start;

        switch(parseInt(preset)) {
            case 24:
                start = new Date(now - 24 * 60 * 60 * 1000);
                break;
            case 48:
                start = new Date(now - 48 * 60 * 60 * 1000);
                break;
            case 168:
                start = new Date(now - 7 * 24 * 60 * 60 * 1000);
                break;
            case 720:
                start = new Date(now - 30 * 24 * 60 * 60 * 1000);
                break;
            default:
                start = new Date(now - 24 * 60 * 60 * 1000);
        }

        return { start, end };
    }

    static formatISO(date) {
        return date.toISOString();
    }

    static parseISO(isoString) {
        return new Date(isoString);
    }

    static formatDisplay(date) {
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}
