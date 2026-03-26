import telebot
from telebot import types
import json
import os

# ====================== 【填写你的信息】 ======================
BOT_TOKEN = "7640455754:AAEBhj0W3_fUqd-yYDgRAvFqiegILbK0stM"
ADMIN_ID = 6649062737
# =============================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
mode = None  # 模式: None / reply / broadcast / set_key
target_user = None
temp_key = None

# ====================== 数据文件 ======================
def get_users():
    if not os.path.exists("users.json"):
        return []
    with open("users.json", "r", encoding="utf-8") as f:
        return list(set(json.load(f)))

def add_user(uid):
    users = get_users()
    if uid not in users:
        users.append(uid)
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False)

def get_keys():
    if not os.path.exists("keys.json"):
        return {}
    with open("keys.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_key(key, data):
    k = get_keys()
    k[key] = data
    with open("keys.json", "w", encoding="utf-8") as f:
        json.dump(k, f, ensure_ascii=False)

# ====================== 管理员按钮 ======================
def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📩 回复用户", "📢 群发消息")
    kb.add("🔑 设置关键词", "❌ 取消模式")
    return kb

# ====================== 提示语 ======================
WELCOME = "要求：媒体不能同时超过10个一起发送，并且视频不能高于3分钟"

# ====================== 启动命令 ======================
@bot.message_handler(commands=["start"])
def start(msg):
    global mode, target_user, temp_key
    cid = msg.chat.id
    if cid == ADMIN_ID:
        mode = None
        target_user = None
        temp_key = None
        bot.send_message(cid, "✅ 管理员面板", reply_markup=admin_menu())
    else:
        bot.send_message(cid, WELCOME)

# ====================== 管理员操作 ======================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def admin_handle(msg):
    global mode, target_user, temp_key
    cid = msg.chat.id
    txt = msg.text

    # 取消
    if txt == "❌ 取消模式":
        mode = None
        target_user = None
        temp_key = None
        bot.send_message(cid, "✅ 已取消", reply_markup=admin_menu())
        return

    # 回复用户
    if txt == "📩 回复用户":
        mode = "reply"
        bot.send_message(cid, "✏️ 输入用户ID：", reply_markup=admin_menu())
        return

    # 群发
    if txt == "📢 群发消息":
        mode = "broadcast"
        bot.send_message(cid, "📢 发送群发内容：", reply_markup=admin_menu())
        return

    # 设置关键词
    if txt == "🔑 设置关键词":
        mode = "set_key"
        bot.send_message(cid, "🔑 请发送要设置的关键词：", reply_markup=admin_menu())
        return

    # 输入关键词
    if mode == "set_key" and txt and not temp_key:
        temp_key = txt.strip()
        bot.send_message(cid, "✅ 请发送关键词回复内容（文字/图片/视频）：", reply_markup=admin_menu())
        return

    # 保存关键词回复内容
    if mode == "set_key" and temp_key:
        data = {"type": "text", "value": ""}
        if msg.text:
            data = {"type": "text", "value": msg.text}
        elif msg.photo:
            data = {"type": "photo", "value": msg.photo[-1].file_id, "caption": msg.caption or ""}
        elif msg.video:
            data = {"type": "video", "value": msg.video.file_id, "caption": msg.caption or ""}
        save_key(temp_key, data)
        bot.send_message(cid, f"✅ 关键词「{temp_key}」已保存！", reply_markup=admin_menu())
        mode = None
        temp_key = None
        return

    # 回复用户
    if mode == "reply" and txt and txt.isdigit():
        target_user = int(txt)
        bot.send_message(cid, f"✅ 已绑定 {target_user}", reply_markup=admin_menu())
        return
    if mode == "reply" and target_user:
        try:
            if msg.text: bot.send_message(target_user, msg.text)
            if msg.photo: bot.send_photo(target_user, msg.photo[-1].file_id, caption=msg.caption)
            if msg.video: bot.send_video(target_user, msg.video.file_id, caption=msg.caption)
            bot.send_message(cid, "✅ 发送成功", reply_markup=admin_menu())
        except:
            bot.send_message(cid, "❌ 失败", reply_markup=admin_menu())
        return

    # 群发
    if mode == "broadcast":
        users = get_users()
        cnt = 0
        for uid in users:
            try:
                if msg.text: bot.send_message(uid, msg.text)
                if msg.photo: bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
                if msg.video: bot.send_video(uid, msg.video.file_id, caption=msg.caption)
                cnt +=1
            except: pass
        bot.send_message(cid, f"✅ 群发成功：{cnt}/{len(users)}", reply_markup=admin_menu())
        mode = None
        return

# ====================== 用户消息验证 ======================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID, content_types=['text','photo','video'])
def user_msg(msg):
    uid = msg.chat.id
    add_user(uid)

    # 检查媒体组
    if hasattr(msg, 'media_group_id'):
        bot.send_message(uid, WELCOME)
        return

    media_num = 0
    if msg.photo: media_num +=1
    if msg.video: media_num +=1
    if media_num > 10:
        bot.send_message(uid, WELCOME)
        return

    if msg.video and msg.video.duration > 180:
        bot.send_message(uid, WELCOME)
        return

    # 关键词触发回复
    text = msg.text or ""
    keys = get_keys()
    for kw in keys:
        if kw in text:
            d = keys[kw]
            if d["type"] == "text":
                bot.send_message(uid, d["value"])
            elif d["type"] == "photo":
                bot.send_photo(uid, d["value"], caption=d.get("caption", ""))
            elif d["type"] == "video":
                bot.send_video(uid, d["value"], caption=d.get("caption", ""))

    # 转发管理员
    bot.send_message(ADMIN_ID, f"👤 {msg.from_user.first_name}\n🆔 {uid}")
    if msg.text:
        bot.send_message(ADMIN_ID, f"💬 {msg.text}")
    if msg.photo:
        bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    if msg.video:
        bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)

# ====================== 启动 ======================
if __name__ == "__main__":
    print("✅ 机器人启动成功！完整版运行中！")
    bot.infinity_polling()
