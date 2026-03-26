import json
import os
import telebot

# ==================== 环境变量 ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MAX_VIDEO_DURATION = 180
MAX_MEDIA_COUNT = 10
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
    bot.reply_to(message, "👑 管理员面板\n请点击按钮操作", reply_markup=keyboard)

# ==================== /start ====================
@bot.message_handler(commands=["start"])
def start(message):
    global temp_kw, replying_user_id
    user_id = message.from_user.id

    # 重置所有状态
    temp_kw = None
    replying_user_id = None

    if user_id == ADMIN_ID:
        admin_menu(message)
        return

    # 用户
    users.add(user_id)
    save_data()
    bot.reply_to(message, "📢 发送文字/图片/视频，我会转发给管理员\n包含关键词可自动回复")

# ==================== 添加关键词 ====================
@bot.message_handler(func=lambda m: m.text == "➕ 添加关键词")
def add_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "🔑 请输入关键词", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_kw)

def get_kw(message):
    global temp_kw
    temp_kw = message.text.strip()
    bot.reply_to(message, "📤 请上传回复内容（可文字+图片+视频）")
    bot.register_next_step_handler(message, save_content)

def save_content(message):
    global temp_kw
    if temp_kw is None:
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
    bot.reply_to(message, "✅ 关键词保存成功！")
    temp_kw = None
    admin_menu(message)

# ==================== 查看关键词（带编号） ====================
@bot.message_handler(func=lambda m: m.text == "📋 查看关键词")
def list_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    if not rules:
        bot.reply_to(message, "📭 暂无关键词")
        return
    text = "📋 关键词列表（编号顺序）\n"
    for i, key in enumerate(list(rules.keys()), 1):
        text += f"{i}. {key}\n"
    bot.reply_to(message, text)

# ==================== 删除关键词 ====================
@bot.message_handler(func=lambda m: m.text == "🗑 删除关键词")
def del_kw(message):
    if message.from_user.id != ADMIN_ID:
        return
    list_kw(message)
    bot.reply_to(message, "🗑 请输入要删除的**数字编号**", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, do_del)

def do_del(message):
    try:
        idx = int(message.text) - 1
        keys = list(rules.keys())
        del rules[keys[idx]]
        save_data()
        bot.reply_to(message, "✅ 删除成功")
    except:
        bot.reply_to(message, "❌ 编号错误")
    admin_menu(message)

# ==================== 群发 ====================
@bot.message_handler(func=lambda m: m.text == "📢 群发所有用户")
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "📢 请发送群发内容", reply_markup=telebot.types.ReplyKeyboardRemove())
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
            success += 1
        except:
            continue
    bot.reply_to(message, f"✅ 群发完成：{success} 人")
    admin_menu(message)

# ==================== 一对一回复用户 ====================
@bot.message_handler(func=lambda m: m.text == "✉️ 一对一回复用户")
def reply_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "✉️ 请输入用户ID", reply_markup=telebot.types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, set_reply)

def set_reply(message):
    global replying_user_id
    uid = message.text.strip()
    if not uid.isdigit():
        bot.reply_to(message, "❌ 请输入数字ID")
        bot.register_next_step_handler(message, set_reply)
        return
    replying_user_id = int(uid)
    bot.reply_to(message, f"✅ 已绑定用户 {replying_user_id}\n发送内容将直接回复对方")

# ==================== 发送组合内容给用户 ====================
def send_combined(chat_id, rule):
    caption = rule.get("caption", "")
    media = rule.get("media", [])
    group = []
    has_text = False

    for item in media:
        if item["type"] == "photo":
            group.append(telebot.InputMediaPhoto(item["file_id"], caption=caption if not group else ""))
        elif item["type"] == "video":
            group.append(telebot.InputMediaVideo(item["file_id"], caption=caption if not group else ""))
        elif item["type"] == "text":
            bot.send_message(chat_id, item["text"])
            has_text = True

    if group:
        bot.send_media_group(chat_id, group)

# ==================== 用户消息处理 ====================
@bot.message_handler(content_types=["text", "photo", "video"])
def handle_all(message):
    global replying_user_id
    user_id = message.from_user.id
    text = message.text or message.caption or ""

    # 管理员一对一回复
    if user_id == ADMIN_ID and replying_user_id is not None:
        try:
            if message.photo:
                bot.send_photo(replying_user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(replying_user_id, message.video.file_id, caption=message.caption)
            else:
                bot.send_message(replying_user_id, message.text)
            bot.reply_to(message, "✅ 已发送")
        except:
            bot.reply_to(message, "❌ 发送失败")
        return

    # 用户限制
    if message.video and message.video.duration > MAX_VIDEO_DURATION:
        bot.reply_to(message, "❌ 视频不能超过3分钟")
        return

    # 转发给管理员
    if user_id != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"👤 {message.from_user.first_name}\n🆔 {user_id}")
        if message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
        if message.video:
            bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)
        if message.text and not message.photo and not message.video:
            bot.send_message(ADMIN_ID, f"💬 {message.text}")

    # 关键词模糊触发
    for kw, rule in rules.items():
        if kw in text:
            send_combined(user_id, rule)
            return

# ==================== 启动 ====================
if __name__ == "__main__":
    print("✅ 机器人运行中 — Render Worker 永不休眠")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
