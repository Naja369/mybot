import telebot
import os

# ====================== 【你只需要改这里！】 ======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
# ==================================================================

bot = telebot.TeleBot(BOT_TOKEN)
replying_user = None

# ====================== 功能实现 ======================
@bot.message_handler(commands=['start'])
def start(message):
    global replying_user
    if message.from_user.id == ADMIN_ID:
        replying_user = None
        bot.reply_to(message, "✅ 管理员已重置\n输入用户ID即可回复")
    else:
        bot.reply_to(message, "✅ 消息会转发给管理员")

# 处理所有消息（文字、图片、视频）
@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_all(message):
    global replying_user
    uid = message.from_user.id
    name = message.from_user.first_name

    # ============== 管理员模式：回复用户 ==============
    if uid == ADMIN_ID:
        # 输入纯数字 = 绑定用户ID
        if message.text and message.text.isdigit():
            replying_user = int(message.text)
            bot.reply_to(message, f"✅ 已绑定用户：{replying_user}")
            return

        # 已绑定用户 → 发什么都转发给用户
        if replying_user:
            try:
                if message.text:
                    bot.send_message(replying_user, message.text)
                elif message.photo:
                    bot.send_photo(replying_user, message.photo[-1].file_id, caption=message.caption)
                elif message.video:
                    bot.send_video(replying_user, message.video.file_id, caption=message.caption)
                bot.reply_to(message, "✅ 已发送")
            except:
                bot.reply_to(message, "❌ 发送失败")
        return

    # ============== 用户模式：转发给管理员 ==============
    bot.send_message(ADMIN_ID, f"👤 {name}\n🆔 {uid}")
    if message.text:
        bot.send_message(ADMIN_ID, f"💬 {message.text}")
    elif message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=message.caption)
    elif message.video:
        bot.send_video(ADMIN_ID, message.video.file_id, caption=message.caption)

# ====================== 启动机器人 ======================
if __name__ == "__main__":
    print("✅ 机器人启动成功！功能全部正常！")
    bot.infinity_polling()
