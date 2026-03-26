import telebot
from telebot import types
import json
import os
import time

# ====================== 【你的信息】 ======================
BOT_TOKEN = "7640455754:AAF6fHaBz4WuuBqb_nGI8Lj7-rgOUMZ8WGU"
ADMIN_ID = 6649062737
# ==========================================================

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None, skip_pending=True)

# 状态
mode = None
reply_uid = None
temp_key = None
temp_media = []

user_last_notify = {}
NOTIFY_COOLDOWN = 300

# ====================== 数据存储 ======================
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

def save_key(keyword, medias):
    keys = load_keys()
    keys[keyword] = medias
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

# ====================== 重置状态 ======================
def reset_all():
    global mode, reply_uid, temp_key, temp_media
    mode = None
    reply_uid = None
    temp_key = None
    temp_media = []

# ====================== 管理员按钮 ======================
def admin_buttons():
    kb = types.ReplyKeyboardMarkup(resize_key=True)
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
    reset_all()
    cid = msg.chat.id
    if cid == ADMIN_ID:
        bot.send_message(cid, "✅ 管理员面板", reply_markup=admin_buttons())
    else:
        save_user(cid)
        bot.send_message(cid, RULE)

# ====================== 管理员操作 ======================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def admin_actions(msg):
    global mode, reply_uid, temp_key, temp_media
    cid = msg.chat.id
    txt = msg.text or ""

    if txt in ["📩 回复用户", "📢 群发消息", "🔑 添加关键词", "📋 查看关键词", "🗑 删除关键词"]:
        reset_all()

    if txt in ["❌ 全部取消","❌ 取消回复","❌ 取消群发"]:
        reset_all()
        bot.send_message(cid, "✅ 已重置", reply_markup=admin_buttons())
        return

    # 回复用户
    if txt == "📩 回复用户":
        mode = "reply"
        bot.send_message(cid, "✏️ 输入用户ID：", reply_markup=admin_buttons())
        return

    # 群发
    if txt == "📢 群发消息":
        mode = "broadcast"
        bot.send_message(cid, "📤 发送内容（文字/图片+文字/视频+文字）", reply_markup=admin_buttons())
        return

    # ============== 添加关键词：第一步 输入关键词 ==============
    if txt == "🔑 添加关键词":
        mode = "set_keyword"
        bot.send_message(cid, "🔑 请发送关键词：", reply_markup=admin_buttons())
        return

    # 查看关键词
    if txt == "📋 查看关键词":
        keys = load_keys()
        if not keys:
            bot.send_message(cid, "📭 暂无关键词", reply_markup=admin_buttons())
        else:
            res = "📋 关键词列表：\n"
            for i, k in enumerate(keys.keys(), 1):
                res += f"{i}. {k}\n"
            bot.send_message(cid, res, reply_markup=admin_buttons())
        return

    # 删除关键词
    if txt == "🗑 删除关键词":
        mode = "del_key"
        bot.send_message(cid, "🗑 输入序号或关键词：", reply_markup=admin_buttons())
        return

    # ============== 添加关键词：第二步 收集内容 ==============
    if mode == "set_keyword" and txt:
        temp_key = txt.strip()
        mode = "set_media"
        temp_media = []
        bot.send_message(cid, "✅ 请发送回复内容（可发多张图/视频/混合，发送完成后点取消结束）", reply_markup=admin_buttons())
        return

    # 收集媒体
    if mode == "set_media":
        item = None
        if msg.photo:
            item = {
                "type": "photo",
                "file": msg.photo[-1].file_id,
                "cap": msg.caption or ""
            }
        elif msg.video:
            item = {
                "type": "video",
                "file": msg.video.file_id,
                "cap": msg.caption or ""
            }
        elif msg.text:
            item = {
                "type": "text",
                "txt": msg.text
            }
        if item:
            temp_media.append(item)
        return

    # 绑定ID
    if mode == "reply" and txt.isdigit():
        reply_uid = int(txt)
        bot.send_message(cid, f"✅ 已绑定：{reply_uid}", reply_markup=admin_buttons())
        return

    # 删除确认
    if mode == "del_key" and txt:
        del_key(txt)
        bot.send_message(cid, "🗑 删除成功", reply_markup=admin_buttons())
        reset_all()
        return

    # 持续回复
    if reply_uid is not None:
        try:
            if msg.text: bot.send_message(reply_uid, msg.text)
            if msg.photo: bot.send_photo(reply_uid, msg.photo[-1].file_id, caption=msg.caption)
            if msg.video: bot.send_video(reply_uid, msg.video.file_id, caption=msg.caption)
            bot.send_message(cid, "✅ 已发送", reply_markup=admin_buttons())
        except:
            bot.send_message(cid, "❌ 失败", reply_markup=admin_buttons())
        return

    # 群发
    if mode == "broadcast":
        users = load_users()
        ok = 0
        for uid in users:
            try:
                if msg.text and not msg.photo and not msg.video:
                    bot.send_message(uid, msg.text)
                elif msg.photo:
                    bot.send_photo(uid, msg.photo[-1].file_id, caption=msg.caption)
                elif msg.video:
                    bot.send_video(uid, msg.video.file_id, caption=msg.caption)
                ok += 1
            except:
                pass
        bot.send_message(cid, f"✅ 群发成功：{ok}/{len(users)}", reply_markup=admin_buttons())
        reset_all()
        return

# ====================== 用户消息 ======================
@bot.message_handler(func=lambda m: m.chat.id != ADMIN_ID, content_types=['text','photo','video'])
def user_msg(msg):
    uid = msg.chat.id
    save_user(uid)
    now = time.time()

    media_count = 0
    if msg.photo: media_count +=1
    if msg.video: media_count +=1
    video_long = msg.video and msg.video.duration > 180 if msg.video else False

    if media_count > 10 or video_long:
        bot.send_message(uid, RULE)
        return

    # 关键词触发（支持多内容）
    text = msg.text or ""
    keys = load_keys()
    for kw in keys:
        if kw in text:
            for item in keys[kw]:
                try:
                    if item["type"] == "text":
                        bot.send_message(uid, item["txt"])
                    elif item["type"] == "photo":
                        bot.send_photo(uid, item["file"], caption=item.get("cap",""))
                    elif item["type"] == "video":
                        bot.send_video(uid, item["file"], caption=item.get("cap",""))
                except:
                    pass

    # 5分钟提示一次
    if uid not in user_last_notify or now - user_last_notify[uid] > NOTIFY_COOLDOWN:
        user_last_notify[uid] = now
        bot.send_message(ADMIN_ID, f"👤 {msg.from_user.first_name}\n🆔 {uid}")

    # 转发
    if msg.text: bot.send_message(ADMIN_ID, f"💬 {msg.text}")
    if msg.photo: bot.send_photo(ADMIN_ID, msg.photo[-1].file_id, caption=msg.caption)
    if msg.video: bot.send_video(ADMIN_ID, msg.video.file_id, caption=msg.caption)

# ====================== 启动 ======================
if __name__ == "__main__":
    print("✅ 机器人启动成功 - 最终终极版")
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except:
            time.sleep(3)
