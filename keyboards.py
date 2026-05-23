from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters.callback_data import CallbackData

class MenuAction(CallbackData, prefix="menu"):
    action: str

class OfferAction(CallbackData, prefix="offer"):
    action: str
    offer_id: int

class RejectReason(CallbackData, prefix="rej"):
    reason: str
    offer_id: int

class ReviewAction(CallbackData, prefix="rev"):
    action: str
    review_id: int

class CategoryAction(CallbackData, prefix="cat"):
    category: str

class TrackingAction(CallbackData, prefix="track"):
    action: str
    keyword: str = ""

class ComplaintAction(CallbackData, prefix="complaint"):
    action: str
    reporter_id: int
    complaint_id: str

class ScammersPageAction(CallbackData, prefix="scampage"):
    page: int

class AdminAction(CallbackData, prefix="admin"):
    action: str

def main_menu(is_admin=False):
    buttons = [
        [InlineKeyboardButton(text="Создать объявление", callback_data=MenuAction(action="seller_buyer").pack())],
        [
            InlineKeyboardButton(text="Рейтинг", callback_data=MenuAction(action="top").pack()),
            InlineKeyboardButton(text="Профиль", callback_data=MenuAction(action="profile").pack())
        ],
        [
            InlineKeyboardButton(text="Полезное", callback_data=MenuAction(action="useful").pack()),
            InlineKeyboardButton(text="Мошенники", callback_data=MenuAction(action="scam_base").pack())
        ]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="Админ-панель", callback_data=MenuAction(action="admin_panel").pack())])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def seller_buyer_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Продаю", callback_data=MenuAction(action="sell").pack()),
         InlineKeyboardButton(text="Приобретаю", callback_data=MenuAction(action="buy").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())]
    ])

RUS_CATEGORIES = {
    "transport": "Транспорт",
    "realty": "Недвижимость",
    "business": "Бизнес",
    "accessories": "Аксессуары",
    "skins": "Скины"
}

def categories_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Транспорт", callback_data=CategoryAction(category="transport").pack()),
            InlineKeyboardButton(text="Недвижимость", callback_data=CategoryAction(category="realty").pack())
        ],
        [
            InlineKeyboardButton(text="Бизнес", callback_data=CategoryAction(category="business").pack()),
            InlineKeyboardButton(text="Аксессуары", callback_data=CategoryAction(category="accessories").pack())
        ],
        [
            InlineKeyboardButton(text="Скины", callback_data=CategoryAction(category="skins").pack()),
            InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="seller_buyer").pack())
        ]
    ])

def moderation_kb(offer_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Опубликовать", callback_data=OfferAction(action="publish", offer_id=offer_id).pack()),
         InlineKeyboardButton(text="Отклонить", callback_data=OfferAction(action="reject", offer_id=offer_id).pack())]
    ])

def reject_reasons_kb(offer_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Неверная категория", callback_data=RejectReason(reason="wrong_category", offer_id=offer_id).pack()),
            InlineKeyboardButton(text="Плохое описание", callback_data=RejectReason(reason="bad_description", offer_id=offer_id).pack())
        ],
        [
            InlineKeyboardButton(text="Нет стоимости", callback_data=RejectReason(reason="no_price", offer_id=offer_id).pack()),
            InlineKeyboardButton(text="Другое", callback_data=RejectReason(reason="other", offer_id=offer_id).pack())
        ],
        [InlineKeyboardButton(text="Неправильный username", callback_data=RejectReason(reason="wrong_username", offer_id=offer_id).pack())],
        [InlineKeyboardButton(text="← Отмена", callback_data=OfferAction(action="cancel_reject", offer_id=offer_id).pack())]
    ])

def review_moderation_kb(review_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Одобрить", callback_data=ReviewAction(action="approve", review_id=review_id).pack()),
         InlineKeyboardButton(text="Отклонить", callback_data=ReviewAction(action="reject", review_id=review_id).pack())]
    ])

def complaint_moderation_kb(reporter_id, complaint_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Одобрить", callback_data=ComplaintAction(action="approve", reporter_id=reporter_id, complaint_id=complaint_id).pack()),
         InlineKeyboardButton(text="Отклонить", callback_data=ComplaintAction(action="reject", reporter_id=reporter_id, complaint_id=complaint_id).pack())]
    ])

def back_to_main():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())]])

def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())]
    ])

def useful_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отслеживание", callback_data=MenuAction(action="tracking").pack())],
        [InlineKeyboardButton(text="Средние цены", callback_data=MenuAction(action="avg_prices").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())]
    ])

def scam_base_kb(page=0, total_pages=1):
    buttons = []
    if total_pages > 0:
        start = max(0, min(page, total_pages-5))
        end = min(start+5, total_pages)
        for p in range(start, end):
            buttons.append(InlineKeyboardButton(text=f"{p+1:02d}", callback_data=ScammersPageAction(page=p).pack()))
        if end < total_pages:
            if end < total_pages - 1:
                buttons.append(InlineKeyboardButton(text="...", callback_data="none"))
            buttons.append(InlineKeyboardButton(text=f"{total_pages:02d}", callback_data=ScammersPageAction(page=total_pages-1).pack()))
    rows = [buttons[i:i+3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="Пожаловаться", callback_data=MenuAction(action="complaint").pack())])
    rows.append([InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def tracking_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить", callback_data=TrackingAction(action="add").pack()),
         InlineKeyboardButton(text="Удалить", callback_data=TrackingAction(action="delete_menu").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="useful").pack())]
    ])

def back_to_useful():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="useful").pack())]])

def admin_panel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Заблокировать пользователя", callback_data=AdminAction(action="ban_user").pack())],
        [InlineKeyboardButton(text="Разблокировать пользователя", callback_data=AdminAction(action="unban_user").pack())],
        [InlineKeyboardButton(text="Удалить объявления", callback_data=AdminAction(action="delete_offers").pack())],
        [InlineKeyboardButton(text="Добавить мошенника", callback_data=AdminAction(action="add_scammer").pack())],
        [InlineKeyboardButton(text="Управление администраторами", callback_data=AdminAction(action="manage_admins").pack())],
        [InlineKeyboardButton(text="Фильтр слов", callback_data=AdminAction(action="filter_words").pack())],
        [InlineKeyboardButton(text="Закрепить объявление", callback_data=AdminAction(action="pin_offer").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="main_menu").pack())]
    ])

def filter_words_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить слово", callback_data=AdminAction(action="add_filter_word").pack()),
         InlineKeyboardButton(text="Удалить слово", callback_data=AdminAction(action="remove_filter_word").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="admin_panel").pack())]
    ])

def manage_admins_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить администратора", callback_data=AdminAction(action="add_admin").pack()),
         InlineKeyboardButton(text="Снять администратора", callback_data=AdminAction(action="remove_admin").pack())],
        [InlineKeyboardButton(text="Очистить username", callback_data=AdminAction(action="clear_username").pack())],
        [InlineKeyboardButton(text="← Назад", callback_data=MenuAction(action="admin_panel").pack())]
    ])