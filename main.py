import telebot
from telebot import types
import json
import os
import time

# ====================== 【你的信息】 ======================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")
if ADMIN_ID == 0:
    raise ValueError("ADMIN_ID environment variable is not set")
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
# [保持原有的 load_users, save_user, load_keys, save_key, del_key 函数不变]

# ====================== 重置状态 ======================
def reset_all():
    global mode, reply_uid, temp_key, temp_media
    mode = None
    reply_uid = None
    temp_key = None
    temp_media = []

# ====================== 管理员按钮（内联按钮） ======================
def admin_buttons():
    kb = types.InlineKeyboardMarkup()
    kb.row(
        types.InlineKeyboardButton("📩 回复用户", callback_data="reply"),
        types.InlineKeyboardButton("📢 群发消息", callback_data="broadcast")
    )
    kb.row(
        types.InlineKeyboardButton("🔑 添加关键词", callback_data="set_keyword"),
        types.InlineKeyboardButton("📋 查看关键词", callback_data="view_keywords")
    )
    kb.row(
        types.InlineKeyboardButton("🗑 删除关键词", callback_data="del_key"),
        types.InlineKeyboardButton("📊 统计信息", callback_data="stats")
    )
    kb.row(
        types.InlineKeyboardButton("❌ 全部取消", callback_data="cancel_all")
    )
    return kb

def cancel_button():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("❌ 取消", callback_data="cancel_all"))
    return kb

# ====================== 规则 ======================
RULE = "要求：媒体不能同时超过10个一起发送，并且视频不能高于3分钟"

# ====================== /start ======================
@bot.message_handler(commands=["start"])
def start(msg):
    reset_all()
    cid = msg.chat.id
    if cid == ADMIN_ID:
        bot.send_message(cid, "✅ 欢迎使用管理员面板\n\n请选择操作：", reply_markup=admin_buttons())
    else:
        save_user(cid)
        bot.send_message(cid, RULE)

# ====================== 回调查询处理（内联按钮点击） ======================
@bot.callback_query_handler(func=lambda call: call.from_user.id == ADMIN_ID)
def admin_callback(call):
    global mode, reply_uid, temp_key, temp_media
    cid = call.message.chat.id
    data = call.data
    
    bot.answer_callback_query(call.id)
    
    if data == "cancel_all":
        reset_all()
        bot.edit_message_text("✅ 已重置", cid, call.message.message_id, reply_markup=admin_buttons())
        return
    
    if data == "reply":
        mode = "reply"
        bot.edit_message_text("✏️ 请输入用户ID：", cid, call.message.message_id, reply_markup=cancel_button())
        return
    
    if data == "broadcast":
        mode = "broadcast"
        bot.edit_message_text("📤 请发送要群发的内容（文字/图片/视频）：", cid, call.message.message_id, reply_markup=cancel_button())
        return
    
    if data == "set_keyword":
        mode = "set_keyword"
        bot.edit_message_text("🔑 请发送关键词：", cid, call.message.message_id, reply_markup=cancel_button())
        return
    
    if data == "view_keywords":
        keys = load_keys()
        if not keys:
            bot.answer_callback_query(call.id, "📭 暂无关键词", show_alert=True)
        else:
            res = "📋 关键词列表：\n\n"
            for i, k in enumerate(keys.keys(), 1):
                res += f"{i}. {k}\n"
            bot.edit_message_text(res, cid, call.message.message_id, reply_markup=admin_buttons())
        return
    
    if data == "del_key":
        mode = "del_key"
        keys = load_keys()
        if not keys:
            bot.answer_callback_query(call.id, "📭 暂无关键词可删除", show_alert=True)
            return
        res = "🗑 请输入序号或关键词名称：\n\n"
        for i, k in enumerate(keys.keys(), 1):
            res += f"{i}. {k}\n"
        bot.edit_message_text(res, cid, call.message.message_id, reply_markup=cancel_button())
        return
    
    if data == "stats":
        users = load_users()
        keys = load_keys()
        stats_text = f"📊 机器人统计信息\n\n👥 用户总数：{len(users)}\n🔑 关键词总数：{len(keys)}"
        bot.answer_callback_query(call.id, stats_text, show_alert=True)
        return

# ====================== 管理员操作（文本消息处理） ======================
@bot.message_handler(func=lambda m: m.chat.id == ADMIN_ID)
def admin_actions(msg):
    global mode, reply_uid, temp_key, temp_media
    cid = msg.chat.id
    txt = msg.text or ""

    # ============== 添加关键词：第二步 收集内容 ==============
    if mode == "set_keyword" and txt:
        temp_key = txt.strip()
        mode = "set_media"
        temp_media = []
        bot.send_message(cid, "✅ 请发送回复内容（可发多张图/视频/混合，发送完成后点取消结束）", reply_markup=cancel_button())
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
            bot.send_message(cid, f"✅ 已添加 ({len(temp_media)} 项)", reply_markup=cancel_button())
        return

    # 绑定ID
    if mode == "reply" and txt.isdigit():
        reply_uid = int(txt)
        bot.send_message(cid, f"✅ 已绑定用户：{reply_uid}\n\n现在发送消息将转发给该用户", reply_markup=cancel_button())
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
            bot.send_message(cid, "✅ 已发送", reply_markup=cancel_button())
        except:
            bot.send_message(cid, "❌ 发送失败", reply_markup=cancel_button())
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
    print("✅ 机器人启动成功 - 内联按钮版本")
    while True:
        try:
            bot.infinity_polling(timeout=60)
        except:
            time.sleep(3)
