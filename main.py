from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import json
import os

# ======================= 【你的信息】 =======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
MAX_VIDEO_DURATION = 180
MAX_MEDIA_COUNT = 10
# =============================================================

replying_user_id = None

DATA_FILE = "rules.json"
USER_FILE = "users.json"
rules = {}
users = set()

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, encoding="utf-8") as f:
        rules = json.load(f)
if os.path.exists(USER_FILE):
    with open(USER_FILE, encoding="utf-8") as f:
        users = set(json.load(f))

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False)

# ===================== /start =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user_id
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        replying_user_id = None
        keyboard = [
            ["➕ 添加关键词","📋 查看规则"],
            ["🗑 删除规则","📢 群发所有用户"],
            ["✉️ 持续回复用户"]
        ]
        await update.message.reply_text("✅ 已取消回复模式\n👑 管理员面板", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return

    users.add(user_id)
    save_data()
    await update.message.reply_text(
        "📢 要求：媒体不能超过10个，视频不能超过3分钟，\n且配好文案再发送！不然无法接收！"
    )

# ===================== 持续回复用户 =====================
async def start_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("✉️ 请输入用户ID，输入后可一直回复", reply_markup=ReplyKeyboardRemove())

async def set_reply_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user_id
    uid = update.message.text.strip()
    if not uid.isdigit():
        await update.message.reply_text("❌ ID必须是数字")
        return
    replying_user_id = int(uid)
    await update.message.reply_text(f"✅ 已绑定用户 {replying_user_id}\n现在发任何内容都会直接发给TA\n发送 /start 取消")

# ===================== 关键词管理 =====================
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("请输入关键词", reply_markup=ReplyKeyboardRemove())

async def get_kw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["kw"] = update.message.text.strip()
    await update.message.reply_text("发送回复内容")

async def save_kw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kw = context.user_data["kw"]
    msg = update.message
    if msg.photo:
        rules[kw] = {"type":"photo","file":msg.photo[-1].file_id}
    elif msg.video:
        rules[kw] = {"type":"video","file":msg.video.file_id}
    elif msg.text:
        rules[kw] = {"type":"text","text":msg.text}
    save_data()
    await update.message.reply_text("✅ 保存成功")
    await start(update, context)

async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = f"📋 共 {len(rules)} 条\n"
    for i,k in enumerate(list(rules.keys())[:20]):
        text += f"{i+1}. {k}\n"
    await update.message.reply_text(text)

async def del_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await show_rules(update, context)
    await update.message.reply_text("输入序号删除")

async def del_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        idx = int(update.message.text)-1
        del rules[list(rules.keys())[idx]]
        save_data()
        await update.message.reply_text("🗑 删除成功")
    except:
        await update.message.reply_text("❌ 错误")
    await start(update, context)

# ===================== 群发 =====================
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("发送群发内容（支持图文/视频+文字）\n/start 取消", reply_markup=ReplyKeyboardRemove())

async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    success = 0
    for uid in users:
        try:
            if msg.photo:
                await context.bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video:
                await context.bot.send_video(uid, msg.video.file_id, caption=msg.caption)
            elif msg.text:
                await context.bot.send_message(uid, msg.text)
            success += 1
        except:
            continue
    await update.message.reply_text(f"✅ 群发成功：{success} 人")
    await start(update, context)

# ===================== 用户消息 =====================
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global replying_user_id
    user_id = update.effective_user.id
    msg = update.message

    if user_id == ADMIN_ID:
        if replying_user_id:
            try:
                if msg.photo:
                    await context.bot.send_photo(replying_user_id, msg.photo[-1].file_id, caption=msg.caption)
                elif msg.video:
                    await context.bot.send_video(replying_user_id, msg.video.file_id, caption=msg.caption)
                elif msg.text:
                    await context.bot.send_message(replying_user_id, msg.text)
                await update.message.reply_text("✅ 已发送", quote=False)
            except:
                await update.message.reply_text("❌ 发送失败", quote=False)
        return

    media_num = 0
    if msg.photo: media_num = len(msg.photo)
    if msg.video: media_num = 1
    if msg.media_group_id: media_num = 100

    if media_num > MAX_MEDIA_COUNT:
        await update.message.reply_text(f"❌ 最多发 {MAX_MEDIA_COUNT} 个媒体")
        return

    if msg.video and msg.video.duration > MAX_VIDEO_DURATION:
        await update.message.reply_text("❌ 视频不能超过3分钟")
        return

    user = update.effective_user
    await context.bot.send_message(ADMIN_ID, f"👤 用户：{user.first_name}\n🆔 ID：{user.id}")
    
    if msg.photo:
        await context.bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    elif msg.video:
        await context.bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)
    elif msg.text:
        await context.bot.send_message(ADMIN_ID, f"💬 {msg.text}")

    if msg.text:
        for kw, content in rules.items():
            if kw in msg.text:
                try:
                    if content["type"] == "text":
                        await update.message.reply_text(content["text"])
                    elif content["type"] == "photo":
                        await update.message.reply_photo(content["file"])
                    elif content["type"] == "video":
                        await update.message.reply_video(content["file"])
                except:
                    pass
                return

# ===================== 启动 =====================
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^✉️ 持续回复用户$"), start_reply))
    application.add_handler(MessageHandler(filters.Regex("^➕ 添加关键词$"), add_start))
    application.add_handler(MessageHandler(filters.Regex("^📋 查看规则$"), show_rules))
    application.add_handler(MessageHandler(filters.Regex("^🗑 删除规则$"), del_start))
    application.add_handler(MessageHandler(filters.Regex("^📢 群发所有用户$"), broadcast_start))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_user_message))
    application.add_handler(MessageHandler(filters.VIDEO, handle_user_message))

    print("✅ 机器人启动成功 — 持续回复模式")
    application.run_polling()

if __name__ == "__main__":
    main()
