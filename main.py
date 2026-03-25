import telebot
import json
import os

# ====================== 【你的信息】 ======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
MAX_VIDEO_DURATION = 180
MAX_MEDIA_COUNT = 10
# ==========================================================

bot = telebot.TeleBot(BOT_TOKEN)
replying_user_id = None

# 数据文件
if not os.path.exists("rules.json"):
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump({}, f)

if not os.path.exists("users.json"):
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump([], f)

with open("rules.json", "r", encoding="utf-8") as f:
    rules = json.load(f)

with open("users.json", "r", encoding="utf-8") as f:
    users = set(json.load(f))

def save_data():
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open("users.json", "w", encoding="utf-8") as f:
        json.dump(list(users), f, ensure_ascii=False, indent=2)

# ====================== /start ======================
@bot.message_handler(commands=['start'])
def start(message):
    global replying_user_id
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        replying_user_id = None
        bot.reply_to(message, "✅ 管理员模式\n功能：输入ID直接回复用户，发消息自动转发")
        return

    users.add(user_id)
    save_data()
    bot.reply_to(message, "📌 发送消息会自动转发给管理员\n视频≤3分钟，媒体≤10个")

# ====================== 自动转发给管理员 ======================
@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_message(message):
    global replying_user_id
    user_id = message.from_user.id
    name = message.from_user.first_name

    # 管理员回复用户
    if user_id == ADMIN_ID and replying_user_id:
        try:
            if message.text:
                bot.send_message(replying_user_id, message.text)
            elif message.photo:
                bot.send_photo(replying_user_id, message.photo[-1].file_id, caption=message.caption)
            elif message.video:
                bot.send_video(replying_user_id, message.video.file_id, caption=message.caption)
            bot.reply_to(message, "✅ 已发送")
        except:
            bot.reply_to(message, "❌ 发送失败")
        return

    # 用户消息转发给管理员
    if user_id != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"👤 {name}\n🆔 {user_id}")
        if message.text:
            bot.send_message(ADMIN_ID, f"💬 {message.text}")
            # 关键词回复
            for kw in rules:
                if kw in message.text:
                    r = rules[kw]
                    if r["type"] == "text":
                        bot.send_message(user_id, r["content"])
                    elif r["type"] == "photo":
                        bot.send_photo(user_id, r["content"])
                    elif r["type"] == "video":
                        bot.send_video(user_id, r["content"])
        elif message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
        elif message.video:
            bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)
        return

    # 管理员输入纯数字 = 绑定用户ID
    if user_id == ADMIN_ID and message.text and message.text.isdigit():
        replying_user_id = int(message.text)
        bot.reply_to(message, f"✅ 已绑定用户 {replying_user_id}\n发消息直接回复")

# ====================== 启动 ======================
if __name__ == "__main__":
    print("✅ 机器人启动成功！【完整版功能已上线】")
    bot.infinity_polling()
