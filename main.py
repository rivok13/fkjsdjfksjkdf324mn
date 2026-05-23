import asyncio, logging
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand, Message, CallbackQuery
from database import Database
from config import BOT_TOKEN, ADMIN_IDS
from states import RegisterContact  # импорт состояния регистрации

from handlers import (
    common, offer, moderation, admin, scammers,
    tracking, ratings, reviews, avg_price
)

class UsernameMiddleware(BaseMiddleware):
    """Если у пользователя удалён contact_username, возвращает его к регистрации."""
    async def __call__(self, handler, event, data):
        db: Database = data.get('db')
        if not db:
            return await handler(event, data)

        user_id = event.from_user.id
        user = await db.get_user(user_id)

        # Если пользователь существует, но username отсутствует или пуст
        if user and (not user[2] or user[2].strip() == ''):
            # Пропускаем только состояние регистрации
            state: FSMContext = data.get('state')
            if state:
                current_state = await state.get_state()
                if current_state == RegisterContact.waiting_for_username:
                    return await handler(event, data)

            # Принудительно переводим в регистрацию
            text = "Ваш username был сброшен администратором. Пожалуйста, введите новый username (без @):"
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=True)
                # Отправляем сообщение с запросом username
                await event.message.answer(text)
            elif isinstance(event, Message):
                await event.answer(text)
            # Устанавливаем состояние
            if state:
                await state.set_state(RegisterContact.waiting_for_username)
            return  # Не передаём управление дальше

        return await handler(event, data)

class BanMiddleware(BaseMiddleware):
    """Проверяет, не заблокирован ли пользователь."""
    async def __call__(self, handler, event, data):
        db: Database = data.get('db')
        if not db:
            return await handler(event, data)

        user_id = event.from_user.id
        user = await db.get_user(user_id)

        if user and user[4] == 1:  # is_banned
            if not await db.is_admin(user_id) and not await db.is_moderator(user_id):
                nickname = user[2] if user[2] else f"id{user_id}"
                text = f"⚠️ {nickname}, вы были заблокированы в данном боте навсегда"
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                elif isinstance(event, Message):
                    await event.answer(text)
                return
        return await handler(event, data)

async def on_startup(bot: Bot, db: Database):
    await db.connect()
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню")
    ])
    for uid in ADMIN_IDS:
        if not await db.get_user(uid):
            await db.add_user(uid, "admin", "admin")

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    db = Database()

    # Порядок Middleware: сначала проверяем username, потом бан
    dp.message.middleware(UsernameMiddleware())
    dp.callback_query.middleware(UsernameMiddleware())

    dp.message.middleware(BanMiddleware())
    dp.callback_query.middleware(BanMiddleware())

    class DbBotMiddleware(BaseMiddleware):
        async def __call__(self, handler, event, data):
            data['db'] = db
            data['bot'] = bot
            return await handler(event, data)

    dp.update.middleware(DbBotMiddleware())

    dp.include_router(common.router)
    dp.include_router(offer.router)
    dp.include_router(moderation.router)
    dp.include_router(admin.router)
    dp.include_router(scammers.router)
    dp.include_router(tracking.router)
    dp.include_router(ratings.router)
    dp.include_router(reviews.router)
    dp.include_router(avg_price.router)

    await on_startup(bot, db)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())