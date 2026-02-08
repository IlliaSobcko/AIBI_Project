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

@api_bp.route('/test_debug', methods=['GET'])
def api_test_debug():
    """Debug endpoint to verify routes are loaded"""
    return jsonify({"status": "Routes are loaded!", "route_count": 10}), 200


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
        from main import fetch_chats_only, DRAFT_BOT

        # Get date range parameters (but convert to hours for fetch_chats_only)
        start_date, end_date = get_date_range_from_request()

        # Calculate hours difference for filtering
        time_diff = end_date - start_date
        hours_ago = int(time_diff.total_seconds() / 3600)  # Convert to hours
        print(f"[API] [/api/chats] Fetching chats from last {hours_ago} hours")
        print(f"[API] [/api/chats] Date range: {start_date} to {end_date}")

        # Check bot connection status
        bot_connected = DRAFT_BOT is not None and hasattr(DRAFT_BOT, 'client') and DRAFT_BOT.client is not None

        # If bot is not connected, still try to fetch from aibi_session directly
        # FIX: Remove bot dependency - fetch directly from authenticated session
        if not bot_connected:
            print(f"[API] [/api/chats] WARNING: Bot not connected, using direct session access")
            # Continue to fetch_chats_only which uses aibi_session directly

        # FIX: Always fetch chats - don't block on bot connection
        if False:  # Disabled - always try to fetch
            return jsonify({
                "chats": [],
                "total_chats": 0,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "status": "connecting",
                "message": "Telegram bot is still connecting... Please wait 30 seconds and refresh."
            }), 200

        # FIX: Pass hours_ago parameter to fetch only chats with recent activity
        print(f"[API] [/api/chats] Calling fetch_chats_only with hours_ago={hours_ago}")
        chats = run_async(fetch_chats_only(limit=100, hours_ago=hours_ago))

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
            "end_date": end_date.isoformat(),
            "status": "connected"
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return user-friendly error instead of 500
        return jsonify({
            "chats": [],
            "total_chats": 0,
            "status": "error",
            "error": str(e),
            "message": "Failed to fetch chats. Bot may still be connecting."
        }), 200  # Return 200 so UI doesn't break


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
    DIRECT METHOD - Uses TelegramClient('aibi_session') exactly like Quick_test.py

    This is the EXACT same method that successfully sent messages in Quick_test.py.
    No bot registry, no wrappers, no complexity - just direct TelegramClient.
    """
    try:
        from telethon import TelegramClient
        import os

        data = request.get_json()
        if not data or 'chat_id' not in data or 'reply_text' not in data:
            return jsonify({"error": "Missing chat_id or reply_text"}), 400

        chat_id = int(data.get('chat_id'))
        reply_text = data.get('reply_text', '')

        if not reply_text.strip():
            return jsonify({"error": "Reply text cannot be empty"}), 400

        print(f"[WEB] [DIRECT SEND] Sending to chat {chat_id}")
        print(f"[WEB] [DIRECT SEND] Using aibi_session (same as Quick_test.py)")

        # EXACT method from Quick_test.py that worked
        async def send_direct():
            api_id = int(os.getenv("TG_API_ID"))
            api_hash = os.getenv("TG_API_HASH")

            print(f"[WEB] [DIRECT SEND] Creating TelegramClient with aibi_session")
            client = TelegramClient('aibi_session', api_id, api_hash)

            try:
                print(f"[WEB] [DIRECT SEND] Connecting to Telegram...")
                await client.connect()

                # Check authorization
                if not await client.is_user_authorized():
                    raise Exception("Session not authorized. Run manual_phone_auth.py first.")

                print(f"[WEB] [DIRECT SEND] Sending message to {chat_id}...")
                # EXACT same call that worked in Quick_test.py
                await client.send_message(chat_id, reply_text)

                print(f"[WEB] [DIRECT SEND] [SUCCESS] Message sent successfully!")
                return {"success": True, "message": f"Message sent to {chat_id}"}

            finally:
                await client.disconnect()
                print(f"[WEB] [DIRECT SEND] Disconnected")

        # Run in current event loop
        result = run_async(send_direct())
        return jsonify(result), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Send failed: {str(e)}"}), 500


@api_bp.route('/messages', methods=['GET'])
def api_get_messages():
    """
    GET /api/messages?chat_id=<optional>&limit=20

    Get messages from Telegram listener

    Returns:
        {
            "<chat_id>": [
                {
                    "message_id": 12345,
                    "sender_id": 123456789,
                    "sender_name": "John",
                    "text": "Message preview...",
                    "date": "2026-02-07T12:00:00"
                },
                ...
            ]
        }
    """
    try:
        from main import BOT_REGISTRY

        chat_id = request.args.get('chat_id')
        limit = request.args.get('limit', 20, type=int)

        if chat_id:
            try:
                chat_id = int(chat_id)
            except ValueError:
                return jsonify({"error": "Invalid chat_id"}), 400

        messages = BOT_REGISTRY.get_messages(chat_id=chat_id, limit=limit)

        return jsonify({
            "messages": messages,
            "total_chats": len(messages),
            "limit": limit
        }), 200

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


@api_bp.route('/generate_faq', methods=['POST'])
def api_generate_faq():
    """
    POST /api/generate_faq

    Generate FAQ from successful reply patterns (AI Self-Learning)

    Returns:
        {
            "success": true,
            "total_patterns": 25,
            "topics_identified": 5,
            "file_path": "/path/to/dynamic_instructions.txt",
            "message": "Knowledge base updated with 25 new successful cases!"
        }
    """
    try:
        from knowledge_base_storage import get_knowledge_base

        kb_storage = get_knowledge_base()

        # Get statistics
        stats = kb_storage.get_statistics()
        total_patterns = stats['total_patterns']

        if total_patterns == 0:
            return jsonify({
                "success": False,
                "error": "No successful patterns found yet. Approve some drafts first!"
            }), 400

        # Generate FAQ
        result = kb_storage.generate_faq("dynamic_instructions.txt")

        if result['success']:
            return jsonify({
                "success": True,
                "total_patterns": result['total_patterns'],
                "topics_identified": result['topics_identified'],
                "file_path": result['file_path'],
                "message": f"Knowledge base updated with {result['total_patterns']} new successful cases!"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/knowledge_stats', methods=['GET'])
def api_knowledge_stats():
    """
    GET /api/knowledge_stats

    Get AI Self-Learning statistics

    Returns:
        {
            "total_patterns": 25,
            "last_updated": "2026-02-07T22:00:00",
            "clients_helped": 8,
            "most_used": [...],
            "recent": [...]
        }
    """
    try:
        from knowledge_base_storage import get_knowledge_base

        kb_storage = get_knowledge_base()
        stats = kb_storage.get_statistics()

        return jsonify({
            "success": True,
            "stats": stats
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/general_stats', methods=['GET'])
def api_general_stats():
    """
    GET /api/general_stats

    Get general analytics stats from all reports

    Returns:
        {
            "total_reports": 5,
            "win_count": 3,
            "loss_count": 1,
            "unknown_count": 1,
            "total_revenue": 15000.00,
            "average_confidence": 85,
            "last_updated": "2026-02-07T12:00:00"
        }
    """
    try:
        from features.analytics_engine import UnifiedReportAnalyzer
        from pathlib import Path
        import re

        analyzer = UnifiedReportAnalyzer(reports_folder='reports')

        # Get all reports and analyze them
        report_files = list(Path('reports').glob('*.txt')) if Path('reports').exists() else []

        stats = {
            "total_reports": len(report_files),
            "win_count": 0,
            "loss_count": 0,
            "unknown_count": 0,
            "total_revenue": 0.0,
            "average_confidence": 0,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        confidence_scores = []

        for report_file in report_files:
            try:
                text = report_file.read_text(encoding='utf-8')

                # Extract deal status
                status = analyzer.extract_deal_status(text)
                if status == "Win":
                    stats["win_count"] += 1
                elif status == "Loss":
                    stats["loss_count"] += 1
                else:
                    stats["unknown_count"] += 1

                # Extract revenue
                revenue = analyzer.extract_revenue(text)
                stats["total_revenue"] += revenue

                # Extract confidence
                confidence_match = re.search(r'ВПЕВНЕНІСТЬ ШІ:\s*(\d+)%', text)
                if confidence_match:
                    confidence_scores.append(int(confidence_match.group(1)))

            except Exception as e:
                print(f"[STATS] Error processing {report_file}: {e}")
                continue

        # Calculate average confidence
        if confidence_scores:
            stats["average_confidence"] = round(sum(confidence_scores) / len(confidence_scores))

        return jsonify(stats), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "total_reports": 0,
            "win_count": 0,
            "loss_count": 0,
            "unknown_count": 0,
            "total_revenue": 0.0,
            "average_confidence": 0,
            "error": str(e)
        }), 200  # Return 200 even on error to avoid breaking the UI
