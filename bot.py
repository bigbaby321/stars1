
import json
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

import os
TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"
WAIT_TIME = 8 * 60 * 60

LEVELS = [(150000, 5, 1), (100000, 4, 3), (20000, 3, 12), (10000, 2, 17), (0, 1, 21)]

SEND_STAR_URL = "https://t.me/YourBotUsername?start=pay_{user_id}_{amount}"
SEND_STAR_INSTRUCTION = "\n\n*Hướng dẫn:* Gửi cú pháp `pay_YourTelegramID_SoSao` để nạp sao."

def get_level_info(total_deposit):
    for amount, level, days in LEVELS:
        if total_deposit >= amount:
            return level, days
    return 1, 21

def get_reward_by_level(level):
    return {1: 0.5, 2: 2, 3: 5, 4: 10, 5: 20}.get(level, 0.5)

try:
    with open(DATA_FILE, "r") as f:
        user_data = json.load(f)
except:
    user_data = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🪓 Khai Thác", callback_data="mine_menu"),
         InlineKeyboardButton("💼 Ví", callback_data="wallet")],
        [InlineKeyboardButton("💫 Gửi Sao Telegram", callback_data="send_star"),
         InlineKeyboardButton("🏆 BXH", callback_data="leaderboard")],
        [InlineKeyboardButton("💸 Rút Sao", callback_data="withdraw"),
         InlineKeyboardButton("📜 Lịch sử", callback_data="history_0")],
        [InlineKeyboardButton("🎖 Cấp độ VIP", callback_data="vip_level")],
        [InlineKeyboardButton("👨‍👩‍👧 Giới Thiệu", callback_data="referral")],
        [InlineKeyboardButton("📢 Kênh Chính", url="https://t.me/examplechannel"),
         InlineKeyboardButton("🛠 Hỗ Trợ", url="https://t.me/supportuser")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_menu")]])

def start(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0,
            "last_claim": 0,
            "deposits": [],
            "withdraw_requests": [],
            "mining_logs": []
        }
        save_data()

    if len(args) == 1 and args[0].startswith("pay_"):
        try:
            _, pay_user_id, pay_amount = args[0].split("_")
            if pay_user_id == user_id:
                amt = int(pay_amount)
                user_data[user_id]["balance"] += amt
                user_data[user_id]["deposits"].append({"amount": amt, "time": time.time()})
                save_data()
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"✅ Đã thanh toán `{amt}` sao.\nRút sau 21 ngày.",
                    parse_mode=ParseMode.MARKDOWN
                )
        except:
            context.bot.send_message(chat_id=update.effective_chat.id, text="❗ Lỗi định dạng.")

    balance = user_data[user_id]["balance"]
    total_deposit = sum(d["amount"] for d in user_data[user_id]["deposits"])
    level, _ = get_level_info(total_deposit)
    send_main_menu(update.effective_chat.id, context, balance, level)

def send_main_menu(chat_id, context, balance, level):
    msg = (
        "🎉 *Chào mừng đến hệ thống khai thác Sao Telegram!*\n\n"
        f"*🌟 Số dư:* `{balance}`\n"
        f"🎖 *Cấp độ:* `{level}`\n"
        "*⏳ Thu hoạch mỗi:* `8 giờ`\n\n"
        "_Hãy chọn chức năng bên dưới:_"
    )
    context.bot.send_message(
        chat_id=chat_id,
        text=msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu()
    )

def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    query.answer()

    if query.data.startswith("history"):
        page = int(query.data.split("_")[1])
        logs = []

        for d in user_data[user_id].get("deposits", []):
            logs.append(f"➕ Nạp {d['amount']} sao - {datetime.fromtimestamp(d['time']).strftime('%d/%m/%Y %H:%M')}")
        for w in user_data[user_id].get("withdraw_requests", []):
            if w.get("status") == "success":
                logs.append(f"➖ Rút {w['amount']} sao - {datetime.fromtimestamp(w['time']).strftime('%d/%m/%Y %H:%M')}")
        for m in user_data[user_id].get("mining_logs", []):
            logs.append(f"⛏ Khai thác {m['amount']} sao - {datetime.fromtimestamp(m['time']).strftime('%d/%m/%Y %H:%M')}")

        logs = sorted(logs, reverse=True)
        per_page = 10
        start = page * per_page
        end = start + per_page
        current = logs[start:end]

        text = "*📜 Lịch sử giao dịch:*

" + "
".join(current) if current else "📜 *Không có giao dịch.*"

        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"history_{page - 1}"))
        if end < len(logs):
            buttons.append(InlineKeyboardButton("Tiếp ➡️", callback_data=f"history_{page + 1}"))
        buttons.append(InlineKeyboardButton("⬅️ Quay lại", callback_data="back_to_menu"))

        query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([buttons]))

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(handle_button))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
