from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from tinydb import TinyDB, Query
from datetime import datetime
import os

# Lấy token từ biến môi trường
TOKEN = os.environ.get("TOKEN")

# DB đơn giản bằng TinyDB
db = TinyDB("users.json")
User = Query()

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get(User.user_id == user_id)

    if not user:
        db.insert({
            "user_id": user_id,
            "stars": 0,
            "deposit_date": None,
            "status": "idle"
        })
        update.message.reply_text("👋 Chào mừng bạn đến với bot chuyển đổi sao Telegram thành USDT!")
    else:
        update.message.reply_text("👋 Bạn đã từng sử dụng bot này rồi!")

def deposit(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    args = context.args

    if not args or not args[0].isdigit():
        update.message.reply_text("❌ Vui lòng nhập số sao muốn nạp. Ví dụ: /deposit 100")
        return

    stars = int(args[0])
    today = datetime.now().strftime("%Y-%m-%d")

    user = db.get(User.user_id == user_id)
    if user:
        db.update({
            "stars": stars,
            "deposit_date": today,
            "status": "pending"
        }, User.user_id == user_id)
        update.message.reply_text(
            f"✅ Bạn đã nạp {stars} sao.\n⏳ Chờ admin duyệt.\n📅 Ngày nạp: {today}"
        )
    else:
        update.message.reply_text("Bạn chưa dùng /start. Vui lòng gửi /start trước.")

def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user = db.get(User.user_id == user_id)

    if not user or user["stars"] == 0:
        update.message.reply_text("💼 Bạn chưa nạp sao nào. Sử dụng /deposit để nạp.")
        return

    deposit_date = user.get("deposit_date")
    stars = user["stars"]

    if not deposit_date:
        update.message.reply_text("❗ Dữ liệu ngày nạp bị thiếu. Vui lòng liên hệ admin.")
        return

    deposit_day = datetime.strptime(deposit_date, "%Y-%m-%d")
    today = datetime.now()
    delta = (today - deposit_day).days
    days_left = max(0, 21 - delta)

    update.message.reply_text(
        f"💼 Số dư sao: {stars}\n📅 Ngày nạp: {deposit_date}\n⏳ Còn {days_left} ngày nữa là bạn có thể rút USDT."
    )

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("deposit", deposit))
    dp.add_handler(CommandHandler("balance", balance))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()