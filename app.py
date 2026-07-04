import os
from dotenv import load_dotenv
from flask import Flask, request, abort

load_dotenv()
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    FollowEvent,
    JoinEvent,
    LeaveEvent,
    UnfollowEvent,
)

import stock
import subscribers

app = Flask(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


# ── 定時推播 ──────────────────────────────────────────────
def push_daily_summary():
    targets = subscribers.get_all_targets()
    if not targets:
        return

    message = stock.daily_summary()
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        for target_id in targets:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=target_id,
                        messages=[TextMessage(text=message)],
                    )
                )
            except Exception as e:
                print(f"推播失敗 {target_id}: {e}")


# 美股收盤後推播（台灣時間週二~六 05:30，對應美東時間前一天 16:30）
# 台股收盤後推播（台灣時間週一~五 14:00）
scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(
    push_daily_summary,
    CronTrigger(day_of_week="tue-sat", hour=5, minute=30, timezone="Asia/Taipei"),
    id="us_close",
)
scheduler.add_job(
    push_daily_summary,
    CronTrigger(day_of_week="mon-fri", hour=14, minute=0, timezone="Asia/Taipei"),
    id="tw_close",
)
scheduler.start()


# ── Webhook ───────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


# 使用者加入 Bot → 訂閱推播
@handler.add(FollowEvent)
def handle_follow(event):
    subscribers.add_user(event.source.user_id)
    _reply(event, "👋 歡迎！已自動訂閱每日收盤摘要推播。\n\n輸入「說明」查看查詢指令。")


# 使用者封鎖 Bot → 取消訂閱
@handler.add(UnfollowEvent)
def handle_unfollow(event):
    subscribers.remove_user(event.source.user_id)


# Bot 加入群組 → 訂閱群組推播
@handler.add(JoinEvent)
def handle_join(event):
    if event.source.type == "group":
        subscribers.add_group(event.source.group_id)
    elif event.source.type == "room":
        subscribers.add_group(event.source.room_id)
    _reply(event, "📊 已加入！每日收盤後自動推播摘要。\n輸入「說明」查看查詢指令。")


# Bot 離開群組 → 取消訂閱
@handler.add(LeaveEvent)
def handle_leave(event):
    if event.source.type == "group":
        subscribers.remove_group(event.source.group_id)


# 文字訊息處理
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text.strip()

    # 查詢自己的 User ID
    if text in ("我的ID", "my id", "userid"):
        reply = f"您的 LINE User ID：\n{event.source.user_id}"
    # 自選清單
    elif text in ("我的清單", "自選清單", "清單"):
        reply = stock.watchlist_summary()
    # 手動觸發推播（測試用）
    elif text == "測試推播":
        reply = stock.daily_summary()
    # 訂閱/取消
    elif text == "訂閱":
        subscribers.add_user(event.source.user_id)
        reply = "✅ 已訂閱每日收盤摘要推播"
    elif text == "取消訂閱":
        subscribers.remove_user(event.source.user_id)
        reply = "❌ 已取消訂閱"
    else:
        reply = stock.query(text)

    _reply(event, reply)


def _reply(event, text: str):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=text)],
            )
        )


if __name__ == "__main__":
    app.run(port=5000, debug=True)
