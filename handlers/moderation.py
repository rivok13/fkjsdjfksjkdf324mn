import logging
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from database import Database
from keyboards import OfferAction, RejectReason, reject_reasons_kb, moderation_kb, MenuAction, RUS_CATEGORIES
from config import CHANNEL_ID, CHANNEL_USERNAME

router = Router()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def get_post_link(message_id: int) -> str:
    return f"https://t.me/{CHANNEL_USERNAME}/{message_id}"

@router.callback_query(OfferAction.filter(F.action == "publish"))
async def publish_offer(callback: CallbackQuery, callback_data: OfferAction, db: Database, bot: Bot):
    if not await db.is_admin(callback.from_user.id) and not await db.is_moderator(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    offer = await db.get_offer(callback_data.offer_id)
    if not offer: return await callback.answer("Не найдено")
    user = await db.get_user(offer['user_id'])
    safe_title = escape_html(offer['title'])
    safe_text = escape_html(offer['text'])
    rus_cat = RUS_CATEGORIES.get(offer['category'], offer['category'])
    is_seller = offer['is_seller']
    price_type = offer['price_type']
    price = offer['price']

    if is_seller:
        price_str = f"{price:,}".replace(",", ".") if price_type == 'fixed' else "Договорная"
    else:
        price_str = f"{price:,}".replace(",", ".") if price_type == 'fixed' else "Договорной"

    type_str = "Продам" if is_seller else "Куплю"
    cost_label = "Стоимость" if is_seller else "Бюджет"

    post_text = (
        f"<b>Категория:</b> {rus_cat}\n\n"
        f"<b>{type_str}:</b> {safe_title}\n"
        f"<b>Подробнее:</b> {safe_text}\n\n"
        f"<b>{cost_label}:</b> {price_str}\n\n"
        f"<blockquote>Предложение: t.me/esprezzomarket_bot</blockquote>"
    )
    contact_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Написать", url=f"https://t.me/{user[2]}")]
    ])
    try:
        if offer['media_files']:
            media_group = [InputMediaPhoto(media=fid, caption=post_text if i == 0 else None, parse_mode="HTML")
                           for i, fid in enumerate(offer['media_files'])]
            msgs = await bot.send_media_group(CHANNEL_ID, media_group)
            await bot.send_message(CHANNEL_ID, "Связь с продавцом:", reply_markup=contact_btn)
            msg_id = msgs[0].message_id
        else:
            msg = await bot.send_message(CHANNEL_ID, post_text, reply_markup=contact_btn)
            msg_id = msg.message_id
        await db.update_offer_status(offer['id'], 'approved', channel_message_id=msg_id, moderator_id=callback.from_user.id)
        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply("✅ Опубликовано")

        post_link = get_post_link(msg_id)
        try:
            await bot.send_message(
                offer['user_id'],
                f"✅ Ваше объявление «{safe_title}» опубликовано",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Перейти", url=post_link)],
                    [InlineKeyboardButton(text="Главное меню", callback_data=MenuAction(action="main_menu").pack())]
                ])
            )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление автору: {e}")

        trackings = await db.get_all_trackings()
        for uid, keyword in trackings:
            if keyword.lower() in offer['title'].lower() or keyword.lower() in offer['text'].lower():
                try:
                    await bot.send_message(
                        uid,
                        f"🔔 Появилось объявление по ключевому слову «{keyword}»:\n{offer['title'][:200]}",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="Перейти", url=post_link)]
                        ])
                    )
                except: pass
    except Exception as e:
        logging.error(f"Ошибка публикации: {e}")
        await callback.answer("Ошибка публикации", show_alert=True)
    await callback.answer()

@router.callback_query(OfferAction.filter(F.action == "reject"))
async def reject_offer(callback: CallbackQuery, callback_data: OfferAction, db: Database):
    if not await db.is_admin(callback.from_user.id) and not await db.is_moderator(callback.from_user.id):
        return await callback.answer("Нет прав")
    await callback.message.edit_reply_markup(reply_markup=reject_reasons_kb(callback_data.offer_id))
    await callback.answer()

@router.callback_query(RejectReason.filter())
async def reject_reason(callback: CallbackQuery, callback_data: RejectReason, db: Database, bot: Bot):
    offer = await db.get_offer(callback_data.offer_id)
    if not offer: return await callback.answer("Не найдено")
    reason_codes = {
        "wrong_category": "Неверная категория",
        "bad_description": "Плохое описание",
        "no_price": "Нет стоимости",
        "other": "Другое",
        "wrong_username": "Неправильный username"
    }
    reason_text = reason_codes.get(callback_data.reason, callback_data.reason)
    await db.update_offer_status(callback_data.offer_id, 'rejected', rejection_reason=reason_text)
    try:
        await bot.send_message(
            offer['user_id'],
            f"❌ Ваше объявление «{escape_html(offer['title'])}» отклонено\n\nПричина: {reason_text}"
        )
    except: pass
    await callback.message.edit_text("❌ Отклонено")
    await callback.answer()

@router.callback_query(OfferAction.filter(F.action == "cancel_reject"))
async def cancel_reject(callback: CallbackQuery, callback_data: OfferAction, db: Database):
    offer = await db.get_offer(callback_data.offer_id)
    if offer:
        await callback.message.edit_reply_markup(reply_markup=moderation_kb(callback_data.offer_id))
    await callback.answer()