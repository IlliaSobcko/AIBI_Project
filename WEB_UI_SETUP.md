# AIBI Web UI - Quick Setup Guide

## Installation

### 1. Install Dependencies

All required packages are already in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Update `.env` with web UI settings:

```bash
# Flask security
FLASK_SECRET_KEY=generate_random_32_char_string

# Scheduler (disabled by default for manual mode)
AUTO_SCHEDULER=false

# Dashboard defaults
DEFAULT_DATE_HOURS=24

# Cache settings
ANALYSIS_CACHE_TTL_HOURS=1
```

Generate secure secret key:
```python
import secrets
print(secrets.token_hex(32))
```

### 3. Start Server

```bash
python main.py
```

Server will start on `http://0.0.0.0:8080`

## First Time Use

### Step 1: Authenticate

1. Visit: `http://localhost:8080/auth`
2. Enter phone number with country code (e.g., `+1234567890`)
3. Check Telegram for verification code
4. Enter code to complete authentication
5. Session file created automatically

### Step 2: View Chats

1. Visit: `http://localhost:8080/`
2. Select date range (default: last 24 hours)
3. Click "Apply Filter"
4. See list of chats with message counts

### Step 3: Analyze Chats

1. Click "Analyze" button on desired chat
2. Analysis runs on-demand
3. View results in real-time
4. Results cached for 1 hour

### Step 4: Manage Settings

1. Visit: `http://localhost:8080/settings`
2. Toggle scheduler on/off (optional)
3. Change default date range
4. View authentication status

## API Quick Start

### Get Chat List (cost-free)

```bash
curl "http://localhost:8080/api/chats?hours=24"
```

### Analyze Single Chat

```bash
curl -X POST http://localhost:8080/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": 12345,
    "start_date": "2026-01-31T00:00:00Z",
    "end_date": "2026-02-01T23:59:59Z"
  }'
```

### Check Auth Status

```bash
curl http://localhost:8080/api/auth/status
```

### Toggle Scheduler

```bash
curl -X POST http://localhost:8080/api/scheduler/toggle \
  -H "Content-Type: application/json" \
  -d '{"enabled": true}'
```

## File Structure

```
web/                  → Flask blueprints & logic
├── __init__.py       → Blueprint registration
├── routes.py         → All endpoints
├── session_manager.py → Preferences & cache
└── telegram_auth.py  → Web authentication

templates/            → HTML templates
├── base.html         → Layout
├── dashboard.html    → Main UI
├── auth.html         → Auth form
└── settings.html     → Settings page

static/               → Frontend assets
├── css/main.css      → Styling
└── js/
    ├── api.js        → API client
    ├── app.js        → Dashboard logic
    └── datefilter.js → Date utilities

analysis_cache/       → Cache files (auto-created)
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8080
netstat -ano | findstr :8080

# Kill it
taskkill /PID <PID> /F
```

### Template Not Found

Ensure `templates/` and `static/` directories exist in project root

### JavaScript Errors

Check browser console: F12 → Console tab

### API Errors

Check server logs: Console output from `python main.py`

## Production Deployment

### HTTPS Support

1. Generate SSL certificate
2. Update Flask config:
   ```python
   app.run(ssl_context=('cert.pem', 'key.pem'))
   ```

### Environment Variables

Set in production environment:

```bash
export FLASK_SECRET_KEY=secure_random_32_chars
export AUTO_SCHEDULER=false
export TG_API_ID=your_api_id
export TG_API_HASH=your_api_hash
export AI_API_KEY=your_ai_key
```

### Rate Limiting (Optional)

Add Flask-Limiter for production:

```bash
pip install Flask-Limiter
```

### Database (Optional)

For multi-user support, replace file-based cache with:
- SQLite (simple)
- PostgreSQL (scalable)
- Redis (fast)

## Monitoring

### Check Scheduler Status

```bash
curl http://localhost:8080/api/scheduler/status
```

### View Cache Size

```bash
du -sh analysis_cache/
```

### Clear Cache

Delete cache files:
```bash
rm analysis_cache/*.json
```

## Performance Tips

1. **Cache Management:** Adjust `ANALYSIS_CACHE_TTL_HOURS` based on usage
2. **Date Range:** Smaller ranges = faster analysis
3. **Scheduler:** Keep disabled unless auto-analysis needed
4. **Concurrency:** Use gunicorn for production:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 main:app
   ```

## FAQ

**Q: Does my session get saved?**
A: Yes, automatically in `aibi_session.session` file

**Q: Can I use old credentials?**
A: Yes, existing session works with web UI

**Q: What happens if I close the browser?**
A: Session persists - your preferences are saved

**Q: Can multiple users access simultaneously?**
A: Yes, with proper deployment (see Production Deployment)

**Q: How do I disable auto-scheduler?**
A: Set `AUTO_SCHEDULER=false` in `.env` (default)

**Q: What if cache gets corrupted?**
A: Delete `analysis_cache/` - it auto-recreates

## Support

For issues:
1. Check `.env` configuration
2. Review browser console (F12)
3. Check server console output
4. Verify Telegram API credentials
5. Ensure network connectivity

---

**Ready to use! Start with: `python main.py`**
