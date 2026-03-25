import telebot

# ================== 填写你自己的 ==================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
# ==================================================

bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ 机器人部署成功！正常运行中！")

@bot.message_handler(func=lambda msg: True)
def reply_all(message):
    bot.reply_to(message, "✅ 收到消息：" + message.text)

if __name__ == "__main__":
    print("✅ 机器人启动成功！")
    bot.infinity_polling()
