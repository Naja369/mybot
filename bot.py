import json
import os
import telebot
import threading
import time

# ==================== 环境变量 ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MAX_VIDEO_DURATION = 180
# ==================================================

bot = telebot.TeleBot(BOT_TOKEN)

# 数据文件
DATA_FILE = "rules.json"
USER_FILE = "users.json"

rules = {}
users = set()

# 加载数据
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        rules = json.load(f)

if os.path.exists(USER_FILE):
    with open(USER_FILE, "r", encoding="utf-8") as f:
        users = set(json.load(f))

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False, indent=2)

# 全局状态
temp_kw = None
replying_user_id = None

# ==================== 管理员按钮菜单 ====================
def admin_menu(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        "➕ 添加关键词",
        "📋 查看关键词",
        "🗑 删除关键词",
        "📢 群发所有用户",
        "✉️ 一对一回复用户"
    )
    bot.reply_to(message, "👑 管理员面板", reply_markup=keyboard)

# ==================== /start ====================
@bot.message_handler(commands=["start"])
def start(message):
    global temp_kw, replying_user_id
    temp_kw = None
    replying_user_id = None

    if message.from_user.id == ADMIN_ID:
        admin_menu(message)
        return

    users.add(message.from_user.id)
    save_data()
    bot.reply_to(message, "📢 发送消息即可联系管理员")

# ==================== 添加关键词 ====================
@bot.message_handler(func=lambda m: m.text == "➕ 添加关键词")
def add_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "🔑 输入关键词", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_kw)

def get_kw(message):
    global temp_kw
    temp_kw = message.text.strip()
    bot.reply_to(message, "📤 上传内容（文字+图片+视频）")
    bot.register_next_step_handler(message, save_content)

def save_content(message):
    global temp_kw
    if not temp_kw:
        return

    caption = message.caption or message.text or ""
    media = []
    if message.photo:
        media.append({"type": "photo", "file_id": message.photo[-1].file_id})
    if message.video:
        media.append({"type": "video", "file_id": message.video.file_id})
    if message.text and not message.photo and not message.video:
        media.append({"type": "text", "text": message.text})

    rules[temp_kw] = {"caption": caption, "media": media}
    save_data()
    bot.reply_to(message, "✅ 保存成功")
    temp_kw = None
    admin_menu(message)

# ==================== 查看关键词 ====================
@bot.message_handler(func=lambda m: m.text == "📋 查看关键词")
def list_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not rules:
        bot.reply_to(message, "📭 暂无关键词")
        return
    text = "📋 关键词列表\n"
    for i, k in enumerate(list(rules.keys()), 1):
        text += f"{i}. {k}\n"
    bot.reply_to(message, text)

# ==================== 删除关键词 ====================
@bot.message_handler(func=lambda m: m.text == "🗑 删除关键词")
def del_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    list_kw(message)
    bot.reply_to(message, "🗑 输入编号删除", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, do_del)

def do_del(message):
    try:
        del rules[list(rules.keys())[int(message.text)-1]]
        save_data()
        bot.reply_to(message, "✅ 删除成功")
    except:
        bot.reply_to(message, "❌ 失败")
    admin_menu(message)

# ==================== 群发 ====================
@bot.message_handler(func=lambda m: m.text == "📢 群发所有用户")
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "📢 发送群发内容", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, do_broadcast)

def do_broadcast(message):
    success = 0
    for uid in users:
        try:
            if message.photo:
                bot.send_photo(uid, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(uid, message.video.file_id, caption=message.caption)
            else:
                bot.send_message(uid, message.text)
            success +=1
        except:
            continue
    bot.reply_to(message, f"✅ 发送完成 {success} 人")
    admin_menu(message)

# ==================== 一对一回复 ====================
@bot.message_handler(func=lambda m: m.text == "✉️ 一对一回复用户")
def reply_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "✉️ 输入用户ID", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_reply)

def set_reply(message):
    global replying_user_id
    if message.text.isdigit():
        replying_user_id = int(message.text)
        bot.reply_to(message, f"✅ 已绑定 {replying_user_id}")
    else:
        bot.reply_to(message, "❌ ID错误")

# ==================== 发送组合内容 ====================
def send_combined(chat_id, rule):
    caption = rule.get("caption", "")
    media = rule.get("media", [])
    group = []
    for item in media:
        if item["type"] == "photo":
            group.append(telebot.InputMediaPhoto(item["file_id"], caption=caption if not group else ""))
        if item["type"] == "video":
            group.append(telebot.InputMediaVideo(item["file_id"], caption=caption if not group else ""))
        if item["type"] == "text":
            bot.send_message(chat_id, item["text"])
    if group:
        bot.send_media_group(chat_id, group)

# ==================== 消息处理 ====================
@bot.message_handler(content_types=["text", "photo", "video"])
def handle_all(message):
    global replying_user_id
    uid = message.from_user.id

    # 管理员回复
    if uid == ADMIN_ID and replying_user_id is not None:
        try:
            if message.photo:
                bot.send_photo(replying_user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(replying_user_id, message.video.file_id, caption=message.caption)
            else:
                bot.send_message(replying_user_id, message.text)
            bot.reply_to(message, "✅ 已发送")
        except:
            bot.reply_to(message, "❌ 失败")
        return

    # 视频限制
    if message.video and message.video.duration > MAX_VIDEO_DURATION:
        bot.reply_to(message, "❌ 视频不能超过3分钟")
        return

    # 转发给管理员
    if uid != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"👤 {message.from_user.first_name} | 🆔 {uid}")
        if message.photo: bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
        if message.video: bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)
        if message.text and not message.photo and not message.video:
            bot.send_message(ADMIN_ID, f"💬 {message.text}")

    # 关键词触发
    text = (message.text or message.caption or "")
    for kw, rule in rules.items():
        if kw in text:
            send_combined(uid, rule)
            return

# ==================== 伪Web服务，防止超时（免费Web Service专用） ====================
from flask import Flask
app = Flask(__name__)

@app.route("/")
def index():
    return "✅ 机器人运行中"

def run_web():
    app.run(host="0.0.0.0", port=10000)

# ==================== 启动 ====================
if __name__ == "__main__":
    # 启动伪Web，防止超时
    threading.Thread(target=run_web, daemon=True).start()
    print("✅ 机器人启动（Web Service 免费版）")
    bot.infinity_polling(timeout=15, long_polling_timeout=5, skip_pending=True)
