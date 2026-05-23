import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import MenuAction, TrackingAction, tracking_menu_kb, back_to_useful
from states import TrackingAdd
from config import IMAGES, CHANNEL_USERNAME

router = Router()

@router.callback_query(MenuAction.filter(F.action == "tracking"))
async def tracking_menu(callback: CallbackQuery, db: Database):
    keywords = await db.get_user_keywords(callback.from_user.id)
    txt = "<b>⚔️ ESPREZZO MARKET – Отслеживание</b>\n\n"
    if keywords:
        txt += "<b>Ключевые слова:</b>\n"
        for k in keywords:
            txt += f"– {k}\n"
    else:
        txt += "Нет активных ключевых слов."
    txt += "\nНавигационные кнопки ниже:"
    await callback.message.edit_caption(
        caption=txt,
        reply_markup=tracking_menu_kb()
    )
    await callback.answer()

@router.callback_query(TrackingAction.filter(F.action == "add"))
async def tracking_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption(
        caption="<b>⚔️ ESPREZZO MARKET – Отслеживание</b>\n\nВведите ключевое слово:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="tracking").pack())]
        ])
    )
    await state.set_state(TrackingAdd.waiting_for_keyword)
    await state.update_data(original_message_id=callback.message.message_id, chat_id=callback.message.chat.id)
    await callback.answer()

@router.message(TrackingAdd.waiting_for_keyword)
async def tracking_add_done(message: Message, state: FSMContext, db: Database, bot: Bot):
    kw = message.text.strip().lower()
    kw_clean = kw.replace(" ", "_")
    if not kw_clean:
        return
    await db.add_track_keyword(message.from_user.id, kw_clean)
    data = await state.get_data()
    msg_id = data.get("original_message_id")
    chat_id = data.get("chat_id")
    if msg_id and chat_id:
        keywords = await db.get_user_keywords(message.from_user.id)
        txt = "<b>⚔️ ESPREZZO MARKET – Отслеживание</b>\n\n"
        if keywords:
            txt += "<b>Ключевые слова:</b>\n"
            for k in keywords:
                txt += f"– {k}\n"
        else:
            txt += "Нет активных ключевых слов."
        txt += "\nНавигационные кнопки ниже:"
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=msg_id,
            caption=txt,
            reply_markup=tracking_menu_kb()
        )
    await state.clear()
    await message.delete()

@router.callback_query(TrackingAction.filter(F.action == "delete_menu"))
async def tracking_delete_menu(callback: CallbackQuery, db: Database):
    keywords = await db.get_user_keywords(callback.from_user.id)
    if not keywords:
        await callback.answer("Нет слов для удаления")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=k, callback_data=TrackingAction(action="delete", keyword=k).pack())] for k in keywords
    ] + [[InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="tracking").pack())]])
    await callback.message.edit_caption(
        caption="<b>⚔️ ESPREZZO MARKET – Отслеживание</b>\n\nВыберите слово для удаления:",
        reply_markup=kb
    )
    await callback.answer()

@router.callback_query(TrackingAction.filter(F.action == "delete"))
async def tracking_delete_exec(callback: CallbackQuery, callback_data: TrackingAction, db: Database):
    await db.remove_track_keyword(callback.from_user.id, callback_data.keyword)
    keywords = await db.get_user_keywords(callback.from_user.id)
    txt = "<b>⚔️ ESPREZZO MARKET – Отслеживание</b>\n\n"
    if keywords:
        txt += "<b>Ключевые слова:</b>\n"
        for k in keywords:
            txt += f"– {k}\n"
    else:
        txt += "Нет активных ключевых слов."
    txt += "\nНавигационные кнопки ниже:"
    await callback.message.edit_caption(caption=txt, reply_markup=tracking_menu_kb())
    await callback.answer()