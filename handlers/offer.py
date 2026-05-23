import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import (
    MenuAction, CategoryAction, categories_kb, seller_buyer_kb,
    moderation_kb, RUS_CATEGORIES
)
from states import NewOffer
from config import IMAGES, CATEGORY_TITLE_EXAMPLES, MODERATION_CHAT_ID

router = Router()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def parse_price(text: str) -> int:
    clean = text.replace(".", "").replace(",", "").replace(" ", "")
    if clean.isdigit():
        return int(clean)
    return 0

@router.callback_query(MenuAction.filter(F.action.in_(["sell", "buy"])))
async def seller_buyer(callback: CallbackQuery, callback_data: MenuAction, state: FSMContext):
    if callback_data.action == "sell":
        await state.update_data(is_seller=True)
    elif callback_data.action == "buy":
        await state.update_data(is_seller=False)
    text = "<b>⚔️ ESPREZZO MARKET – Категория объявления</b>\n\nВам необходимо выбрать категорию, которая будет соответствовать вашему объявлению"
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["category"], caption=text), reply_markup=categories_kb())
    await callback.answer()

@router.callback_query(CategoryAction.filter())
async def category_chosen(callback: CallbackQuery, callback_data: CategoryAction, state: FSMContext):
    cat = callback_data.category
    await state.update_data(category=cat)
    example = CATEGORY_TITLE_EXAMPLES.get(cat, "Товар")
    text = f"<b>⚔️ ESPREZZO MARKET – Введите заголовок</b>\n\nВведите заголовок объявления, например: «{example}»"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="seller_buyer").pack())]
    ])
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["title_input"], caption=text), reply_markup=kb)
    await state.set_state(NewOffer.entering_title)
    await callback.answer()

@router.message(NewOffer.entering_title)
async def title_entered(message: Message, state: FSMContext):
    title = message.text.strip()
    if not title:
        await message.answer("Заголовок не может быть пустым. Введите ещё раз:")
        return
    await state.update_data(title=title)
    text = "<b>⚔️ ESPREZZO MARKET – Введите описание</b>\n\nВведите описание объявления:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_title").pack())]
    ])
    await message.answer_photo(IMAGES["description"], caption=text, reply_markup=kb)
    await state.set_state(NewOffer.entering_text)

@router.callback_query(MenuAction.filter(F.action == "back_to_title"))
async def back_to_title(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cat = data.get("category", "")
    example = CATEGORY_TITLE_EXAMPLES.get(cat, "Товар")
    text = f"<b>⚔️ ESPREZZO MARKET – Введите заголовок</b>\n\nВведите заголовок объявления, например: «{example}»"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="seller_buyer").pack())]
    ])
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["title_input"], caption=text), reply_markup=kb)
    await state.set_state(NewOffer.entering_title)
    await callback.answer()

@router.message(NewOffer.entering_text)
async def offer_text_entered(message: Message, state: FSMContext):
    await state.update_data(text=message.text)
    data = await state.get_data()
    is_seller = data.get("is_seller", True)
    if is_seller:
        text = "<b>⚔️ ESPREZZO MARKET – Введите стоимость</b>\n\nВведите стоимость в формате: 1.000.000\nИли отправьте «Договорная»"
        img = IMAGES["price_input"]
    else:
        text = "<b>⚔️ ESPREZZO MARKET – Введите бюджет</b>\n\nВведите бюджет в формате: 1.000.000\nИли отправьте «Договорной»"
        img = IMAGES["budget_input"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_text").pack())]
    ])
    await message.answer_photo(img, caption=text, reply_markup=kb)
    await state.set_state(NewOffer.entering_price)

@router.callback_query(MenuAction.filter(F.action == "back_to_text"))
async def back_to_text(callback: CallbackQuery, state: FSMContext):
    text = "<b>⚔️ ESPREZZO MARKET – Введите описание</b>\n\nВведите описание объявления:"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_title").pack())]
    ])
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["description"], caption=text), reply_markup=kb)
    await state.set_state(NewOffer.entering_text)
    await callback.answer()

@router.message(NewOffer.entering_price)
async def price_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    raw = message.text.strip()
    if raw.lower() in ["договорная", "договорной", "договорная цена", "договорной бюджет"]:
        await state.update_data(price=0, price_type="negotiable")
    else:
        price = parse_price(raw)
        if price <= 0:
            await message.answer("⚠️ Введено некорректное значение. Стоимость должна быть положительной с использованием разделительных точек\n\nПример: 1.000.000")
            return
        await state.update_data(price=price, price_type="fixed")
    text = "<b>⚔️ ESPREZZO MARKET – Прикрепите изображение</b>\n\nПрикреплено изображений: 0 / 5"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Далее →", callback_data=MenuAction(action="finish_offer").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_price").pack())]
    ])
    msg = await message.answer_photo(IMAGES["photo_upload"], caption=text, reply_markup=kb)
    await state.update_data(media=[], media_msg_id=msg.message_id, media_chat_id=msg.chat.id)
    await state.set_state(NewOffer.uploading_media)

@router.callback_query(MenuAction.filter(F.action == "back_to_price"))
async def back_to_price(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_seller = data.get("is_seller", True)
    if is_seller:
        text = "<b>⚔️ ESPREZZO MARKET – Введите стоимость</b>\n\nВведите стоимость в формате: 1.000.000\nИли отправьте «Договорная»"
        img = IMAGES["price_input"]
    else:
        text = "<b>⚔️ ESPREZZO MARKET – Введите бюджет</b>\n\nВведите бюджет в формате: 1.000.000\nИли отправьте «Договорной»"
        img = IMAGES["budget_input"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_text").pack())]
    ])
    await callback.message.edit_media(InputMediaPhoto(media=img, caption=text), reply_markup=kb)
    await state.set_state(NewOffer.entering_price)
    await callback.answer()

@router.message(NewOffer.uploading_media, F.photo)
async def offer_photo(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    media = data.get("media", [])
    if len(media) >= 5:
        await message.answer("Достигнут лимит в 5 фото. Нажмите «Далее» для продолжения.",
                             reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                 [InlineKeyboardButton(text="Далее →", callback_data=MenuAction(action="finish_offer").pack())]
                             ]))
        return
    media.append(message.photo[-1].file_id)
    await state.update_data(media=media)
    msg_id = data.get("media_msg_id")
    chat_id = data.get("media_chat_id")
    if msg_id and chat_id:
        new_caption = f"<b>⚔️ ESPREZZO MARKET – Прикрепите изображение</b>\n\nПрикреплено изображений: {len(media)} / 5"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Далее →", callback_data=MenuAction(action="finish_offer").pack())],
            [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="back_to_price").pack())]
        ])
        try:
            await bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=new_caption, reply_markup=kb)
        except Exception as e:
            logging.error(f"Ошибка редактирования caption: {e}")
    try:
        await message.delete()
    except:
        pass

@router.callback_query(MenuAction.filter(F.action == "finish_offer"))
async def finish_offer(callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    if "game_nickname" in data:
        return
    if not data:
        await callback.message.answer("Ошибка: начните заново через /start")
        return
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала завершите регистрацию.")
        return

    title = data.get("title", "")
    text = data.get("text", "")
    full_text = f"{title} {text}".lower()
    has_filter, word = await db.check_filter_words(full_text)
    if has_filter:
        await callback.message.edit_caption(
            caption=f"❌ Ваше объявление автоматически отклонено.\nНайдено запрещенное слово: «{word}»",
            reply_markup=None
        )
        await state.clear()
        return

    price = data.get("price", 0)
    price_type = data.get("price_type", "fixed")
    is_seller = data.get("is_seller", True)
    category = data.get("category")
    offer_id = await db.add_offer(callback.from_user.id, category, title, text, price, price_type, is_seller)
    for fid in data.get("media", []):
        await db.add_media(offer_id, fid)

    safe_username = escape_html(f"@{user[2]}")
    safe_title = escape_html(title)
    safe_text = escape_html(text)
    rus_cat = RUS_CATEGORIES.get(category, category)
    type_str = "Продам" if is_seller else "Куплю"
    price_str = f"{price:,}".replace(",", ".") if price_type == 'fixed' else ("Договорная" if is_seller else "Договорной")
    msg_mod = (
        f"📢 Новое объявление\n\n"
        f"{type_str}: {safe_title}\n"
        f"Подробнее: {safe_text}\n"
        f"{'Стоимость' if is_seller else 'Бюджет'}: {price_str}\n\n"
        f"От: {safe_username}"
    )
    kb = moderation_kb(offer_id)
    try:
        media_files = data.get("media", [])
        if media_files:
            await bot.send_photo(MODERATION_CHAT_ID, media_files[0], caption=msg_mod, reply_markup=kb)
            if len(media_files) > 1:
                group = [InputMediaPhoto(media=fid) for fid in media_files[1:]]
                await bot.send_media_group(MODERATION_CHAT_ID, group)
        else:
            await bot.send_message(MODERATION_CHAT_ID, msg_mod, reply_markup=kb)
    except Exception as e:
        logging.error(f"Ошибка отправки в модерацию: {e}")
        await callback.answer("Ошибка отправки модераторам", show_alert=True)
        return

    await callback.message.edit_caption(
        caption="<b>⚔️ ESPREZZO MARKET – Модерация</b>\n\nВаше объявление находится на рассмотрении администраторов, ожидайте ⚙️",
        reply_markup=None
    )
    await state.clear()