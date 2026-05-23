from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InputMediaPhoto
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards import main_menu, MenuAction, seller_buyer_kb, categories_kb, useful_kb
from states import RegisterContact, AskRating, WriteReview
from config import IMAGES

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db: Database):
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer_photo(
            IMAGES["username_input"],
            caption="<b>⚔️ ESPREZZO MARKET – Регистрация</b>\n\nВведите ваш Telegram username (без @):"
        )
        await state.set_state(RegisterContact.waiting_for_username)
    else:
        # Проверка бана (если забанен и не админ/модер)
        if user[4] == 1 and not await db.is_admin(message.from_user.id) and not await db.is_moderator(message.from_user.id):
            await message.answer(f"⚠️ {user[2]}, вы были заблокированы в данном боте навсегда")
            return
        is_admin = await db.is_admin(message.from_user.id)
        text = (
            "<b>⚔️ Добро пожаловать в ESPREZZO MARKET</b>\n\n"
            "Вы можете отправить свое предложение, после\n"
            "детальной проверки мы разместим ваше объявление"
        )
        await message.answer_photo(IMAGES["start"], caption=text, reply_markup=main_menu(is_admin))

@router.message(RegisterContact.waiting_for_username, F.text)
async def register_contact(message: Message, state: FSMContext, db: Database):
    username = message.text.strip().lstrip('@')
    if not username:
        await message.answer("Введи корректный username")
        return
    success = await db.add_user(message.from_user.id, message.from_user.username, username)
    if not success:
        await message.answer("Этот username уже занят другим пользователем. Выберите другой.")
        return
    is_admin = await db.is_admin(message.from_user.id)
    text = (
        "<b>⚔️ Добро пожаловать в ESPREZZO MARKET</b>\n\n"
        "Вы можете отправить свое предложение, после\n"
        "детальной проверки мы разместим ваше объявление"
    )
    await message.answer_photo(IMAGES["start"], caption=text, reply_markup=main_menu(is_admin))
    await state.clear()

EXCLUDED_ACTIONS = [
    "finish_offer", "finish_complaint",
    "back_to_title", "back_to_text", "back_to_price",
    "back_to_description"
]

@router.callback_query(MenuAction.filter(~F.action.in_(EXCLUDED_ACTIONS)))
async def menu_handler(callback: CallbackQuery, callback_data: MenuAction, state: FSMContext, db: Database):
    action = callback_data.action
    is_admin = await db.is_admin(callback.from_user.id)

    if action == "main_menu":
        text = (
            "<b>⚔️ Добро пожаловать в ESPREZZO MARKET</b>\n\n"
            "Вы можете отправить свое предложение, после\n"
            "детальной проверки мы разместим ваше объявление"
        )
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["start"], caption=text), reply_markup=main_menu(is_admin))
    elif action == "seller_buyer":
        text = "<b>⚔️ ESPREZZO MARKET – Тип объявления</b>\n\nВыберите, кто вы:"
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["category"], caption=text), reply_markup=seller_buyer_kb())
    elif action == "sell":
        await state.update_data(is_seller=True)
        text = "<b>⚔️ ESPREZZO MARKET – Категория объявления</b>\n\nВам необходимо выбрать категорию, которая будет соответствовать вашему объявлению"
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["category"], caption=text), reply_markup=categories_kb())
    elif action == "buy":
        await state.update_data(is_seller=False)
        text = "<b>⚔️ ESPREZZO MARKET – Категория объявления</b>\n\nВам необходимо выбрать категорию, которая будет соответствовать вашему объявлению"
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["category"], caption=text), reply_markup=categories_kb())
    elif action == "top":
        from handlers.ratings import show_top
        await show_top(callback, db)
        return
    elif action == "profile":
        from handlers.ratings import show_profile
        await show_profile(callback, db)
        return
    elif action == "useful":
        txt = "<b>⚔️ ESPREZZO MARKET – Полезное</b>\n\nВыберите нужный раздел:"
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["useful"], caption=txt), reply_markup=useful_kb())
    elif action == "tracking":
        from handlers.tracking import tracking_menu
        await tracking_menu(callback, db)
        return
    elif action == "avg_prices":
        from handlers.avg_price import avg_price_start
        await avg_price_start(callback, state)
        return
    elif action == "scam_base":
        from handlers.scammers import show_scammers_page
        await show_scammers_page(callback, db, 0)
        return
    elif action == "complaint":
        from handlers.scammers import complaint_start
        await complaint_start(callback, state)
        return
    elif action == "ask_rating":
        await callback.message.answer_photo(IMAGES["username_input"], caption="Введите username продавца (без @):")
        await state.set_state(AskRating.waiting_for_username)
    elif action == "review":
        await callback.message.answer_photo(IMAGES["username_input"], caption="Введите username продавца для отзыва (без @):")
        await state.set_state(WriteReview.waiting_for_seller_username)
    elif action == "admin_panel":
        if not is_admin:
            await callback.answer("Нет доступа", show_alert=True)
            return
        from keyboards import admin_panel_kb
        await callback.message.edit_media(InputMediaPhoto(media=IMAGES["admin_panel"], caption="<b>Админ-панель</b>"), reply_markup=admin_panel_kb())
    await callback.answer()