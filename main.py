import telebot
from telebot import types
import json
import os

# ====================== 【你的信息】 ======================
BOT_TOKEN = "7640455754:AAFDGnMMietMVA8jGbpa2Tii5aATc0PEkdQ"
ADMIN_ID = 6649062737
# ==========================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

mode = None
reply_uid = None
temp_key = None

# ====================== 数据 ======================
def load_users():
    if not os.path.exists("users.json"):
        return []
    with open("users.json", "r", encoding="utf-8") as f:
        return list(set(json.load(f)))

def save_user(uid):
    users = load_users()
    if uid not in users:
        users.append(uid)
        with open("users.json", "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False)

def load_keys():
    if not os.path.exists("keys.json"):
        return {}
    with open("keys.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_key(keyword, content):
    keys = load_keys()
    keys[keyword] = content
    with open("keys.json", "w", encoding="utf-8") as f:
        json.dump(keys, f, ensure_ascii=False)

def del_key(key):
    keys = load_keys()
    key_list = list(keys.keys())
    if key.isdigit() and 1 <= int(key) <= len(key_list):
        del keys[key_list[int(key)-1]]
    elif key in keys:
        del keys[key]
    with open("keys.json", "w", encoding="utf-8") as f:
        json.dump(keys, f, ensure_ascii=False)

# ====================== 管理员按钮 ======================
def admin_buttons():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📩 回复用户", "❌ 取消回复")
    kb.row("📢 群发消息", "❌ 取消群发")
    kb.row("🔑 添加关键词", "📋 查看关键词")
    kb.row("🗑 删除关键词", "❌ 全部取消")
    return kb

# ====================== 规则 ======================
RULE = "要求：媒体不能同时超过10个一起发送，并且视频不能高于3分钟"

# ====================== /start ======================
@bot.message_handler(commands=["start"])
def start(msg):
    global mode, reply_uid, temp_key
    cid = msg.chat.id
    if cid == ADMIN_ID:
        mode = None
        reply_uid = None
        temp_key = None
        bot.send_message(cid, "✅ 管理员面板", reply_markup=admin_buttons())
    else:
        bot.send_message(cid, RULE)

# ====================== 管理员操作 ======================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def admin_actions(msg):
    global mode, reply_uid, temp_key
    cid = msg.chat.id
    txt = msg.text or ""

    if txt in ["❌ 全部取消","❌ 取消回复","❌ 取消群发"]:
        mode = None
        reply_uid = None
        temp_key = None
        bot.send_message(cid, "✅ 已重置", reply_markup=admin_buttons())
        return

    if txt == "📩 回复用户":
        mode = "reply"
        bot.send_message(cid, "✏️ 输入用户ID：", reply_markup=admin_buttons())
        return

    if txt == "📢 群发消息":
        mode = "broadcast"
        bot.send_message(cid, "📤 发送群发内容：", reply_markup=admin_buttons())
        return

    if txt == "🔑 添加关键词":
        mode = "set_key1"
        bot.send_message(cid, "🔑 输入关键词：", reply_markup=admin_buttons())
        return

    if txt == "📋 查看关键词":
        keys = load_keys()
        if not keys:
            bot.send_message(cid, "📭 暂无关键词", reply_markup=admin_buttons())
            return
        res = "📋 关键词列表：\n"
        for i, k in enumerate(keys.keys(), 1):
            res += f"{i}. {k}\n"
        bot.send_message(cid, res, reply_markup=admin_buttons())
        return

    if txt == "🗑 删除关键词":
        mode = "del_key"
        bot.send_message(cid, "🗑 输入序号或关键词：", reply_markup=admin_buttons())
        return

    if mode == "reply" and txt.isdigit():
        reply_uid = int(txt)
        bot.send_message(cid, f"✅ 已绑定：{reply_uid}，可持续回复", reply_markup=admin_buttons())
        return

    if mode == "set_key1" and txt:
        temp_key = txt
        mode = "set_key2"
        bot.send_message(cid, "✅ 发送回复内容：", reply_markup=admin_buttons())
        return

    if mode == "set_key2" and temp_key:
        data = {}
        if msg.text:
            data = {"type":"text","txt":msg.text}
        elif msg.photo:
            data = {"type":"photo","file":msg.photo[-1].file_id,"cap":msg.caption or ""}
        elif msg.video:
            data = {"type":"video","file":msg.video.file_id,"cap":msg.caption or ""}
        save_key(temp_key, data)
        bot.send_message(cid, f"✅ 关键词「{temp_key}」已保存", reply_markup=admin_buttons())
        mode = None
        temp_key = None
        return

    if mode == "del_key" and txt:
        del_key(txt)
        bot.send_message(cid, "🗑 删除成功", reply_markup=admin_buttons())
        mode = None
        return

    if reply_uid is not None:
        try:
            if msg.text:
                bot.send_message(reply_uid, msg.text)
            if msg.photo:
                bot.send_photo(reply_uid, msg.photo[-1].file_id, caption=msg.caption)
            if msg.video:
                bot.send_video(reply_uid, msg.video.file_id, caption=msg.caption)
            bot.send_message(cid, "✅ 已发送", reply_markup=admin_buttons())
        except:
            bot.send_message(cid, "❌ 发送失败", reply_markup=admin_buttons())
        return

    if mode == "broadcast":
        users = load_users()
        ok = 0
        for uid in users:
            try:
                if msg.text: bot.send_message(uid, msg.text)
                if msg.photo: bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
                if msg.video: bot.send_video(uid, msg.video.file_id, caption=msg.caption)
                ok +=1
            except:
                pass
        bot.send_message(cid, f"✅ 群发成功：{ok}/{len(users)}", reply_markup=admin_buttons())
        mode = None
        return

# ====================== 用户消息 ======================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID, content_types=['text','photo','video'])
def user_msg(msg):
    uid = msg.chat.id
    save_user(uid)

    # 统计媒体数量（图片+视频）
    media_count = 0
    if msg.photo:
        media_count += 1
    if msg.video:
        media_count += 1

    # 视频时长
    video_too_long = False
    if msg.video and msg.video.duration > 180:
        video_too_long = True

    # 违规条件：媒体>10 或 视频>3分钟 → 任一满足就违规
    if media_count > 10 or video_too_long:
        bot.send_message(uid, RULE)
        return

    # ====================== 不违规 → 全部转发给你 ======================
    # 关键词触发（包含即可）
    text = msg.text or ""
    keys = load_keys()
    for kw in keys:
        if kw in text:
            d = keys[kw]
            if d["type"] == "text":
                bot.send_message(uid, d["txt"])
            elif d["type"] == "photo":
                bot.send_photo(uid, d["file"], caption=d.get("cap",""))
            elif d["type"] == "video":
                bot.send_video(uid, d["file"], caption=d.get("cap",""))

    # 转发给管理员（文字+图片+视频 一起发）
    bot.send_message(ADMIN_ID, f"👤 {msg.from_user.first_name}\n🆔 {uid}")
    if msg.text:
        bot.send_message(ADMIN_ID, f"💬 {msg.text}")
    if msg.photo:
        bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    if msg.video:
        bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)

# ====================== 启动 ======================
if __name__ == "__main__":
    print("✅ 机器人启动成功 - 最终完整版")
    bot.infinity_polling()
