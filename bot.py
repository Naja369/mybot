import json
import os
import telebot

# ==================== 环境变量配置 ====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

MAX_VIDEO_DURATION = 180
MAX_MEDIA_COUNT = 10
# ======================================================

bot = telebot.TeleBot(BOT_TOKEN)

# 存储文件
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

# 保存数据
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open(USER_FILE, "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False, indent=2)

# 全局状态
replying_user_id = None
temp_add_keyword = None

# ==================== /start ====================
@bot.message_handler(commands=['start'])
def start(message):
    global replying_user_id
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        replying_user_id = None
        bot.reply_to(message, "✅ 已取消回复模式")
        return

    users.add(user_id)
    save_data()
    bot.reply_to(message, "📢 要求：媒体不能超过10个，视频不能超过3分钟，且配好文案再发送！不然无法接收！")

# ==================== /reply ====================
@bot.message_handler(commands=['reply'])
def start_reply(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "✉️ 请输入用户ID")
    bot.register_next_step_handler(message, set_reply_user)

def set_reply_user(message):
    global replying_user_id
    uid = message.text.strip()
    if not uid.isdigit():
        bot.reply_to(message, "❌ ID必须是数字")
        bot.register_next_step_handler(message, set_reply_user)
        return
    replying_user_id = int(uid)
    bot.reply_to(message, f"✅ 已绑定用户 {replying_user_id}\n发消息直接回复TA，/start 取消")

# ==================== /add 新版关键词 ====================
@bot.message_handler(commands=['add'])
def add_keyword(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "🔑 请输入要设置的关键词")
    bot.register_next_step_handler(message, get_keyword)

def get_keyword(message):
    global temp_add_keyword
    temp_add_keyword = message.text.strip()
    bot.reply_to(message, "📤 请上传回复内容（可 文字+图片+视频 任意组合）\n上传完成后将自动保存")
    bot.register_next_step_handler(message, save_multi_content)

def save_multi_content(message):
    global temp_add_keyword
    kw = temp_add_keyword

    # 存储组合内容
    media_list = []
    caption = message.caption or message.text or ""

    # 图片
    if message.photo:
        for p in message.photo:
            media_list.append({"type": "photo", "file_id": p.file_id})

    # 视频
    if message.video:
        media_list.append({"type": "video", "file_id": message.video.file_id})

    # 纯文字
    if message.text and not message.photo and not message.video:
        media_list.append({"type": "text", "text": message.text})

    # 保存规则
    rules[kw] = {
        "caption": caption,
        "media": media_list
    }
    save_data()
    bot.reply_to(message, "✅ 规则保存成功！")

# ==================== /list ====================
@bot.message_handler(commands=['list'])
def show_rules(message):
    if message.from_user.id != ADMIN_ID:
        return
    text = f"📋 共 {len(rules)} 条关键词\n"
    for i, k in enumerate(list(rules.keys())[:20]):
        text += f"{i+1}. {k}\n"
    bot.reply_to(message, text)

# ==================== /del ====================
@bot.message_handler(commands=['del'])
def del_rule(message):
    if message.from_user.id != ADMIN_ID:
        return
    show_rules(message)
    bot.reply_to(message, "🗑 输入序号删除")
    bot.register_next_step_handler(message, delete_done)

def delete_done(message):
    try:
        idx = int(message.text) - 1
        key = list(rules.keys())[idx]
        del rules[key]
        save_data()
        bot.reply_to(message, "✅ 删除成功")
    except:
        bot.reply_to(message, "❌ 操作失败")

# ==================== /broadcast ====================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "📢 请发送群发内容")
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
    bot.reply_to(message, f"✅ 发送完成：{success} 人")

# ==================== 发送组合内容给用户 ====================
def send_combined_content(chat_id, rule):
    caption = rule.get("caption", "")
    media = rule.get("media", [])

    if not media:
        bot.send_message(chat_id, caption)
        return

    # 发送媒体组
    media_group = []
    for m in media:
        if m["type"] == "photo":
            media_group.append(telebot.InputMediaPhoto(media=m["file_id"], caption=caption if len(media_group)==0 else ""))
        elif m["type"] == "video":
            media_group.append(telebot.InputMediaVideo(media=m["file_id"], caption=caption if len(media_group)==0 else ""))
        elif m["type"] == "text":
            bot.send_message(chat_id, m["text"])

    if media_group:
        bot.send_media_group(chat_id, media_group)

# ==================== 用户消息处理 ====================
@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_all(message):
    global replying_user_id
    user_id = message.from_user.id

    # 管理员回复用户
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

    # 用户限制检查
    if message.video and message.video.duration > MAX_VIDEO_DURATION:
        bot.reply_to(message, "❌ 视频不能超过3分钟")
        return

    # 转发给管理员
    try:
        bot.send_message(ADMIN_ID, f"👤 {message.from_user.first_name}\n🆔 {user_id}")
        if message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
        if message.video:
            bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)
        if message.text and not message.photo and not message.video:
            bot.send_message(ADMIN_ID, f"💬 {message.text}")
    except:
        pass

    # 关键词触发（包含即可）
    text = message.text or message.caption or ""
    for kw, rule in rules.items():
        if kw in text:
            send_combined_content(user_id, rule)
            return

# ==================== 启动 ====================
if __name__ == "__main__":
    print("✅ 机器人运行中... Render Worker 模式")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
