from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os

# ====================== 你的配置 ======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
MAX_MEDIA = 10
MAX_VIDEO_TIME = 180
# ======================================================

replying_user = None
rules = {}
users = set()

# 读取数据
if os.path.exists("rules.json"):
    with open("rules.json","r",encoding="utf-8") as f:
        rules = json.load(f)
if os.path.exists("users.json"):
    with open("users.json","r",encoding="utf-8") as f:
        users = set(json.load(f))

def save():
    with open("rules.json","w",encoding="utf-8") as f:
        json.dump(rules,f,ensure_ascii=False,indent=2)
    with open("users.json","w",encoding="utf-8") as f:
        json.dump(list(users),f,ensure_ascii=False,indent=2)

# ====================== 功能区 ======================
async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    global replying_user
    uid = update.effective_user.id
    if uid == ADMIN_ID:
        replying_user = None
        kb = [["➕ 添加关键词","📋 查看规则"],["🗑 删除规则","📢 群发"],["✉️ 持续回复用户"]]
        await update.message.reply_text("✅ 已取消回复\n👑管理员面板", reply_markup=ReplyKeyboardMarkup(kb,resize_keyboard=True))
        return
    users.add(uid)
    save()
    await update.message.reply_text("📌最多发10个媒体，视频≤3分钟")

async def reply_start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✏️输入用户ID")

async def reply_set(update:Update, context:ContextTypes.DEFAULT_TYPE):
    global replying_user
    t = update.message.text.strip()
    if not t.isdigit():
        await update.message.reply_text("❌ID必须是数字")
        return
    replying_user = int(t)
    await update.message.reply_text(f"✅已绑定 {replying_user}，发消息直接回复，/start取消")

async def msg_handle(update:Update, context:ContextTypes.DEFAULT_TYPE):
    global replying_user
    uid = update.effective_user.id
    msg = update.message

    # 管理员持续回复
    if uid == ADMIN_ID and replying_user:
        try:
            if msg.photo: await context.bot.send_photo(replying_user, msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video: await context.bot.send_video(replying_user, msg.video.file_id, caption=msg.caption)
            elif msg.text: await context.bot.send_message(replying_user, msg.text)
            await update.message.reply_text("✅已发送")
        except:
            await update.message.reply_text("❌发送失败")
        return

    # 用户限制
    cnt = len(msg.photo) if msg.photo else (1 if msg.video else 0)
    if msg.media_group_id: cnt=999
    if cnt>MAX_MEDIA:
        await update.message.reply_text(f"❌最多发{MAX_MEDIA}个媒体")
        return
    if msg.video and msg.video.duration>MAX_VIDEO_TIME:
        await update.message.reply_text("❌视频≤3分钟")
        return

    # 转发给管理员
    u = update.effective_user
    await context.bot.send_message(ADMIN_ID, f"👤{u.first_name}\n🆔{u.id}")
    if msg.photo: await context.bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    elif msg.video: await context.bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)
    elif msg.text: await context.bot.send_message(ADMIN_ID, f"💬{msg.text}")

    # 关键词
    if msg.text:
        for k in rules:
            if k in msg.text:
                c = rules[k]
                if c["type"]=="text": await update.message.reply_text(c["text"])
                if c["type"]=="photo": await update.message.reply_photo(c["file"])
                if c["type"]=="video": await update.message.reply_video(c["file"])
                return

# ====================== 启动 ======================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("✉️ 持续回复用户"), reply_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handle))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, msg_handle))

    print("✅ 机器人启动成功！")
    app.run_polling()

if __name__=="__main__":
    main()
