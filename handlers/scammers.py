import logging, uuid
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import (
    MenuAction, ComplaintAction, ScammersPageAction, scam_base_kb, back_to_main,
    complaint_moderation_kb
)
from states import Complaint
from config import IMAGES, MODERATION_CHAT_ID

router = Router()

complaint_storage = {}

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

async def show_scammers_page(callback: CallbackQuery, db: Database, page: int):
    total = await db.get_scammers_count()
    total_pages = max(1, (total + 4) // 5)
    if page < 0: page = 0
    if page >= total_pages: page = total_pages - 1
    scammers = await db.get_scammers_page(page * 5, 5)
    if not scammers:
        txt = "<b>⚔️ ESPREZZO MARKET – Мошенники</b>\n\nСписок мошенников в данный момент находится на стадии формирования"
    else:
        txt = "<b>⚔️ ESPREZZO MARKET – Мошенники</b>\n\n"
        for i, (gn, un, uid) in enumerate(scammers, 1):
            idx = page * 5 + i
            game_nick = gn if gn else "—"
            username = un if un else "—"
            txt += f"⚠️ [{idx:02d}] Никнейм: {game_nick}\nUsername: @{username}\n\n"
    await callback.message.edit_media(
        InputMediaPhoto(media=IMAGES["scam_base"], caption=txt, parse_mode="HTML"),
        reply_markup=scam_base_kb(page, total_pages)
    )

@router.callback_query(ScammersPageAction.filter())
async def scammers_page_handler(callback: CallbackQuery, callback_data: ScammersPageAction, db: Database):
    await show_scammers_page(callback, db, callback_data.page)
    await callback.answer()

# ---------- Жалоба (редактирование одного сообщения) ----------
@router.callback_query(MenuAction.filter(F.action == "complaint"))
async def complaint_start(callback: CallbackQuery, state: FSMContext):
    # Заменяем медиа и текст ОДНИМ вызовом, указывая caption внутри InputMediaPhoto
    await callback.message.edit_media(
        InputMediaPhoto(
            media=IMAGES["username_input"],
            caption="<b>⚔️ ESPREZZO MARKET – Введите Nickname</b>\n\nВведите игровой nick_name мошенника. Если не знаете, отправьте «-»:",
            parse_mode="HTML"
        )
    )
    await state.set_state(Complaint.waiting_for_game_nickname)
    await state.update_data(complaint_msg_id=callback.message.message_id,
                            complaint_chat_id=callback.message.chat.id)
    await callback.answer()

@router.message(Complaint.waiting_for_game_nickname)
async def complaint_game_nickname(message: Message, state: FSMContext, bot: Bot):
    game_nickname = message.text.strip()
    if not game_nickname:
        game_nickname = "-"
    await state.update_data(game_nickname=game_nickname)
    data = await state.get_data()
    msg_id = data.get("complaint_msg_id")
    chat_id = data.get("complaint_chat_id")
    if msg_id and chat_id:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption="<b>⚔️ ESPREZZO MARKET – Введите Username</b>\n\nВведите username нарушителя. Без символа «@»:"
        )
    await state.set_state(Complaint.waiting_for_username)
    await message.delete()

@router.message(Complaint.waiting_for_username)
async def complaint_username(message: Message, state: FSMContext, bot: Bot):
    username = message.text.strip().lstrip('@')
    if not username:
        await message.answer("Введите корректный username")
        return
    await state.update_data(target_username=username)
    data = await state.get_data()
    msg_id = data.get("complaint_msg_id")
    chat_id = data.get("complaint_chat_id")
    if msg_id and chat_id:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption="<b>⚔️ ESPREZZO MARKET – Введите описание</b>\n\nОпишите краткое описание вашей жалобы:"
        )
    await state.set_state(Complaint.waiting_for_reason)
    await message.delete()

@router.message(Complaint.waiting_for_reason)
async def complaint_reason(message: Message, state: FSMContext, bot: Bot):
    reason = message.text
    await state.update_data(reason=reason)
    data = await state.get_data()
    msg_id = data.get("complaint_msg_id")
    chat_id = data.get("complaint_chat_id")
    if msg_id and chat_id:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption="<b>⚔️ ESPREZZO MARKET – Прикрепите фото</b>\n\nПрикрепите доказательства мошеннических действий:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Далее →", callback_data=MenuAction(action="finish_complaint").pack())]
            ])
        )
    await state.set_state(Complaint.waiting_for_photo)
    await state.update_data(media=[])
    await message.delete()

@router.message(Complaint.waiting_for_photo, F.photo)
async def complaint_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    media = data.get("media", [])
    media.append(message.photo[-1].file_id)
    await state.update_data(media=media)
    msg_id = data.get("complaint_msg_id")
    chat_id = data.get("complaint_chat_id")
    if msg_id and chat_id:
        new_caption = f"<b>⚔️ ESPREZZO MARKET – Прикрепите фото</b>\n\nПрикреплено изображений: {len(media)}"
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption=new_caption,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Далее →", callback_data=MenuAction(action="finish_complaint").pack())]
            ])
        )
    await message.delete()

@router.callback_query(MenuAction.filter(F.action == "finish_complaint"))
async def finish_complaint(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    game_nickname = data.get("game_nickname", "-")
    target_username = data.get("target_username")
    reason = data.get("reason")
    media = data.get("media", [])
    reporter_id = callback.from_user.id
    reporter_name = callback.from_user.full_name

    target_user = await db.get_user_by_username(target_username)
    target_uid = target_user[0] if target_user else None

    complaint_id = uuid.uuid4().hex[:8]
    complaint_storage[complaint_id] = {
        "reporter_id": reporter_id,
        "target_username": target_username,
        "game_nickname": game_nickname,
        "reason": reason
    }

    txt = (
        f"🚨 Новая жалоба\n\n"
        f"Игровой никнейм: {escape_html(game_nickname)}\n\n"
        f"Нарушитель: @{escape_html(target_username)} (ID: {target_uid or '—'})\n\n"
        f"От: {escape_html(reporter_name)} (ID: {reporter_id})\n\n"
        f"Причина: {escape_html(reason)}"
    )
    kb = complaint_moderation_kb(reporter_id, complaint_id)
    try:
        if media:
            await bot.send_photo(MODERATION_CHAT_ID, media[0], caption=txt, reply_markup=kb)
            if len(media) > 1:
                group = [InputMediaPhoto(media=fid) for fid in media[1:]]
                await bot.send_media_group(MODERATION_CHAT_ID, group)
        else:
            await bot.send_message(MODERATION_CHAT_ID, txt, reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка отправки жалобы: {e}")

    await callback.message.edit_caption(
        caption="<b>⚔️ ESPREZZO MARKET – Модерация</b>\n\nВаше обращение находится на рассмотрении администраторов, ожидайте ⚙️",
        reply_markup=None
    )
    await state.clear()

@router.callback_query(ComplaintAction.filter())
async def complaint_moderation(callback: CallbackQuery, callback_data: ComplaintAction, bot: Bot, db: Database):
    if not await db.is_admin(callback.from_user.id) and not await db.is_moderator(callback.from_user.id):
        await callback.answer("Нет прав", show_alert=True)
        return
    action = callback_data.action
    reporter_id = callback_data.reporter_id
    complaint_id = callback_data.complaint_id

    if complaint_id not in complaint_storage:
        await callback.answer("Данные жалобы устарели.")
        return
    data = complaint_storage.pop(complaint_id)
    target_username = data["target_username"]
    game_nickname = data["game_nickname"]
    reason = data["reason"]

    if action == "approve":
        target_user = await db.get_user_by_username(target_username)
        target_uid = target_user[0] if target_user else None
        await db.add_scammer(game_nickname, target_username, target_uid, reporter_id, reason)
        try:
            await bot.send_message(reporter_id, f"✅ Ваша жалоба на @{target_username} одобрена. Пользователь добавлен в список мошенников.")
        except: pass
        await callback.message.edit_text(f"Жалоба на @{target_username} одобрена.")
    elif action == "reject":
        try:
            await bot.send_message(reporter_id, f"❌ Ваша жалоба на пользователя @{target_username} отклонена")
        except: pass
        await callback.message.edit_text(f"Жалоба на @{target_username} отклонена.")
    await callback.answer()