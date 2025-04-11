import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import json
import time
from datetime import datetime

# === Logging ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Config ===
TOKEN = os.getenv("TOKEN")
DATA_FILE = "data.json"
WAIT_TIME = 8 * 60 * 60
LEVELS = [(150000, 5, 1), (100000, 4, 3), (20000, 3, 12), (10000, 2, 17), (0, 1, 21)]

# === Data ===
try:
    with open(DATA_FILE, "r") as f:
        user_data = json.load(f)
except FileNotFoundError:
    user_data = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(user_data, f)

def get_level_info(total_deposit):
    for amount, level, days in LEVELS:
        if total_deposit >= amount:
            return level, days
    return 1, 21

def get_reward_by_level(level):
    return {1: 0.5, 2: 2, 3: 5, 4: 10, 5: 20}.get(level, 0.5)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("🪓 Khai Thác", callback_data="mine_menu"),
         InlineKeyboardButton("💼 Ví", callback_data="wallet")],
        [InlineKeyboardButton("📜 Lịch sử", callback_data="history_0")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {
            "balance": 0,
            "last_claim": 0,
            "deposits": [],
            "withdraw_requests": [],
            "mining_logs": []
        }
        save_data()
    balance = user_data[user_id]["balance"]
    deposits = user_data[user_id].get("deposits", [])
    total = sum(d["amount"] for d in deposits)
    level, _ = get_level_info(total)
    text = f"Welcome!\n\nBalance: {balance}\nLevel: {level}"
    await update.message.reply_text(text, reply_markup=get_main_menu())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    await query.answer()

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
\n" + "\n".join(current) if current else "🔍 Không có giao dịch."
        buttons = []
        if page > 0:
            buttons.append(InlineKeyboardButton("⬅️ Trước", callback_data=f"history_{page - 1}"))
        if end < len(logs):
            buttons.append(InlineKeyboardButton("Tiếp ➡️", callback_data=f"history_{page + 1}"))
        buttons.append(InlineKeyboardButton("⬅️ Quay lại", callback_data="mine_menu"))

        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup([buttons]))

    elif query.data == "mine_menu":
        now = time.time()
        last = user_data[user_id]["last_claim"]
        total_deposit = sum(d["amount"] for d in user_data[user_id]["deposits"])
        level, _ = get_level_info(total_deposit)
        reward = get_reward_by_level(level)
        remaining = max(0, int(WAIT_TIME - (now - last)))
        remaining_str = time.strftime('%H:%M:%S', time.gmtime(remaining))
        msg = (
            f"🪓 *Khai Thác Sao*\n\n"
            f"📈 Cấp độ: *{level}*\n"
            f"🎁 Phần thưởng: *{reward} sao*\n"
            f"🌟 Số dư: `{user_data[user_id]['balance']}`\n"
            f"⏳ Thời gian còn lại: `{remaining_str}`"
        )
        btn = [[InlineKeyboardButton("🪓 Thu Hoạch", callback_data="mine_now")]]
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(btn))

    elif query.data == "mine_now":
        now = time.time()
        last = user_data[user_id]["last_claim"]
        if now - last >= WAIT_TIME:
            total_deposit = sum(d["amount"] for d in user_data[user_id]["deposits"])
            level, _ = get_level_info(total_deposit)
            reward = get_reward_by_level(level)
            user_data[user_id]["balance"] += reward
            user_data[user_id]["last_claim"] = now
            user_data[user_id]["mining_logs"].append({"amount": reward, "time": now})
            save_data()
            await query.edit_message_text(f"✅ Đã khai thác thành công! 🌟 +{reward} sao.", reply_markup=get_main_menu())
        else:
            await query.edit_message_text("⏳ Chưa đến thời gian khai thác. Vui lòng chờ thêm!", reply_markup=get_main_menu())

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    print("✅ Bot started.")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
