from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto
from database import Database
from keyboards import MenuAction, back_to_main, profile_kb
from config import IMAGES

router = Router()

async def show_top(callback: CallbackQuery, db: Database):
    top = await db.get_top_sellers_by_offers(5)
    if not top:
        txt = "<b>🏆 ESPREZZO MARKET – Рейтинг продавцов</b>\n\nРейтинг в данный момент находится на стадии формирования"
    else:
        txt = "<b>🏆 Рейтинг:</b>\n\n"
        for i, (_, contact, cnt) in enumerate(top, 1):
            username = contact if contact else "—"
            txt += f"[{i:02d}] @{username} – Количество объявлений: {cnt}\n\n"
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["rating"], caption=txt), reply_markup=back_to_main())
    await callback.answer()

async def show_profile(callback: CallbackQuery, db: Database):
    user = await db.get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала зарегистрируйтесь /start")
        return
    contact = user[2] if user[2] else "—"
    offers_cnt = await db.get_user_offers_count(callback.from_user.id)
    rank = await db.get_user_rank(callback.from_user.id)
    txt = (
        f"<b>⚔️ ESPREZZO MARKET – Мой профиль</b>\n\n"
        f"<b>Ваш ID:</b> {callback.from_user.id}\n"
        f"<b>Ваш username:</b> @{contact}\n\n"
        f"<b>Всего объявлений:</b> {offers_cnt}"
    )
    if rank:
        txt += f"\n<b>Место в общем рейтинге:</b> {rank}"
    else:
        txt += "\n<b>Место в общем рейтинге:</b> —"
    await callback.message.edit_media(InputMediaPhoto(media=IMAGES["profile"], caption=txt), reply_markup=profile_kb())
    await callback.answer()

@router.callback_query(MenuAction.filter(F.action == "top"))
async def top_handler(callback: CallbackQuery, db: Database):
    await show_top(callback, db)

@router.callback_query(MenuAction.filter(F.action == "profile"))
async def profile_handler(callback: CallbackQuery, db: Database):
    await show_profile(callback, db)