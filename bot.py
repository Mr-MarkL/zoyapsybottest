"""
Telegram-бот для психолога Зои Антонец
pip install python-telegram-bot==21.6
"""

import logging
import os
import sqlite3
from datetime import datetime
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler,
    ConversationHandler,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DB_PATH   = os.environ.get("DB_PATH", "zoya.db")
CONTACT   = "@Zoiapsyonline"
GROUP     = "https://t.me/Comebeakinself"
ANON_BOT  = "https://t.me/anonaskbot"

ADMINS = {"zoiapsyonline", "imarkell"}

ASK_EVENT_TYPE, ASK_EVENT_TITLE, ASK_EVENT_DATE, ASK_EVENT_DESC, ASK_EVENT_LINK = range(5)

# ═══ БАЗА ДАННЫХ ══════════════════════════════════════════════════════════════

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    c = get_db()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT,
            first_seen TEXT,
            last_seen TEXT,
            visits INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER,
            username TEXT,
            full_name TEXT,
            topic TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            title TEXT,
            description TEXT,
            link TEXT,
            event_date TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS admin_ids (
            username TEXT PRIMARY KEY,
            tg_id INTEGER NOT NULL
        );
    """)
    c.commit()
    c.close()

def save_admin_id(username: str, tg_id: int):
    """Сохраняем числовой ID админа при его /start."""
    c = get_db()
    c.execute("INSERT OR REPLACE INTO admin_ids(username, tg_id) VALUES(?,?)",
              (username.lower(), tg_id))
    c.commit()
    c.close()

def get_admin_tg_ids():
    """Возвращаем список числовых ID всех зарегистрированных админов."""
    c = get_db()
    rows = c.execute("SELECT tg_id FROM admin_ids").fetchall()
    c.close()
    return [r["tg_id"] for r in rows]

def is_new_visitor(tg_id: int) -> bool:
    c = get_db()
    exists = c.execute("SELECT 1 FROM visitors WHERE tg_id=?", (tg_id,)).fetchone()
    c.close()
    return exists is None

def upsert_visitor(tg_id, username, full_name):
    c = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if c.execute("SELECT 1 FROM visitors WHERE tg_id=?", (tg_id,)).fetchone():
        c.execute(
            "UPDATE visitors SET last_seen=?,visits=visits+1,username=?,full_name=? WHERE tg_id=?",
            (now, username, full_name, tg_id)
        )
    else:
        c.execute(
            "INSERT INTO visitors(tg_id,username,full_name,first_seen,last_seen) VALUES(?,?,?,?,?)",
            (tg_id, username, full_name, now, now)
        )
    c.commit()
    c.close()

def add_lead(tg_id, username, full_name, topic):
    c = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute(
        "INSERT INTO leads(tg_id,username,full_name,topic,created_at) VALUES(?,?,?,?,?)",
        (tg_id, username, full_name, topic, now)
    )
    c.commit()
    c.close()

def get_visitors(limit=50):
    c = get_db()
    rows = c.execute("SELECT * FROM visitors ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_leads(limit=50):
    c = get_db()
    rows = c.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    c.close()
    return [dict(r) for r in rows]

def get_events(type_filter=None, active_only=False):
    c = get_db()
    q = "SELECT * FROM events WHERE 1=1"
    params = []
    if type_filter:
        q += " AND type=?"
        params.append(type_filter)
    if active_only:
        q += " AND is_active=1"
    q += " ORDER BY created_at DESC"
    rows = c.execute(q, params).fetchall()
    c.close()
    return [dict(r) for r in rows]

def add_event(type_, title, description, link, event_date):
    c = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute(
        "INSERT INTO events(type,title,description,link,event_date,created_at) VALUES(?,?,?,?,?,?)",
        (type_, title, description, link, event_date, now)
    )
    c.commit()
    c.close()

def toggle_event(eid):
    c = get_db()
    c.execute("UPDATE events SET is_active=CASE WHEN is_active=1 THEN 0 ELSE 1 END WHERE id=?", (eid,))
    c.commit()
    c.close()

def delete_event(eid):
    c = get_db()
    c.execute("DELETE FROM events WHERE id=?", (eid,))
    c.commit()
    c.close()

def stats():
    c = get_db()
    tv = c.execute("SELECT COUNT(*) FROM visitors").fetchone()[0]
    tl = c.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    td = datetime.now().strftime("%Y-%m-%d")
    dv = c.execute("SELECT COUNT(*) FROM visitors WHERE first_seen LIKE ?", (td+"%",)).fetchone()[0]
    dl = c.execute("SELECT COUNT(*) FROM leads WHERE created_at LIKE ?", (td+"%",)).fetchone()[0]
    c.close()
    return {"total_visitors": tv, "total_leads": tl, "today_visitors": dv, "today_leads": dl}

# ═══ ПРОВЕРКА ПРАВ ════════════════════════════════════════════════════════════

def is_admin(update: Update) -> bool:
    u = update.effective_user
    if not u:
        return False
    return (u.username or "").lower() in ADMINS

# ═══ УВЕДОМЛЕНИЯ ══════════════════════════════════════════════════════════════

async def notify_admins(app, text: str):
    """
    Отправляет уведомление по числовым ID из таблицы admin_ids.
    Работает только после того, как админ хотя бы раз написал /start боту.
    """
    ids = get_admin_tg_ids()
    if not ids:
        logger.warning("notify_admins: таблица admin_ids пуста — админы не зарегистрированы.")
        return
    for uid in ids:
        try:
            await app.bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            logger.warning(f"notify_admins: не удалось отправить {uid}: {e}")

# ═══ КЛАВИАТУРЫ ═══════════════════════════════════════════════════════════════

def kb_main():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🪞 Обо мне"),        KeyboardButton("💙 Форматы работы")],
        [KeyboardButton("🌿 Запросы"),         KeyboardButton("📅 Эфиры / События")],
        [KeyboardButton("📩 Контакты"),        KeyboardButton("❓ Анонимный вопрос")],
    ], resize_keyboard=True)

def kb_admin():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📊 Статистика"),       KeyboardButton("👥 Посетители")],
        [KeyboardButton("📋 Лиды"),             KeyboardButton("📅 Управление событиями")],
        [KeyboardButton("➕ Добавить событие"), KeyboardButton("🔙 Режим пользователя")],
    ], resize_keyboard=True)

def kb_about():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🧭 Кто я и мой путь"),    KeyboardButton("🌟 Ценности и принципы")],
        [KeyboardButton("🧩 Подход к работе"),      KeyboardButton("🎓 Опыт и образование")],
        [KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)

def kb_requests():
    return ReplyKeyboardMarkup([
        [KeyboardButton("💔 Отношения"),         KeyboardButton("🌧 Тревога и страхи")],
        [KeyboardButton("⚡ Кризисы и потери"),  KeyboardButton("🔗 Созависимость")],
        [KeyboardButton("🌱 Самооценка"),         KeyboardButton("🧭 Поиск себя")],
        [KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)

def kb_events():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🎥 Прошедшие эфиры"),  KeyboardButton("📆 Предстоящие события")],
        [KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)

def signup_btn(cb):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📝 Записаться на консультацию", callback_data=cb)
    ]])

def event_manage_kb(events_list):
    rows = []
    for e in events_list:
        status = "✅" if e["is_active"] else "🔇"
        rows.append([
            InlineKeyboardButton(
                f"{status} {e['title'][:30]}",
                callback_data=f"etoggle_{e['id']}"
            ),
            InlineKeyboardButton("🗑", callback_data=f"edelete_{e['id']}")
        ])
    rows.append([InlineKeyboardButton("✖️ Закрыть", callback_data="eclose")])
    return InlineKeyboardMarkup(rows)

# ═══ ТЕКСТЫ ═══════════════════════════════════════════════════════════════════

def events_text(type_):
    evts = get_events(type_filter=type_, active_only=True)
    if not evts:
        label = "прошедших эфиров" if type_ == "past" else "запланированных событий"
        return f"Пока нет {label}. Следите за обновлениями!"
    icon = "🎥" if type_ == "past" else "📆"
    header = "Прошедшие эфиры" if type_ == "past" else "Предстоящие события"
    lines = [f"{icon} {header}\n"]
    for e in evts:
        line = f"• {e['title']}"
        if e.get("event_date"):
            line += f" — {e['event_date']}"
        if e.get("description"):
            line += f"\n  {e['description']}"
        if e.get("link"):
            line += f"\n  {e['link']}"
        lines.append(line)
    return "\n".join(lines)

TEXTS = {
"welcome": (
    "Здравствуйте! 🌿\n\n"
    "Я — виртуальный помощник психолога Зои Антонец.\n"
    "Здесь вы можете узнать о форматах работы, темах, "
    "с которыми работает Зоя, и записаться на консультацию.\n\n"
    "Выберите нужный раздел в меню ниже 👇"
),
"about_section": "Раздел «Обо мне». Выберите подраздел 👇",
"who_i_am": (
    "🧭 Кто я и мой путь\n\n"
    "Меня зовут Зоя Антонец 💙\n\n"
    "Я — психолог-консультант, магистр психологии. "
    "Моя работа строится на убеждении: каждый человек несёт в себе "
    "ресурсы для перемен — иногда просто нужен тот, кто поможет их найти.\n\n"
    "Я пришла в профессию через живой интерес к тому, "
    "как внутреннее состояние человека определяет качество его жизни. "
    "За каждой «проблемой» стоит живой опыт — он заслуживает внимания, а не оценки.\n\n"
    "Работаю онлайн с взрослыми. Веду сессии бережно, "
    "без давления и спешки — так, чтобы с первой встречи "
    "вы чувствовали себя услышанным и в безопасности.\n\n"
    "Если вы здесь — значит, что-то важное уже просится к свету. "
    "Я буду рада пройти этот путь рядом с вами."
),
"values": (
    "🌟 Мои ценности и принципы\n\n"
    "🔒 Конфиденциальность\n"
    "Всё, что происходит на сессии, остаётся между нами. Это моё личное обязательство.\n\n"
    "🛡 Безопасность\n"
    "Правило «стоп» действует всегда: вы можете остановить исследование любой темы.\n\n"
    "🌿 Безоценочность\n"
    "На сессии нет правильного или неправильного. Значимы ваш опыт и ваш взгляд.\n\n"
    "🔑 Уважение к вашему пути\n"
    "Вы — главный эксперт своей жизни. Я помогаю услышать себя.\n\n"
    "✨ Постоянное развитие\n"
    "Я регулярно прохожу супервизию и нахожусь в личной терапии — "
    "чтобы быть для вас устойчивой опорой."
),
"approach": (
    "🧩 Мой подход к работе\n\n"
    "Я работаю интегративно — осознанно сочетаю инструменты, которые подходят именно вам.\n\n"
    "📘 КПТ (когнитивно-поведенческая терапия)\n"
    "Помогает распознать мысли, поддерживающие тревогу или деструктивные паттерны.\n\n"
    "📗 Гештальт-консультирование\n"
    "Работает с незавершёнными ситуациями прошлого, восстанавливает контакт с чувствами.\n\n"
    "📙 МАК (метафорические ассоциативные карты)\n"
    "Открывает доступ к глубинным переживаниям там, где слова ещё не найдены.\n\n"
    "Каждый человек уникален — я выстраиваю подход, который работает именно для вас."
),
"education": (
    "🎓 Опыт и образование\n\n"
    "🏛 Образование:\n"
    "— Магистр психологии (диплом государственного университета)\n"
    "— КПТ и гештальт-консультирование\n"
    "— Методы работы с агрессией\n"
    "— МАК в практике психолога\n"
    "— Боевой ПТСР и семьи военнослужащих\n\n"
    "💼 Практический опыт:\n"
    "— 1,5+ лет волонтёрства в фонде «НеТерпи»\n"
    "— Регулярные супервизии и интервизионные группы\n"
    "— Постоянная личная терапия\n\n"
    "Все дипломы и сертификаты готова предоставить по запросу."
),
"formats": (
    "💙 Форматы работы\n\n"
    "🖥 Онлайн-консультации (индивидуально)\n\n"
    "📌 Платформы: Яндекс.Телемост, MAX, WeChat\n\n"
    "💰 Стоимость:\n"
    "— Первая пробная сессия: 2 500 руб. / 60 минут\n"
    "— Последующие сессии: 5 000 руб. / 60 минут\n\n"
    "🗓 Запись за 24 часа по предоплате.\n\n"
    "📋 Напишите мне:\n"
    "✔️ Имя, возраст\n"
    "✔️ Краткое описание запроса\n"
    "✔️ Удобное время (будни/выходные, утро/день/вечер МСК)\n\n"
    f"📩 {CONTACT}"
),
"relations": (
    "💔 Отношения\n\n"
    "Близкие люди должны быть источником тепла — но иногда именно они "
    "причиняют самую глубокую боль. Постоянные конфликты, ощущение "
    "одиночества рядом с партнёром, непонимание с родителями — "
    "всё это не норма, с которой нужно просто мириться.\n\n"
    "За каждым таким паттерном стоит что-то важное из прошлого: "
    "незакрытые обиды, усвоенные роли, страх близости или отвержения. "
    "Когда мы находим это — отношения начинают меняться.\n\n"
    "На консультации мы разберём, что происходит в ваших отношениях, "
    "откуда это берётся и что можно изменить уже сейчас.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"anxiety": (
    "🌧 Тревога и страхи\n\n"
    "Тревога редко приходит одна. Она захватывает мысли, мешает спать, "
    "заставляет избегать людей и ситуаций — и постепенно сужает жизнь "
    "до маленького безопасного круга. Это изматывает.\n\n"
    "Хорошая новость: тревога поддаётся работе. Это не часть характера "
    "и не приговор — это выученная реакция психики, которую можно переучить. "
    "Иррациональные страхи, хроническое чувство вины — всё это меняется.\n\n"
    "Если тревога уже давно управляет вашей жизнью — пришло время "
    "вернуть этот контроль себе.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"crisis": (
    "⚡ Кризисы и потери\n\n"
    "Развод, потеря работы, уход близкого, переезд, болезнь — есть "
    "события, после которых прежняя жизнь уже не возвращается. "
    "Растерянность, пустота, ощущение что земля ушла из-под ног — "
    "это нормальные реакции на ненормальные обстоятельства.\n\n"
    "Но оставаться с этим в одиночестве необязательно. В кризисе "
    "важно иметь рядом того, кто поможет устоять.\n\n"
    "Вместе мы найдём внутренние опоры и постепенно выстроим дорогу к новому этапу. "
    "Кризис — это не конец истории. Иногда это её самая важная глава.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"codependency": (
    "🔗 Созависимость\n\n"
    "Если в вашей семье были алкоголизм, насилие или хаос — "
    "вы, скорее всего, выросли с убеждением, что чужие потребности "
    "важнее ваших. Это называется созависимость, и она незаметно "
    "управляет отношениями, работой и самооценкой.\n\n"
    "Паттерны из дисфункциональной семьи воспроизводятся автоматически: "
    "вы спасаете, терпите, берёте чужую ответственность — и не понимаете, "
    "почему снова оказываетесь в том же сценарии.\n\n"
    "Это можно изменить. Вы научитесь отличать свои границы от чужих "
    "и откроете — каково это, жить для себя, а не для других.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"self_esteem": (
    "🌱 Самооценка\n\n"
    "«В жизни вроде всё есть, а внутри пусто.» Это одна из самых "
    "частых фраз, с которыми приходят на консультацию. "
    "За ней почти всегда стоит одно: человек живёт не своей жизнью.\n\n"
    "Низкая самооценка — это не врождённый дефект. Это результат "
    "усвоенных посланий: «ты недостаточно хорош», «твои желания не важны».\n\n"
    "На сессиях мы найдём, откуда этот голос взялся, и начнём "
    "выстраивать новую опору — изнутри, а не из чужих ожиданий.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"finding_self": (
    "🧭 Поиск себя\n\n"
    "Иногда человек просыпается и понимает: жизнь идёт, а ощущения "
    "что она — его, нет. Правильная работа, правильные отношения — "
    "но что-то важное потерялось по дороге.\n\n"
    "Поиск себя — это не инфантильный кризис. Когда мы живём в отрыве "
    "от собственных ценностей, рано или поздно приходит пустота.\n\n"
    "Вместе мы разберёмся, что действительно важно для вас — "
    "а не для родителей или общества. И найдём путь обратно — к себе настоящему.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),
"contacts": (
    "📩 Контакты\n\n"
    f"💬 Написать лично: {CONTACT}\n\n"
    f"👥 Канал и сообщество: {GROUP}\n\n"
    "Я отвечаю на сообщения в течение дня.\n"
    "Напишите — и мы подберём удобное время для первой встречи 💙"
),
"anon_question": (
    "❓ Анонимный вопрос\n\n"
    "Если вас что-то тревожит, но вы пока не готовы говорить открыто — "
    "воспользуйтесь анонимным ботом.\n\n"
    "✔️ Описать ситуацию, которая беспокоит\n"
    "✔️ Спросить совет в сложном выборе\n"
    "✔️ Получить поддержку, когда тяжело\n"
    "✔️ Разобрать чувства, которые сложно назвать вслух\n\n"
    f"👉 {ANON_BOT}"
),
"requests_section": "С чем я работаю — выберите тему 👇",
"events_section":   "Выберите категорию 👇",
"back_to_main":     "Вы вернулись в главное меню 👇",
"unknown":          "Пожалуйста, воспользуйтесь меню ниже 👇",
}

ROUTES = {
    "🪞 Обо мне":           ("about_section",   kb_about,    None),
    "💙 Форматы работы":    ("formats",          kb_main,     "signup_general"),
    "🌿 Запросы":           ("requests_section", kb_requests, None),
    "📅 Эфиры / События":   ("events_section",   kb_events,   None),
    "📩 Контакты":          ("contacts",         kb_main,     None),
    "❓ Анонимный вопрос":  ("anon_question",    kb_main,     None),
    "🧭 Кто я и мой путь":    ("who_i_am",   kb_about, "signup_general"),
    "🌟 Ценности и принципы": ("values",      kb_about, "signup_general"),
    "🧩 Подход к работе":     ("approach",    kb_about, "signup_general"),
    "🎓 Опыт и образование":  ("education",   kb_about, "signup_general"),
    "💔 Отношения":         ("relations",    kb_requests, "signup_relations"),
    "🌧 Тревога и страхи":  ("anxiety",      kb_requests, "signup_anxiety"),
    "⚡ Кризисы и потери":  ("crisis",       kb_requests, "signup_crisis"),
    "🔗 Созависимость":     ("codependency", kb_requests, "signup_codependency"),
    "🌱 Самооценка":        ("self_esteem",  kb_requests, "signup_self_esteem"),
    "🧭 Поиск себя":        ("finding_self", kb_requests, "signup_finding_self"),
}

SIGNUP_REPLIES = {
    "signup_general":      f"Отлично! Напишите мне, договоримся о времени:\n{CONTACT}",
    "signup_relations":    f"Готова работать с темой отношений.\n{CONTACT}",
    "signup_anxiety":      f"Готова помочь с тревогой и страхами.\n{CONTACT}",
    "signup_crisis":       f"Готова поддержать в кризисный период.\n{CONTACT}",
    "signup_codependency": f"Готова работать с созависимостью.\n{CONTACT}",
    "signup_self_esteem":  f"Готова помочь с самооценкой.\n{CONTACT}",
    "signup_finding_self": f"Готова сопровождать вас на пути к себе.\n{CONTACT}",
}

TOPIC_NAMES = {
    "signup_general":      "Общий запрос",
    "signup_relations":    "Отношения",
    "signup_anxiety":      "Тревога и страхи",
    "signup_crisis":       "Кризисы и потери",
    "signup_codependency": "Созависимость",
    "signup_self_esteem":  "Самооценка",
    "signup_finding_self": "Поиск себя",
}

# ═══ ХЭНДЛЕРЫ ═════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = (user.username or "").lower()
    full_name = user.full_name or "без имени"

    # Если это админ — сохраняем его числовой ID для уведомлений
    if username in ADMINS:
        save_admin_id(username, user.id)
        await update.message.reply_text(
            f"Привет, {user.first_name}! Вы вошли как администратор.\nВыберите режим:",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("🛠 Режим администратора")],
                [KeyboardButton("👤 Режим пользователя")],
            ], resize_keyboard=True)
        )
        return

    # Обычный пользователь
    new = is_new_visitor(user.id)
    upsert_visitor(user.id, user.username or "", full_name)

    if new:
        uname_display = f"@{user.username}" if user.username else f"ID {user.id}"
        await notify_admins(
            ctx.application,
            f"👋 Новый пользователь!\n\n"
            f"👤 {full_name}\n"
            f"📎 {uname_display}\n"
            f"🆔 {user.id}"
        )

    await update.message.reply_text(TEXTS["welcome"], reply_markup=kb_main())


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    raw = (update.message.text or "").strip()

    # Переключение режимов для админов
    if raw == "🛠 Режим администратора":
        if not is_admin(update):
            await update.message.reply_text("У вас нет прав доступа.")
            return
        await update.message.reply_text(
            "Вы в режиме администратора 🛠\n\nВыберите действие:",
            reply_markup=kb_admin()
        )
        return

    if raw in ("👤 Режим пользователя", "🔙 Режим пользователя"):
        await update.message.reply_text(TEXTS["welcome"], reply_markup=kb_main())
        return

    # Admin команды
    if raw == "📊 Статистика" and is_admin(update):
        s = stats()
        await update.message.reply_text(
            f"📊 Статистика бота\n\n"
            f"👥 Всего посетителей: {s['total_visitors']}\n"
            f"📋 Всего заявок: {s['total_leads']}\n"
            f"🌅 Новых сегодня: {s['today_visitors']}\n"
            f"🔥 Заявок сегодня: {s['today_leads']}",
            reply_markup=kb_admin()
        )
        return

    if raw == "👥 Посетители" and is_admin(update):
        visitors = get_visitors(30)
        if not visitors:
            await update.message.reply_text("Посетителей пока нет.", reply_markup=kb_admin())
            return
        lines = ["👥 Последние 30 посетителей:\n"]
        for i, v in enumerate(visitors, 1):
            uname = f"@{v['username']}" if v['username'] else f"ID {v['tg_id']}"
            lines.append(f"{i}. {v['full_name'] or '—'} | {uname} | визитов: {v['visits']} | {v['last_seen']}")
        msg = "\n".join(lines)
        if len(msg) > 4000:
            msg = msg[:4000] + "\n…(обрезано)"
        await update.message.reply_text(msg, reply_markup=kb_admin())
        return

    if raw == "📋 Лиды" and is_admin(update):
        leads = get_leads(30)
        if not leads:
            await update.message.reply_text("Заявок пока нет.", reply_markup=kb_admin())
            return
        lines = ["📋 Последние 30 заявок:\n"]
        for i, l in enumerate(leads, 1):
            uname = f"@{l['username']}" if l['username'] else f"ID {l['tg_id']}"
            lines.append(f"{i}. {l['created_at']} | {l['full_name'] or '—'} | {uname} | {l['topic']}")
        msg = "\n".join(lines)
        if len(msg) > 4000:
            msg = msg[:4000] + "\n…(обрезано)"
        await update.message.reply_text(msg, reply_markup=kb_admin())
        return

    if raw == "📅 Управление событиями" and is_admin(update):
        evts = get_events()
        if not evts:
            await update.message.reply_text(
                "Событий пока нет.\nНажмите «➕ Добавить событие».",
                reply_markup=kb_admin()
            )
            return
        await update.message.reply_text(
            "📅 Управление событиями\n✅ активно | 🔇 скрыто | 🗑 удалить",
            reply_markup=event_manage_kb(evts)
        )
        return

    if raw == "⬅️ Назад":
        await update.message.reply_text(TEXTS["back_to_main"], reply_markup=kb_main())
        return

    if raw == "🎥 Прошедшие эфиры":
        await update.message.reply_text(events_text("past"), reply_markup=kb_events())
        return

    if raw == "📆 Предстоящие события":
        await update.message.reply_text(events_text("upcoming"), reply_markup=kb_events())
        return

    route = ROUTES.get(raw)
    if route is None:
        for key in ROUTES:
            if key.strip() == raw or raw in key or key in raw:
                route = ROUTES[key]
                break

    if route is None:
        await update.message.reply_text(TEXTS["unknown"], reply_markup=kb_main())
        return

    text_key, keyboard_fn, cb_data = route
    if cb_data:
        await update.message.reply_text(TEXTS[text_key], reply_markup=signup_btn(cb_data))
        await update.message.reply_text("Выберите следующий раздел 👇", reply_markup=keyboard_fn())
    else:
        await update.message.reply_text(TEXTS[text_key], reply_markup=keyboard_fn())


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user = update.effective_user

    if data.startswith("etoggle_") and is_admin(update):
        eid = int(data.split("_")[1])
        toggle_event(eid)
        evts = get_events()
        await query.edit_message_reply_markup(reply_markup=event_manage_kb(evts))
        return

    if data.startswith("edelete_") and is_admin(update):
        eid = int(data.split("_")[1])
        delete_event(eid)
        evts = get_events()
        if evts:
            await query.edit_message_reply_markup(reply_markup=event_manage_kb(evts))
        else:
            await query.edit_message_text("Все события удалены.")
        return

    if data == "eclose":
        await query.edit_message_text("Управление событиями закрыто.")
        return

    # Кнопка «Записаться»
    topic_name = TOPIC_NAMES.get(data, data)
    add_lead(user.id, user.username or "", user.full_name or "", topic_name)
    uname_display = f"@{user.username}" if user.username else f"ID {user.id}"
    await notify_admins(
        ctx.application,
        f"🔥 Новая заявка на запись!\n\n"
        f"👤 {user.full_name or 'без имени'}\n"
        f"📎 {uname_display}\n"
        f"📌 Тема: {topic_name}\n"
        f"🆔 {user.id}"
    )
    reply = SIGNUP_REPLIES.get(data, f"Для записи: {CONTACT}")
    await query.message.reply_text(reply)


# ═══ ДИАЛОГ ДОБАВЛЕНИЯ СОБЫТИЯ ════════════════════════════════════════════════

async def add_event_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "Тип события?",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📆 Предстоящее"), KeyboardButton("🎥 Прошедшее")],
             [KeyboardButton("❌ Отмена")]],
            resize_keyboard=True
        )
    )
    return ASK_EVENT_TYPE

async def got_event_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        await update.message.reply_text("Отменено.", reply_markup=kb_admin())
        return ConversationHandler.END
    ctx.user_data["event_type"] = "upcoming" if "Предстоящее" in text else "past"
    await update.message.reply_text("Название события:")
    return ASK_EVENT_TITLE

async def got_event_title(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["event_title"] = update.message.text.strip()
    await update.message.reply_text("Дата (например: 25 апреля 2026) или «-» пропустить:")
    return ASK_EVENT_DATE

async def got_event_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    ctx.user_data["event_date"] = "" if t == "-" else t
    await update.message.reply_text("Краткое описание (или «-» пропустить):")
    return ASK_EVENT_DESC

async def got_event_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    ctx.user_data["event_desc"] = "" if t == "-" else t
    await update.message.reply_text("Ссылка (или «-» пропустить):")
    return ASK_EVENT_LINK

async def got_event_link(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    link = "" if t == "-" else t
    d = ctx.user_data
    add_event(d["event_type"], d["event_title"], d.get("event_desc", ""), link, d.get("event_date", ""))
    type_label = "Предстоящее" if d["event_type"] == "upcoming" else "Прошедшее"
    await update.message.reply_text(
        f"✅ Событие добавлено!\n\n"
        f"Тип: {type_label}\n"
        f"Название: {d['event_title']}\n"
        f"Дата: {d.get('event_date') or '—'}\n"
        f"Ссылка: {link or '—'}",
        reply_markup=kb_admin()
    )
    return ConversationHandler.END

async def cancel_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=kb_admin())
    return ConversationHandler.END

# ═══ ЗАПУСК ═══════════════════════════════════════════════════════════════════

def main():
    init_db()
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан!")

    app = Application.builder().token(BOT_TOKEN).build()

    add_event_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Добавить событие$"), add_event_start)],
        states={
            ASK_EVENT_TYPE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_event_type)],
            ASK_EVENT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_event_title)],
            ASK_EVENT_DATE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_event_date)],
            ASK_EVENT_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_event_desc)],
            ASK_EVENT_LINK:  [MessageHandler(filters.TEXT & ~filters.COMMAND, got_event_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(add_event_conv)
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Бот запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
