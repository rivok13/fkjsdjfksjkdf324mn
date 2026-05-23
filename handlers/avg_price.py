from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import MenuAction, back_to_useful
from states import AvgPrice
from config import IMAGES

router = Router()

def escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

@router.callback_query(MenuAction.filter(F.action == "avg_prices"))
async def avg_price_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_media(
        InputMediaPhoto(media=IMAGES["keyword_input"], caption="<b>Введите название товара или ключевое слово:</b>"),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="useful").pack())]
        ])
    )
    await state.set_state(AvgPrice.waiting_for_keyword)
    await callback.answer()

@router.message(AvgPrice.waiting_for_keyword)
async def avg_price_keyword(message: Message, state: FSMContext, db: Database):
    keyword = message.text.strip()
    if not keyword:
        await message.answer("Введите непустое ключевое слово:")
        return
    avg, count = await db.get_average_price_by_keyword(keyword)
    if count == 0:
        txt = f"💵 Нет средней стоимости для товара «{escape_html(keyword)}». Проверьте, правильно ли вы ввели ключевое слово, и что объявления прошли модерацию."
    elif count < 3:
        txt = f"💵 Нет средней стоимости для товара «{escape_html(keyword)}». Средняя стоимость для данного товара находится на стадии формирования (одобрено менее 3 объявлений)."
    else:
        txt = f"<b>Средняя цена по запросу «{escape_html(keyword)}»:</b> {avg:,.0f} руб."
    await message.answer(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="useful").pack())]
    ]))
    # Состояние сохраняется для возможности повторного ввода