from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os

BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
MAX_MEDIA = 10
MAX_VIDEO = 180

replying_user = None
rules = {}
users = set()

if os.path.exists("rules.json"):
    with open("rules.json","r",encoding="utf-8") as f: rules = json.load(f)
if os.path.exists("users.json"):
    with open("users.json","r",encoding="utf-8") as f: users = set(json.load(f))

def save():
    with open("rules.json","w",encoding="utf-8") as f: json.dump(rules,f,ensure_ascii=False,indent=2)
    with open("users.json","w",encoding="utf-8") as f: json.dump(list(users),f,ensure_ascii=False,indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user
    if update.effective_user.id == ADMIN_ID:
        replying_user = None
        await update.message.reply_text("✅ 已取消回复")
        return
    users.add(update.effective_user.id)
    save()
    await update.message.reply_text("📌 最多发10个媒体，视频≤3分钟")

async def set_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user
    txt = update.message.text.strip()
    if txt.isdigit():
        replying_user = int(txt)
        await update.message.reply_text(f"✅ 已绑定 {replying_user}，可直接回复")
    else:
        await update.message.reply_text("❌ 请输入数字ID")

async def msg_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user
    uid = update.effective_user.id
    msg = update.message

    if uid == ADMIN_ID and replying_user:
        try:
            if msg.photo: await context.bot.send_photo(replying_user, msg.photo[-1].file_id,caption=msg.caption)
            elif msg.video: await context.bot.send_video(replying_user, msg.video.file_id,caption=msg.caption)
            elif msg.text: await context.bot.send_message(replying_user, msg.text)
            await update.message.reply_text("✅ 已发送")
        except:
            await update.message.reply_text("❌ 失败")
        return

    cnt = len(msg.photo) if msg.photo else (1 if msg.video else 0)
    if msg.media_group_id: cnt = 999
    if cnt > MAX_MEDIA:
        await update.message.reply_text(f"❌ 最多{MAX_MEDIA}个媒体")
        return
    if msg.video and msg.video.duration > MAX_VIDEO:
        await update.message.reply_text("❌ 视频≤3分钟")
        return

    u = update.effective_user
    await context.bot.send_message(ADMIN_ID, f"👤{u.first_name}\n🆔{u.id}")
    if msg.photo: await context.bot.send_photo(ADMIN_ID, msg.photo[-1].file_id,caption=msg.caption)
    if msg.video: await context.bot.send_video(ADMIN_ID, msg.video.file_id,caption=msg.caption)
    if msg.text: await context.bot.send_message(ADMIN_ID, f"💬{msg.text}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d+$'), set_user))
    app.add_handler(MessageHandler(filters.ALL, msg_all))
    app.run_polling()

if __name__ == "__main__":
    main()
