import re, logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import AdminAction, admin_panel_kb, filter_words_kb, manage_admins_kb, MenuAction
from states import (
    AdminBan, AdminUnban, AdminDeleteOffers, AdminAddScammer,
    AdminManageAdmins, AdminFilterWords, AdminPinOffer
)
from config import CHANNEL_ID, MODERATION_CHAT_ID, IMAGES

router = Router()

async def safe_edit_message(callback: CallbackQuery, text: str, reply_markup=None):
    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=reply_markup)
    else:
        await callback.message.edit_text(text=text, reply_markup=reply_markup)

@router.callback_query(MenuAction.filter(F.action == "admin_panel"))
async def admin_panel(callback: CallbackQuery, db: Database):
    if not await db.is_admin(callback.from_user.id):
        await callback.answer("Нет доступа")
        return
    await safe_edit_message(callback, "<b>Админ-панель</b>", reply_markup=admin_panel_kb())
    await callback.answer()

# --- Бан ---
@router.callback_query(AdminAction.filter(F.action == "ban_user"))
async def ban_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для блокировки:")
    await state.set_state(AdminBan.waiting_for_user_id)
    await callback.answer()

@router.message(AdminBan.waiting_for_user_id)
async def ban_user_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text)
    except:
        await message.answer("Некорректный ID")
        return
    await state.update_data(ban_uid=uid)
    await message.answer("Введите причину блокировки:")
    await state.set_state(AdminBan.waiting_for_reason)

@router.message(AdminBan.waiting_for_reason)
async def ban_user_reason(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    uid = data['ban_uid']
    reason = message.text
    if await db.is_owner(uid):
        await message.answer("Невозможно заблокировать владельца.")
        await state.clear()
        return
    success = await db.ban_user(uid, reason, 'permanent')
    if success:
        await message.answer(f"Пользователь {uid} заблокирован.")
    else:
        await message.answer("Ошибка при блокировке.")
    await state.clear()

# --- Разбан ---
@router.callback_query(AdminAction.filter(F.action == "unban_user"))
async def unban_user_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для разблокировки:")
    await state.set_state(AdminUnban.waiting_for_user_id)
    await callback.answer()

@router.message(AdminUnban.waiting_for_user_id)
async def unban_user_id(message: Message, state: FSMContext, db: Database):
    try:
        uid = int(message.text)
    except:
        await message.answer("Некорректный ID")
        return
    await db.unban_user(uid)
    await message.answer(f"Пользователь {uid} разблокирован.")
    await state.clear()

# --- Удаление объявлений ---
@router.callback_query(AdminAction.filter(F.action == "delete_offers"))
async def delete_offers_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите количество дней (1, 7, 30):")
    await state.set_state(AdminDeleteOffers.waiting_for_days)
    await callback.answer()

@router.message(AdminDeleteOffers.waiting_for_days)
async def delete_offers_days(message: Message, state: FSMContext, db: Database):
    try:
        days = int(message.text)
        if days not in [1, 7, 30]:
            raise ValueError
    except:
        await message.answer("Некорректное число. Допустимо 1, 7, 30.")
        return
    await db.delete_offers_last_days(days)
    await message.answer(f"Объявления за последние {days} дн. удалены.")
    await state.clear()

# --- Добавить мошенника ---
@router.callback_query(AdminAction.filter(F.action == "add_scammer"))
async def add_scammer_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите игровой никнейм:")
    await state.set_state(AdminAddScammer.waiting_for_game_nickname)
    await callback.answer()

@router.message(AdminAddScammer.waiting_for_game_nickname)
async def add_scammer_nick(message: Message, state: FSMContext):
    await state.update_data(game_nickname=message.text)
    await message.answer("Введите username (без @):")
    await state.set_state(AdminAddScammer.waiting_for_username)

@router.message(AdminAddScammer.waiting_for_username)
async def add_scammer_username(message: Message, state: FSMContext):
    await state.update_data(contact_username=message.text.lstrip('@'))
    await message.answer("Введите причину:")
    await state.set_state(AdminAddScammer.waiting_for_reason)

@router.message(AdminAddScammer.waiting_for_reason)
async def add_scammer_reason(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    game_nickname = data['game_nickname']
    contact_username = data['contact_username']
    reason = message.text
    target_user = await db.get_user_by_username(contact_username)
    uid = target_user[0] if target_user else None
    await db.add_scammer(game_nickname, contact_username, uid, message.from_user.id, reason)
    await message.answer("Мошенник добавлен в базу.")
    await state.clear()

# --- Управление администраторами ---
@router.callback_query(AdminAction.filter(F.action == "manage_admins"))
async def manage_admins(callback: CallbackQuery, db: Database):
    admins = await db.get_all_admins()
    text = "<b>⚙️ Список администраторов:</b>\n\n"
    for i, (uid, contact, level) in enumerate(admins, 1):
        role = "Владелец" if level == 2 else "Администратор"
        text += f"[{i:02d}] @{contact} – {role}\n"
    await safe_edit_message(callback, text, reply_markup=manage_admins_kb())
    await callback.answer()

@router.callback_query(AdminAction.filter(F.action == "add_admin"))
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для добавления в администраторы:")
    await state.set_state(AdminManageAdmins.waiting_for_user_id)
    await state.update_data(action="add")
    await callback.answer()

@router.callback_query(AdminAction.filter(F.action == "remove_admin"))
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ID пользователя для снятия прав администратора:")
    await state.set_state(AdminManageAdmins.waiting_for_user_id)
    await state.update_data(action="remove")
    await callback.answer()

@router.callback_query(AdminAction.filter(F.action == "clear_username"))
async def clear_username_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите username (без @), который нужно освободить:")
    await state.set_state(AdminManageAdmins.waiting_for_user_id)
    await state.update_data(action="clear")
    await callback.answer()

@router.message(AdminManageAdmins.waiting_for_user_id, F.text)
async def process_admin_manage(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    action = data.get("action")
    if action == "add":
        try:
            uid = int(message.text)
        except:
            await message.answer("Некорректный ID")
            return
        success = await db.make_admin(uid)
        if success:
            await message.answer(f"Пользователь {uid} назначен администратором.")
        else:
            await message.answer("Не удалось назначить администратора (возможно, это владелец).")
        await state.clear()
    elif action == "remove":
        try:
            uid = int(message.text)
        except:
            await message.answer("Некорректный ID")
            return
        success = await db.remove_admin(uid)
        if success:
            await message.answer(f"Пользователь {uid} снят с администрирования.")
        else:
            await message.answer("Не удалось снять администратора (возможно, это владелец).")
        await state.clear()
    elif action == "clear":
        username = message.text.strip().lstrip('@')
        await db.clear_username(username)
        await message.answer(f"Username @{username} освобождён.")
        await state.clear()
    else:
        await message.answer("Неизвестное действие.")
        await state.clear()

# --- Фильтр слов ---
@router.callback_query(AdminAction.filter(F.action == "filter_words"))
async def filter_words_menu(callback: CallbackQuery):
    await safe_edit_message(callback, "Управление фильтр-словами:", reply_markup=filter_words_kb())
    await callback.answer()

@router.callback_query(AdminAction.filter(F.action == "add_filter_word"))
async def add_filter_word_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите слово для добавления в фильтр:")
    await state.set_state(AdminFilterWords.waiting_for_word)
    await state.update_data(filter_action="add")
    await callback.answer()

@router.callback_query(AdminAction.filter(F.action == "remove_filter_word"))
async def remove_filter_word_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите слово для удаления из фильтра:")
    await state.set_state(AdminFilterWords.waiting_for_word)
    await state.update_data(filter_action="remove")
    await callback.answer()

@router.message(AdminFilterWords.waiting_for_word)
async def filter_word_entered(message: Message, state: FSMContext, db: Database):
    action = (await state.get_data()).get("filter_action")
    word = message.text.strip().lower()
    if action == "add":
        await db.add_filter_word(word)
        await message.answer(f"Слово «{word}» добавлено в фильтр.")
    elif action == "remove":
        await db.remove_filter_word(word)
        await message.answer(f"Слово «{word}» удалено из фильтра.")
    await state.clear()

# --- Закрепить объявление ---
@router.callback_query(AdminAction.filter(F.action == "pin_offer"))
async def pin_offer_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите ссылку на объявление (например, https://t.me/esprezzomarket/243):")
    await state.set_state(AdminPinOffer.waiting_for_offer_id)
    await callback.answer()

@router.message(AdminPinOffer.waiting_for_offer_id)
async def pin_offer_id(message: Message, state: FSMContext):
    link = message.text.strip()
    match = re.search(r'/(\d+)$', link)
    if not match:
        await message.answer("Некорректная ссылка. Ожидается формат https://t.me/.../123")
        return
    msg_id = int(match.group(1))
    await state.update_data(pin_msg_id=msg_id)
    await message.answer("Введите количество дней (1, 7, 14, 30):")
    await state.set_state(AdminPinOffer.waiting_for_duration)

@router.message(AdminPinOffer.waiting_for_duration)
async def pin_offer_duration(message: Message, state: FSMContext, db: Database, bot: Bot):
    try:
        days = int(message.text)
        if days not in [1, 7, 14, 30]:
            raise ValueError
    except:
        await message.answer("Некорректное число. Допустимо 1, 7, 14, 30.")
        return
    data = await state.get_data()
    msg_id = data['pin_msg_id']
    try:
        await bot.pin_chat_message(CHANNEL_ID, msg_id)
        await db.pin_offer_by_message_id(msg_id, days)
        await message.answer(f"Объявление закреплено на {days} дн.")
    except Exception as e:
        logging.error(f"Ошибка закрепления: {e}")
        await message.answer(f"Не удалось закрепить: {e}")
    await state.clear()