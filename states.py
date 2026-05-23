from aiogram.fsm.state import State, StatesGroup

class RegisterContact(StatesGroup):
    waiting_for_username = State()

class NewOffer(StatesGroup):
    is_seller = State()
    entering_title = State()
    entering_text = State()
    entering_price = State()
    uploading_media = State()

class WriteReview(StatesGroup):
    waiting_for_seller_username = State()
    waiting_for_rating = State()
    waiting_for_comment = State()

class AskRating(StatesGroup):
    waiting_for_username = State()

class TrackingAdd(StatesGroup):
    waiting_for_keyword = State()
    original_message_id = State()
    chat_id = State()

class Complaint(StatesGroup):
    waiting_for_game_nickname = State()
    waiting_for_username = State()
    waiting_for_reason = State()
    waiting_for_photo = State()

class AvgPrice(StatesGroup):
    waiting_for_keyword = State()

# Админские состояния
class AdminBan(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_reason = State()

class AdminUnban(StatesGroup):
    waiting_for_user_id = State()

class AdminDeleteOffers(StatesGroup):
    waiting_for_days = State()

class AdminAddScammer(StatesGroup):
    waiting_for_game_nickname = State()
    waiting_for_username = State()
    waiting_for_reason = State()

class AdminManageAdmins(StatesGroup):
    waiting_for_user_id = State()
    confirm = State()

class AdminFilterWords(StatesGroup):
    waiting_for_word = State()

class AdminPinOffer(StatesGroup):
    waiting_for_offer_id = State()
    waiting_for_duration = State()