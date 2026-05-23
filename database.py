import aiosqlite
from config import DB_NAME, OWNER_IDS

class Database:
    def __init__(self):
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(DB_NAME)
        await self.db.execute("PRAGMA foreign_keys = ON")
        await self._create_tables()
        await self._migrate()

    async def _create_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                contact_username TEXT UNIQUE,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                is_moderator INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                title TEXT DEFAULT '',
                title_lower TEXT DEFAULT '',
                text TEXT,
                price INTEGER DEFAULT 0,
                price_type TEXT DEFAULT 'fixed',
                is_seller INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                edited_at DATETIME,
                moderator_id INTEGER,
                rejection_reason TEXT,
                channel_message_id INTEGER,
                pinned_until DATETIME,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS offer_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                offer_id INTEGER NOT NULL,
                file_id TEXT NOT NULL,
                file_type TEXT DEFAULT 'photo',
                FOREIGN KEY(offer_id) REFERENCES offers(id)
            );
            CREATE TABLE IF NOT EXISTS bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                reason TEXT,
                type TEXT,
                banned_until DATETIME,
                banned_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reviewer_id INTEGER,
                seller_id INTEGER,
                rating INTEGER CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                moderation_comment TEXT,
                FOREIGN KEY(reviewer_id) REFERENCES users(user_id),
                FOREIGN KEY(seller_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS spam_log (
                user_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tracking (
                user_id INTEGER,
                keyword TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS scammers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_nickname TEXT,
                contact_username TEXT,
                user_id INTEGER,
                reporter_id INTEGER,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS filter_words (
                word TEXT PRIMARY KEY
            );
        """)
        await self.db.commit()

    async def _migrate(self):
        try:
            await self.db.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
        except:
            pass
        for uid in OWNER_IDS:
            await self.db.execute("INSERT OR IGNORE INTO users (user_id, contact_username) VALUES (?, ?)", (uid, f"owner{uid}"))
            await self.db.execute("UPDATE users SET is_admin = 2 WHERE user_id = ?", (uid,))
        await self.db.commit()

    # ---------- Пользователи ----------
    async def get_user(self, user_id):
        async with self.db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row

    async def add_user(self, user_id, username, contact_username):
        existing = await self.get_user_by_username(contact_username)
        if existing and existing[0] != user_id:
            return False
        await self.db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, contact_username) VALUES (?, ?, ?)",
            (user_id, username, contact_username)
        )
        await self.db.commit()
        return True

    async def update_contact(self, user_id, contact_username):
        existing = await self.get_user_by_username(contact_username)
        if existing and existing[0] != user_id:
            return False
        await self.db.execute("UPDATE users SET contact_username = ? WHERE user_id = ?", (contact_username, user_id))
        await self.db.commit()
        return True

    async def make_moderator(self, user_id):
        await self.db.execute("UPDATE users SET is_moderator = 1 WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def remove_moderator(self, user_id):
        await self.db.execute("UPDATE users SET is_moderator = 0 WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def is_moderator(self, user_id):
        async with self.db.execute("SELECT is_moderator FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row and row[0] == 1

    async def is_admin(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return False
        try:
            is_adm = user[7]
        except IndexError:
            return False
        return is_adm is not None and is_adm >= 1

    async def is_owner(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            return False
        try:
            return user[7] == 2
        except IndexError:
            return False

    async def make_admin(self, user_id):
        user = await self.get_user(user_id)
        if not user:
            await self.add_user(user_id, f"id{user_id}", f"id{user_id}")
        if await self.is_owner(user_id):
            return False
        await self.db.execute("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
        await self.db.commit()
        return True

    async def remove_admin(self, user_id):
        if await self.is_owner(user_id):
            return False
        await self.db.execute("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
        await self.db.commit()
        return True

    async def get_all_admins(self):
        async with self.db.execute(
            "SELECT user_id, contact_username, is_admin FROM users WHERE is_admin >= 1"
        ) as cursor:
            return await cursor.fetchall()

    async def clear_username(self, contact_username):
        await self.db.execute("UPDATE users SET contact_username = NULL WHERE contact_username = ?", (contact_username,))
        await self.db.commit()

    async def is_username_taken(self, contact_username):
        user = await self.get_user_by_username(contact_username)
        return user is not None

    async def ban_user(self, user_id, reason, ban_type='permanent', duration=None):
        if await self.is_owner(user_id):
            return False
        user = await self.get_user(user_id)
        if not user:
            await self.add_user(user_id, f"id{user_id}", f"id{user_id}")
        await self.db.execute("UPDATE users SET is_banned = 1, ban_reason = ? WHERE user_id = ?", (reason, user_id))
        if ban_type == 'temp':
            await self.db.execute(
                "INSERT INTO bans (user_id, reason, type, banned_until) VALUES (?, ?, ?, datetime('now', '+' || ? || ' seconds'))",
                (user_id, reason, 'temp', duration)
            )
        else:
            await self.db.execute(
                "INSERT INTO bans (user_id, reason, type) VALUES (?, ?, 'permanent')",
                (user_id, reason)
            )
        await self.db.commit()
        return True

    async def unban_user(self, user_id):
        await self.db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?", (user_id,))
        await self.db.execute("DELETE FROM bans WHERE user_id = ?", (user_id,))
        await self.db.commit()

    async def get_user_by_username(self, contact_username):
        async with self.db.execute("SELECT * FROM users WHERE contact_username = ?", (contact_username,)) as cursor:
            return await cursor.fetchone()

    # ---------- Объявления ----------
    async def add_offer(self, user_id, category, title, text, price=0, price_type='fixed', is_seller=1):
        title_lower = title.lower().strip()
        cursor = await self.db.execute(
            "INSERT INTO offers (user_id, category, title, title_lower, text, price, price_type, is_seller) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, category, title, title_lower, text, price, price_type, is_seller)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def add_media(self, offer_id, file_id):
        await self.db.execute("INSERT INTO offer_media (offer_id, file_id) VALUES (?, ?)", (offer_id, file_id))
        await self.db.commit()

    async def get_offer(self, offer_id):
        async with self.db.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)) as cursor:
            offer = await cursor.fetchone()
            if not offer:
                return None
            async with self.db.execute("SELECT file_id FROM offer_media WHERE offer_id = ?", (offer_id,)) as mcur:
                media = [row[0] for row in await mcur.fetchall()]
            offer = dict(zip([d[0] for d in cursor.description], offer))
            offer['media_files'] = media
            return offer

    async def update_offer_status(self, offer_id, status, **kwargs):
        if status == 'approved':
            await self.db.execute(
                "UPDATE offers SET status = ?, channel_message_id = ?, moderator_id = ? WHERE id = ?",
                (status, kwargs.get('channel_message_id'), kwargs.get('moderator_id'), offer_id)
            )
        elif status == 'rejected':
            await self.db.execute(
                "UPDATE offers SET status = ?, rejection_reason = ? WHERE id = ?",
                (status, kwargs.get('rejection_reason'), offer_id)
            )
        else:
            await self.db.execute("UPDATE offers SET status = ? WHERE id = ?", (status, offer_id))
        await self.db.commit()

    async def get_user_offers_count(self, user_id):
        async with self.db.execute("SELECT COUNT(*) FROM offers WHERE user_id = ? AND status = 'approved'", (user_id,)) as cursor:
            return (await cursor.fetchone())[0]

    # ---------- Отзывы ----------
    async def add_review(self, reviewer_id, seller_id, rating, comment):
        cursor = await self.db.execute(
            "INSERT INTO reviews (reviewer_id, seller_id, rating, comment) VALUES (?, ?, ?, ?)",
            (reviewer_id, seller_id, rating, comment)
        )
        await self.db.commit()
        return cursor.lastrowid

    async def update_review_status(self, review_id, status, moderation_comment=None):
        if moderation_comment:
            await self.db.execute(
                "UPDATE reviews SET status = ?, moderation_comment = ? WHERE id = ?",
                (status, moderation_comment, review_id)
            )
        else:
            await self.db.execute("UPDATE reviews SET status = ? WHERE id = ?", (status, review_id))
        await self.db.commit()

    async def get_seller_rating(self, seller_id):
        async with self.db.execute(
            "SELECT AVG(rating), COUNT(*) FROM reviews WHERE seller_id = ? AND status = 'approved'",
            (seller_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return (row[0] or 0.0, row[1])

    async def get_top_sellers(self, limit=10):
        async with self.db.execute(
            """SELECT u.user_id, u.contact_username, AVG(r.rating), COUNT(r.id)
               FROM users u JOIN reviews r ON u.user_id = r.seller_id
               WHERE r.status = 'approved'
               GROUP BY u.user_id
               ORDER BY AVG(r.rating) DESC, COUNT(r.id) DESC
               LIMIT ?""", (limit,)
        ) as cursor:
            return await cursor.fetchall()

    async def get_user_rank(self, user_id):
        top = await self.get_top_sellers(1000)
        for i, (uid, _, _, _) in enumerate(top, 1):
            if uid == user_id:
                return i
        return None

    # ---------- Антиспам ----------
    async def log_spam(self, user_id):
        await self.db.execute("INSERT INTO spam_log (user_id) VALUES (?)", (user_id,))
        await self.db.commit()

    async def get_recent_spam_count(self, user_id, since_seconds):
        async with self.db.execute(
            "SELECT COUNT(*) FROM spam_log WHERE user_id = ? AND timestamp > datetime('now', '-' || ? || ' seconds')",
            (user_id, since_seconds)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def had_temp_ban(self, user_id):
        async with self.db.execute("SELECT COUNT(*) FROM bans WHERE user_id = ? AND type = 'temp'", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] > 0

    async def reset_spam_and_bans(self):
        await self.db.execute("DELETE FROM spam_log")
        await self.db.execute("DELETE FROM bans")
        await self.db.execute("UPDATE users SET is_banned = 0, ban_reason = NULL")
        await self.db.commit()

    # ---------- Отслеживание ----------
    async def add_track_keyword(self, user_id, keyword):
        await self.db.execute("INSERT INTO tracking (user_id, keyword) VALUES (?, ?)", (user_id, keyword))
        await self.db.commit()

    async def remove_track_keyword(self, user_id, keyword):
        await self.db.execute("DELETE FROM tracking WHERE user_id = ? AND keyword = ?", (user_id, keyword))
        await self.db.commit()

    async def get_user_keywords(self, user_id):
        async with self.db.execute("SELECT keyword FROM tracking WHERE user_id = ?", (user_id,)) as cursor:
            return [row[0] for row in await cursor.fetchall()]

    async def get_all_trackings(self):
        async with self.db.execute("SELECT user_id, keyword FROM tracking") as cursor:
            return await cursor.fetchall()

    # ---------- Топ продавцов (по количеству объявлений, максимум 5) ----------
    async def get_top_sellers_by_offers(self, limit=5):
        async with self.db.execute(
            """SELECT u.user_id, u.contact_username, COUNT(o.id) as cnt
               FROM users u JOIN offers o ON u.user_id = o.user_id
               WHERE o.status = 'approved'
               GROUP BY u.user_id
               ORDER BY cnt DESC
               LIMIT ?""", (limit,)
        ) as cursor:
            return await cursor.fetchall()

    # ---------- Средние цены (поиск по title_lower, только продавцы) ----------
    async def get_average_price_by_keyword(self, keyword):
        words = keyword.lower().split()
        conditions = " AND ".join(["title_lower LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]
        async with self.db.execute(
            f"SELECT COUNT(*) FROM offers WHERE status = 'approved' AND is_seller = 1 AND price > 0 AND {conditions}",
            params
        ) as cursor:
            row = await cursor.fetchone()
            count = row[0] if row else 0
        if count == 0:
            return 0, 0
        async with self.db.execute(
            f"SELECT AVG(price) FROM offers WHERE status = 'approved' AND is_seller = 1 AND price > 0 AND {conditions}",
            params
        ) as cursor:
            row = await cursor.fetchone()
            avg = row[0] or 0
        return avg, count

    # ---------- Мошенники ----------
    async def add_scammer(self, game_nickname, contact_username, user_id, reporter_id, reason):
        await self.db.execute(
            "INSERT INTO scammers (game_nickname, contact_username, user_id, reporter_id, reason) VALUES (?, ?, ?, ?, ?)",
            (game_nickname, contact_username, user_id, reporter_id, reason)
        )
        await self.db.commit()

    async def get_scammers_count(self):
        async with self.db.execute("SELECT COUNT(*) FROM scammers") as cursor:
            row = await cursor.fetchone()
            return row[0]

    async def get_scammers_page(self, offset, limit=5):
        async with self.db.execute(
            "SELECT game_nickname, contact_username, user_id FROM scammers ORDER BY id DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ) as cursor:
            return await cursor.fetchall()

    # ---------- Фильтр слов ----------
    async def add_filter_word(self, word):
        await self.db.execute("INSERT OR IGNORE INTO filter_words (word) VALUES (?)", (word.lower(),))
        await self.db.commit()

    async def remove_filter_word(self, word):
        await self.db.execute("DELETE FROM filter_words WHERE word = ?", (word.lower(),))
        await self.db.commit()

    async def get_filter_words(self):
        async with self.db.execute("SELECT word FROM filter_words") as cursor:
            return [row[0] for row in await cursor.fetchall()]

    async def check_filter_words(self, text):
        words = await self.get_filter_words()
        text_lower = text.lower()
        for w in words:
            if w in text_lower:
                return True, w
        return False, None

    # ---------- Админские методы ----------
    async def delete_offers_last_days(self, days):
        await self.db.execute("""
            DELETE FROM offer_media WHERE offer_id IN (
                SELECT id FROM offers WHERE created_at >= datetime('now', ?)
            )
        """, (f'-{days} days',))
        await self.db.execute("""
            DELETE FROM offers WHERE created_at >= datetime('now', ?)
        """, (f'-{days} days',))
        await self.db.commit()

    async def pin_offer(self, offer_id, days):
        await self.db.execute(
            "UPDATE offers SET pinned_until = datetime('now', ?) WHERE id = ?",
            (f'+{days} days', offer_id)
        )
        await self.db.commit()

    async def pin_offer_by_message_id(self, message_id, days):
        await self.db.execute(
            "UPDATE offers SET pinned_until = datetime('now', ?) WHERE channel_message_id = ?",
            (f'+{days} days', message_id)
        )
        await self.db.commit()