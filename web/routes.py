"""Flask routes and API endpoints for AIBI Web UI"""

import asyncio
import os
import threading
from datetime import datetime, timedelta, timezone
from flask import request, jsonify, render_template
from . import web_bp, api_bp

# --- THREAD-SAFE ASYNC WRAPPER ---
_async_lock = threading.Lock()
_event_loop = None

def get_event_loop():
    """Get or create a single event loop for async operations"""
    global _event_loop
    if _event_loop is None or _event_loop.is_closed():
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
    return _event_loop

def run_async(coroutine):
    """Run async function in thread-safe manner"""
    with _async_lock:
        loop = get_event_loop()
        return loop.run_until_complete(coroutine)


def get_date_range_from_request():
    """Parse date range from request parameters or use defaults"""
    # Get parameters from request
    start_param = request.args.get('start_date')
    end_param = request.args.get('end_date')
    hours_param = request.args.get('hours', 24)

    try:
        hours = int(hours_param)
    except (ValueError, TypeError):
        hours = 24

    if start_param and end_param:
        try:
            start_date = datetime.fromisoformat(start_param.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_param.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            # Invalid format - use defaults
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(hours=hours)
    else:
        # Use default: last N hours
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours)

    return start_date, end_date


# --- WEB ROUTES ---

@web_bp.route('/')
def index():
    """Home page with status and links"""
    return render_template('dashboard.html')


@web_bp.route('/auth')
def auth_page():
    """Telegram authentication page"""
    return render_template('auth.html')


@web_bp.route('/settings')
def settings_page():
    """User settings and preferences"""
    return render_template('settings.html')


# --- API ENDPOINTS ---

@api_bp.route('/chats', methods=['GET'])
def api_get_chats():
    """
    GET /api/chats?start_date=<iso8601>&end_date=<iso8601>&hours=24

    Fetch list of chats with message counts (NO AI ANALYSIS)

    Returns:
        {
            "chats": [
                {
                    "chat_id": 12345,
                    "chat_title": "Chat Name",
                    "chat_type": "user|group",
                    "message_count": 5,
                    "last_message_date": "2026-01-31T15:30:00",
                    "has_unread": false,
                    "analyzed": false
                },
                ...
            ],
            "total_chats": 3
        }
    """
    try:
        from main import fetch_chats_only

        start_date, end_date = get_date_range_from_request()

        # Run async function with thread-safe wrapper
        chats = run_async(fetch_chats_only(limit=50))

        # Convert ChatInfo objects to dictionaries for JSON response
        chat_dicts = [
            {
                "chat_id": int(chat.chat_id),  # Ensure int type
                "chat_title": str(chat.chat_title),
                "chat_type": chat.chat_type,
                "message_count": chat.message_count,
                "last_message_date": chat.last_message_date.isoformat() if chat.last_message_date else None,
                "has_unread": chat.has_unread,
                "analyzed": chat.analyzed
            }
            for chat in chats
        ]

        return jsonify({
            "chats": chat_dicts,
            "total_chats": len(chat_dicts),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/analyze', methods=['POST'])
def api_analyze_chat():
    """
    POST /api/analyze
    Body: {
        "chat_id": 12345,
        "start_date": "2026-01-31T00:00:00Z",
        "end_date": "2026-02-01T23:59:59Z",
        "force_refresh": false
    }

    Analyze a specific chat (ON-DEMAND - costs AI tokens)

    Parameters:
        chat_id: Required. Telegram chat ID to analyze
        start_date: Required. ISO 8601 format start datetime
        end_date: Required. ISO 8601 format end datetime
        force_refresh: Optional. If true, bypass cache and fetch fresh data

    Returns:
        {
            "chat_id": 12345,
            "report": "Analysis report text",
            "confidence": 85,
            "from_cache": false
        }
    """
    try:
        data = request.get_json()

        if not data or 'chat_id' not in data:
            return jsonify({"error": "Missing chat_id"}), 400

        chat_id = int(data.get('chat_id'))  # Ensure int type
        start_param = data.get('start_date')
        end_param = data.get('end_date')
        force_refresh = data.get('force_refresh', False)

        # Parse dates
        try:
            start_date = datetime.fromisoformat(start_param.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_param.replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            return jsonify({"error": "Invalid date format. Use ISO 8601 format."}), 400

        # Validate date range (max 30 days)
        if (end_date - start_date).days > 30:
            return jsonify({"error": "Date range cannot exceed 30 days"}), 400

        from main import analyze_single_chat

        # Run async function with thread-safe wrapper
        result = run_async(analyze_single_chat(chat_id, start_date, end_date, force_refresh=force_refresh))

        return jsonify({
            "chat_id": chat_id,
            "report": result.get('report', ''),
            "confidence": result.get('confidence', 0),
            "from_cache": result.get('from_cache', False),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/auth/status', methods=['GET'])
def api_auth_status():
    """
    GET /api/auth/status

    Check authentication status

    Returns:
        {
            "authenticated": true,
            "last_auth": "2026-01-31T12:00:00",
            "session_valid": true
        }
    """
    try:
        from main import SESSION_MANAGER, TELEGRAM_AUTH

        authenticated = SESSION_MANAGER.is_authenticated()
        last_auth = SESSION_MANAGER.get("last_auth")

        session_valid = False
        if TELEGRAM_AUTH and authenticated:
            session_valid = run_async(TELEGRAM_AUTH.is_session_valid())

        return jsonify({
            "authenticated": authenticated,
            "last_auth": last_auth,
            "session_valid": session_valid
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/auth/phone', methods=['POST'])
def api_auth_send_code():
    """
    POST /api/auth/phone
    Body: {"phone": "+1234567890"}

    Send verification code to phone (Step 1 of auth)

    Returns:
        {
            "status": "code_sent",
            "message": "Code sent to +1234567890"
        }
    """
    try:
        data = request.get_json()

        if not data or 'phone' not in data:
            return jsonify({"error": "Missing phone number"}), 400

        phone = data.get('phone')

        from main import TELEGRAM_AUTH

        if not TELEGRAM_AUTH:
            return jsonify({"error": "Telegram auth not initialized"}), 500

        success, message = run_async(TELEGRAM_AUTH.send_code_request(phone))

        if success:
            return jsonify({
                "status": "code_sent",
                "message": message
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/auth/verify', methods=['POST'])
def api_auth_verify_code():
    """
    POST /api/auth/verify
    Body: {
        "phone": "+1234567890",
        "code": "12345"
    }

    Verify code and create session (Step 2 of auth)

    Returns:
        {
            "status": "success",
            "message": "Authenticated as John Doe (+1234567890)"
        }
    """
    try:
        data = request.get_json()

        if not data or 'phone' not in data or 'code' not in data:
            return jsonify({"error": "Missing phone or code"}), 400

        phone = data.get('phone')
        code = data.get('code')

        from main import TELEGRAM_AUTH, SESSION_MANAGER

        if not TELEGRAM_AUTH:
            return jsonify({"error": "Telegram auth not initialized"}), 500

        success, message = run_async(TELEGRAM_AUTH.verify_code(phone, code))

        if success:
            # Mark as authenticated
            SESSION_MANAGER.mark_authenticated()

            return jsonify({
                "status": "success",
                "message": message
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": message
            }), 400

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/scheduler/toggle', methods=['POST'])
def api_toggle_scheduler():
    """
    POST /api/scheduler/toggle
    Body: {"enabled": true}

    Toggle auto-scheduler on/off

    Returns:
        {
            "status": "ok",
            "enabled": true
        }
    """
    try:
        data = request.get_json()

        if not data or 'enabled' not in data:
            return jsonify({"error": "Missing 'enabled' parameter"}), 400

        enabled = data.get('enabled', False)

        from main import scheduler, SESSION_MANAGER

        if enabled and not scheduler.running:
            scheduler.start()
            print("[SCHEDULER] Auto-scheduler ENABLED via API")
        elif not enabled and scheduler.running:
            scheduler.shutdown(wait=False)
            print("[SCHEDULER] Auto-scheduler DISABLED via API")

        SESSION_MANAGER.toggle_scheduler(enabled)

        return jsonify({
            "status": "ok",
            "enabled": scheduler.running
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/scheduler/status', methods=['GET'])
def api_scheduler_status():
    """
    GET /api/scheduler/status

    Get scheduler status

    Returns:
        {
            "enabled": true,
            "running": true
        }
    """
    try:
        from main import scheduler, SESSION_MANAGER

        return jsonify({
            "enabled": SESSION_MANAGER.is_scheduler_enabled(),
            "running": scheduler.running
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# === NEW INTEGRATION ROUTES ===

@api_bp.route('/send_reply', methods=['POST'])
def api_send_reply():
    """
    POST /api/send_reply
    Send reply via Telegram
    """
    try:
        data = request.get_json()
        if not data or 'chat_id' not in data or 'reply_text' not in data:
            return jsonify({"error": "Missing chat_id or reply_text"}), 400

        chat_id = int(data.get('chat_id'))
        reply_text = data.get('reply_text', '')

        if not reply_text.strip():
            return jsonify({"error": "Reply text cannot be empty"}), 400

        # Send via Telegram
        async def send_msg():
            from main import collector
            if collector and collector.client:
                await collector.client.send_message(chat_id, reply_text)
                return {"success": True}
            raise Exception("Telegram client unavailable")

        result = run_async(send_msg())
        print(f"[WEB] Reply sent to chat {chat_id}")
        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/analytics_download', methods=['GET'])
def api_analytics_download():
    """
    GET /api/analytics_download
    Download analytics Excel file
    """
    try:
        from features.analytics_engine import run_unified_analytics
        from flask import send_file
        import os

        result = run_async(run_unified_analytics(
            reports_folder='reports',
            output_file='unified_analytics.xlsx'
        ))

        if not result.get('success'):
            return jsonify({"error": "Analytics failed"}), 500

        file_path = result.get('file_path')
        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 500

        print(f"[WEB] Downloading: {file_path}")
        return send_file(
            file_path,
            as_attachment=True,
            download_name='unified_analytics.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@api_bp.route('/knowledge_base', methods=['GET', 'POST'])
def api_knowledge_base():
    """
    GET/POST /api/knowledge_base
    Manage knowledge base files
    """
    try:
        from pathlib import Path

        if request.method == 'GET':
            file_type = request.args.get('type', 'prices')
            file_path = Path('business_data.txt') if file_type == 'prices' else Path('instructions.txt')

            if not file_path.exists():
                return jsonify({"content": ""}), 200

            content = file_path.read_text(encoding='utf-8')
            print(f"[WEB] Retrieved {file_type}")
            return jsonify({"type": file_type, "content": content}), 200

        else:  # POST
            data = request.get_json()
            if not data or 'type' not in data or 'content' not in data:
                return jsonify({"error": "Missing type or content"}), 400

            file_type = data.get('type')
            content = data.get('content', '')

            file_path = Path('business_data.txt') if file_type == 'prices' else Path('instructions.txt')

            if len(content.strip()) < 10:
                return jsonify({"error": "Content too short"}), 400

            file_path.write_text(content, encoding='utf-8')
            print(f"[WEB] Updated {file_type}")
            return jsonify({"success": True}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
