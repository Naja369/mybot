from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import json
import os
import time
import threading
from flask import Flask

# ======================= 【你的信息】 =======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
MAX_VIDEO_DURATION = 180
MAX_MEDIA_COUNT = 10
# =============================================================

app = Flask('')
last_active_time = time.time()
replying_user_id = None  # 持续回复用户ID

@app.route('/')
def home():
    global last_active_time
    last_active_time = time.time()
    return "✅ 机器人运行中", 200

def run_web():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))

def keep_alive():
    threading.Thread(target=run_web, daemon=True).start()

# 数据文件
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

# 状态
GET_KW, GET_CONTENT = 0, 1
DEL_IDX = 2
BROADCAST = 3
INPUT_ID = 4

# ===================== /start 欢迎语 =====================
def start(update: Update, context: CallbackContext):
    global replying_user_id
    user_id = update.effective_user.id

    # 管理员点 /start = 取消持续回复
    if user_id == ADMIN_ID:
        replying_user_id = None
        keyboard = [
            ["➕ 添加关键词","📋 查看规则"],
            ["🗑 删除规则","📢 群发所有用户"],
            ["✉️ 持续回复用户"]
        ]
        update.message.reply_text("✅ 已取消回复模式\n👑 管理员面板", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
        return ConversationHandler.END

    # 用户点 /start
    users.add(user_id)
    save_data()
    update.message.reply_text(
        "📢 要求：媒体不能超过10个，视频不能超过3分钟，\n且配好文案再发送！不然无法接收！"
    )

# ===================== 持续回复用户（输入一次ID一直回复） =====================
def start_reply(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        return
    update.message.reply_text("✉️ 请输入用户ID，输入后可一直回复", reply_markup=ReplyKeyboardRemove())
    return INPUT_ID

def set_reply_user(update: Update, context: CallbackContext):
    global replying_user_id
    uid = update.message.text.strip()
    if not uid.isdigit():
        update.message.reply_text("❌ ID必须是数字")
        return INPUT_ID
    
    replying_user_id = int(uid)
    update.message.reply_text(f"✅ 已绑定用户 {replying_user_id}\n现在发任何内容都会直接发给TA\n发送 /start 取消")
    return ConversationHandler.END

# ===================== 关键词管理 =====================
def add_start(update: Update, context):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    update.message.reply_text("请输入关键词", reply_markup=ReplyKeyboardRemove())
    return GET_KW

def get_kw(update: Update, context):
    context.user_data["kw"] = update.message.text.strip()
    update.message.reply_text("发送回复内容")
    return GET_CONTENT

def save_kw(update: Update, context):
    kw = context.user_data["kw"]
    msg = update.message
    if msg.photo: rules[kw] = {"type":"photo","file":msg.photo[-1].file_id}
    elif msg.video: rules[kw] = {"type":"video","file":msg.video.file_id}
    elif msg.text: rules[kw] = {"type":"text","text":msg.text}
    save_data()
    update.message.reply_text("✅ 保存成功")
    start(update, context)
    return ConversationHandler.END

def show_rules(update: Update, context):
    if update.effective_user.id != ADMIN_ID: return
    text = f"📋 共 {len(rules)} 条\n"
    for i,k in enumerate(list(rules.keys())[:20]):
        text += f"{i+1}. {k}\n"
    update.message.reply_text(text)

def del_start(update: Update, context):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    show_rules(update, context)
    update.message.reply_text("输入序号删除")
    return DEL_IDX

def del_done(update: Update, context):
    try:
        idx = int(update.message.text)-1
        del rules[list(rules.keys())[idx]]
        save_data()
        update.message.reply_text("🗑 删除成功")
    except:
        update.message.reply_text("❌ 错误")
    start(update, context)
    return ConversationHandler.END

# ===================== 群发 =====================
def broadcast_start(update: Update, context):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    update.message.reply_text("发送群发内容（支持图文/视频+文字）\n/start 取消", reply_markup=ReplyKeyboardRemove())
    return BROADCAST

def broadcast_send(update: Update, context):
    msg = update.message
    success = 0
    for uid in users:
        try:
            if msg.photo: context.bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
            elif msg.video: context.bot.send_video(uid, msg.video.file_id, caption=msg.caption)
            elif msg.text: context.bot.send_message(uid, msg.text)
            success +=1
        except: continue
    update.message.reply_text(f"✅ 群发成功：{success} 人")
    start(update, context)
    return ConversationHandler.END

# ===================== 用户消息处理（支持一次性10个媒体 + 原样转发） =====================
def handle_user_message(update: Update, context: CallbackContext):
    global last_active_time
    last_active_time = time.time()
    user_id = update.effective_user.id
    msg = update.message

    if user_id == ADMIN_ID:
        # 管理员持续回复用户
        global replying_user_id
        if replying_user_id:
            try:
                if msg.photo: context.bot.send_photo(replying_user_id, msg.photo[-1].file_id, caption=msg.caption)
                elif msg.video: context.bot.send_video(replying_user_id, msg.video.file_id, caption=msg.caption)
                elif msg.text: context.bot.send_message(replying_user_id, msg.text)
                update.message.reply_text("✅ 已发送", quote=False)
            except:
                update.message.reply_text("❌ 发送失败", quote=False)
        return

    # 限制：一次性最多10个媒体
    media_num = 0
    if msg.photo: media_num = len(msg.photo)
    if msg.video: media_num = 1
    if msg.media_group_id: media_num = 100

    if media_num > MAX_MEDIA_COUNT:
        update.message.reply_text(f"❌ 最多发 {MAX_MEDIA_COUNT} 个媒体")
        return

    # 视频时长限制
    if msg.video and msg.video.duration > MAX_VIDEO_DURATION:
        update.message.reply_text("❌ 视频不能超过3分钟")
        return

    # 转发给管理员（原样显示图片/视频）
    user = update.effective_user
    context.bot.send_message(ADMIN_ID, f"👤 用户：{user.first_name}\n🆔 ID：{user.id}")
    
    if msg.photo: context.bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    elif msg.video: context.bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)
    elif msg.text: context.bot.send_message(ADMIN_ID, f"💬 {msg.text}")

    # 关键词模糊匹配
    if msg.text:
        for kw, content in rules.items():
            if kw in msg.text:
                try:
                    if content["type"] == "text": update.message.reply_text(content["text"])
                    elif content["type"] == "photo": update.message.reply_photo(content["file"])
                    elif content["type"] == "video": update.message.reply_video(content["file"])
                except: pass
                return

# ===================== 启动 =====================
def main():
    keep_alive()
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("✉️ 持续回复用户"), start_reply)],
        states={INPUT_ID: [MessageHandler(Filters.text & ~Filters.command, set_reply_user)]},
        fallbacks=[CommandHandler("start", start)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("➕ 添加关键词"), add_start)],
        states={GET_KW: [MessageHandler(Filters.text & ~Filters.command, get_kw)], GET_CONTENT: [MessageHandler(Filters.all & ~Filters.command, save_kw)]},
        fallbacks=[CommandHandler("start", start)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("🗑 删除规则"), del_start)],
        states={DEL_IDX: [MessageHandler(Filters.text & ~Filters.command, del_done)]},
        fallbacks=[CommandHandler("start", start)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex("📢 群发所有用户"), broadcast_start)],
        states={BROADCAST: [MessageHandler(Filters.all & ~Filters.command, broadcast_send)]},
        fallbacks=[CommandHandler("start", start)]
    ))

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex("📋 查看规则"), show_rules))
    dp.add_handler(MessageHandler(Filters.all & ~Filters.command, handle_user_message))

    print("✅ 机器人启动成功 — 持续回复模式")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
