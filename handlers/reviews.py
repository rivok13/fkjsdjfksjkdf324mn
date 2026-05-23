from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import MenuAction, ReviewAction, review_moderation_kb, back_to_main
from states import WriteReview, AskRating
from config import IMAGES, MODERATION_CHAT_ID

router = Router()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# Отзывы (оставлены из предыдущего кода)
@router.message(WriteReview.waiting_for_seller_username)
async def review_seller_entered(message: Message, state: FSMContext, db: Database):
    username = message.text.strip()
    seller = await db.get_user_by_username(username)
    if not seller:
        await message.answer("Продавец не найден.")
        return
    await state.update_data(seller_id=seller[0])
    await message.answer("Оцените от 1 до 5:")
    await state.set_state(WriteReview.waiting_for_rating)

@router.message(WriteReview.waiting_for_rating, F.text.regexp(r'^[1-5]$'))
async def review_rating(message: Message, state: FSMContext):
    await state.update_data(rating=int(message.text))
    await message.answer("Напишите комментарий:")
    await state.set_state(WriteReview.waiting_for_comment)

@router.message(WriteReview.waiting_for_comment)
async def review_comment(message: Message, state: FSMContext, db: Database, bot: Bot):
    data = await state.get_data()
    rid = await db.add_review(message.from_user.id, data['seller_id'], data['rating'], message.text)
    seller = await db.get_user(data['seller_id'])
    txt = f"🆕 Отзыв\nПродавец: @{escape_html(seller[2])}\nОценка: {data['rating']}/5\n{escape_html(message.text)}\nОт: {escape_html(message.from_user.full_name)}"
    try:
        await bot.send_message(MODERATION_CHAT_ID, txt, reply_markup=review_moderation_kb(rid))
    except: pass
    await message.answer("Отзыв отправлен на модерацию.")
    await state.clear()

@router.callback_query(ReviewAction.filter(F.action == "approve"))
async def approve_review(callback: CallbackQuery, callback_data: ReviewAction, db: Database):
    if not (callback.from_user.id in ADMIN_IDS or await db.is_moderator(callback.from_user.id)):
        return await callback.answer("Нет прав")
    await db.update_review_status(callback_data.review_id, 'approved')
    await callback.message.edit_text("✅ Отзыв одобрен")
    await callback.answer()

@router.callback_query(ReviewAction.filter(F.action == "reject"))
async def reject_review(callback: CallbackQuery, callback_data: ReviewAction, db: Database):
    if not (callback.from_user.id in ADMIN_IDS or await db.is_moderator(callback.from_user.id)):
        return await callback.answer("Нет прав")
    await db.update_review_status(callback_data.review_id, 'rejected', 'Нарушение')
    await callback.message.edit_text("❌ Отзыв отклонён")
    await callback.answer()

# Чужой рейтинг (вызывается через AskRating)
@router.message(AskRating.waiting_for_username)
async def ask_rating_username(message: Message, state: FSMContext, db: Database):
    username = message.text.strip()
    seller = await db.get_user_by_username(username)
    if not seller:
        await message.answer("Не найден.", reply_markup=back_to_main())
    else:
        avg, cnt = await db.get_seller_rating(seller[0])
        await message.answer(f"⭐ Рейтинг @{username}: {avg:.1f} ({cnt} отз.)", reply_markup=back_to_main())
    await state.clear()