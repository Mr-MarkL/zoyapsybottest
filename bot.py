"""
Telegram-бот для психолога Зои Антонец
pip install python-telegram-bot==21.6
"""

import logging
import os
import json
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN  = os.environ.get("BOT_TOKEN", "")
ADMIN_ID   = os.environ.get("ADMIN_ID", "")   # Telegram ID Зои (число) — добавить в переменные окружения
CONTACT    = "@Zoiapsyonline"
GROUP      = "https://t.me/Comebeakinself"
ANON_BOT   = "https://t.me/anonaskbot"

# ═══ КЛАВИАТУРЫ ═══════════════════════════════════════════════════════════════

def kb_main():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🪞 Обо мне"),        KeyboardButton("💙 Форматы работы")],
        [KeyboardButton("🌿 Запросы"),         KeyboardButton("📅 Эфиры / События")],
        [KeyboardButton("📩 Контакты"),        KeyboardButton("❓ Анонимный вопрос")],
    ], resize_keyboard=True)

def kb_about():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🧭 Кто я и мой путь"),    KeyboardButton("🌟 Ценности и принципы")],
        [KeyboardButton("🧩 Подход к работе"),      KeyboardButton("🎓 Опыт и образование")],
        [KeyboardButton("⬅️ Назад")],
    ], resize_keyboard=True)

def kb_requests():
    return ReplyKeyboardMarkup([
        [KeyboardButton("💔 Отношения"),          KeyboardButton("🌧 Тревога и страхи")],
        [KeyboardButton("⚡ Кризисы и потери"),   KeyboardButton("🔗 Созависимость")],
        [KeyboardButton("🌱 Самооценка"),          KeyboardButton("🧭 Поиск себя")],
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

# ═══ ТЕКСТЫ ═══════════════════════════════════════════════════════════════════

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
    "За каждой «проблемой» стоит живой опыт — и он заслуживает "
    "внимания, а не оценки.\n\n"
    "Работаю онлайн с взрослыми. Веду сессии бережно, "
    "без давления и спешки — так, чтобы с первой встречи "
    "вы чувствовали себя услышанным и в безопасности.\n\n"
    "Если вы здесь — значит, что-то важное уже просится к свету. "
    "Я буду рада пройти этот путь рядом с вами."
),

"values": (
    "🌟 Мои ценности и принципы\n\n"
    "Моя работа держится на нескольких фундаментальных принципах:\n\n"
    "🔒 Конфиденциальность\n"
    "Всё, что происходит на сессии, остаётся между нами. "
    "Это не только профессиональная этика — это моё личное обязательство.\n\n"
    "🛡 Безопасность\n"
    "Я не использую провокативные методы. "
    "Правило «стоп» действует всегда: вы можете остановить "
    "исследование любой темы в любой момент.\n\n"
    "🌿 Безоценочность\n"
    "На сессии нет правильного или неправильного. "
    "Значимы ваш опыт, ваш взгляд, ваша версия событий.\n\n"
    "🔑 Уважение к вашему пути\n"
    "Вы — главный эксперт своей жизни. "
    "Я не выдаю советов и не знаю лучше вас, как вам жить. "
    "Я помогаю услышать себя.\n\n"
    "✨ Постоянное развитие\n"
    "Я регулярно прохожу супервизию, участвую в интервизионных группах "
    "и нахожусь в личной терапии — чтобы быть для вас устойчивой опорой."
),

"approach": (
    "🧩 Мой подход к работе\n\n"
    "Я работаю интегративно: не один метод на все случаи жизни, "
    "а осознанное сочетание инструментов, которые подходят именно вам.\n\n"
    "Основные направления:\n\n"
    "📘 КПТ (когнитивно-поведенческая терапия)\n"
    "Помогает распознать мысли и убеждения, которые поддерживают тревогу, "
    "низкую самооценку или деструктивные паттерны, и шаг за шагом их трансформировать.\n\n"
    "📗 Гештальт-консультирование\n"
    "Работает с незавершёнными ситуациями прошлого, "
    "помогает восстановить контакт с чувствами и перестать жить «на автопилоте».\n\n"
    "📙 МАК (метафорические ассоциативные карты)\n"
    "Образный инструмент, который открывает доступ "
    "к глубинным переживаниям там, где слова ещё не найдены.\n\n"
    "Каждый человек уникален. Я не применяю шаблоны — "
    "я выстраиваю подход, который будет работать именно для вас."
),

"education": (
    "🎓 Опыт и образование\n\n"
    "🏛 Образование:\n"
    "— Магистр психологии (диплом государственного университета)\n"
    "— Дополнительная подготовка по КПТ и гештальт-консультированию\n"
    "— Обучение методам работы с агрессией\n"
    "— МАК в практике психолога\n"
    "— Работа с боевым ПТСР и семьями военнослужащих\n\n"
    "💼 Практический опыт:\n"
    "— Более 1,5 лет волонтёрской работы в фонде «НеТерпи»\n"
    "— Регулярные супервизии и интервизионные группы\n"
    "— Постоянная личная терапия\n\n"
    "Все дипломы и сертификаты готова предоставить по запросу. "
    "Мне важно, чтобы вы работали с проверенным специалистом."
),

"formats": (
    "💙 Форматы работы\n\n"
    "🖥 Онлайн-консультации (индивидуально)\n\n"
    "Сессии проходят в формате видеозвонка — "
    "из любой точки мира, в удобное для вас время.\n\n"
    "📌 Платформы: Яндекс.Телемост, MAX, WeChat\n\n"
    "💰 Стоимость:\n"
    "— Первая пробная сессия: 2 500 руб. / 60 минут\n"
    "— Последующие сессии: 5 000 руб. / 60 минут\n\n"
    "🗓 Запись за 24 часа по предоплате.\n\n"
    "📋 Как записаться — напишите мне:\n"
    "✔️ Имя\n"
    "✔️ Возраст\n"
    "✔️ Краткое описание запроса\n"
    "✔️ Удобное время (будни/выходные, утро/день/вечер по МСК)\n\n"
    f"📩 {CONTACT}"
),

# ═══ ЗАПРОСЫ — мини-статьи с CTA ══════════════════════════════════════════════

"relations": (
    "💔 Отношения\n\n"
    "Близкие люди должны быть источником тепла — но иногда именно они "
    "причиняют самую глубокую боль. Постоянные конфликты, ощущение "
    "одиночества рядом с партнёром, непонимание с родителями — всё это "
    "не норма, с которой нужно просто мириться.\n\n"
    "За каждым таким паттерном стоит что-то важное из прошлого: "
    "незакрытые обиды, усвоенные с детства роли, страх близости или "
    "отвержения. Когда мы находим это — отношения начинают меняться.\n\n"
    "На консультации мы разберём, что именно происходит в ваших "
    "отношениях, откуда это берётся и что можно изменить уже сейчас. "
    "Первый шаг часто оказывается проще, чем кажется.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

"anxiety": (
    "🌧 Тревога и страхи\n\n"
    "Тревога редко приходит одна. Она захватывает мысли, мешает спать, "
    "заставляет избегать людей и ситуаций — и постепенно сужает жизнь "
    "до маленького безопасного круга. Это изматывает.\n\n"
    "Хорошая новость: тревога поддаётся работе. Она не часть характера "
    "и не приговор — это выученная реакция психики, которую можно "
    "переучить. Иррациональные страхи, низкая самооценка, хроническое "
    "чувство вины — всё это меняется в процессе терапии.\n\n"
    "Если тревога уже давно управляет вашей жизнью — пришло время "
    "вернуть этот контроль себе. Я помогу разобраться, откуда она "
    "берётся, и найти путь к внутреннему спокойствию.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

"crisis": (
    "⚡ Кризисы и потери\n\n"
    "Развод, потеря работы, уход близкого, переезд, болезнь — есть "
    "события, после которых прежняя жизнь уже не возвращается. "
    "И это больно. Растерянность, пустота, ощущение, что земля ушла "
    "из-под ног — всё это нормальные реакции на ненормальные обстоятельства.\n\n"
    "Но оставаться с этим в одиночестве необязательно. В кризисе "
    "особенно важно иметь рядом того, кто не будет давать советов "
    "и торопить с «принятием» — а просто поможет устоять.\n\n"
    "Вместе мы найдём внутренние опоры, которые есть у вас даже сейчас, "
    "и постепенно выстроим дорогу к новому этапу. Кризис — это не конец "
    "истории. Иногда это её самая важная глава.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

"codependency": (
    "🔗 Созависимость\n\n"
    "Если в вашей семье были алкоголизм, насилие, постоянный хаос или "
    "эмоциональная холодность — вы, скорее всего, выросли с убеждением, "
    "что чужие потребности важнее ваших. Это называется созависимость, "
    "и она незаметно управляет отношениями, работой и самооценкой.\n\n"
    "Паттерны из дисфункциональной семьи воспроизводятся во взрослой "
    "жизни автоматически: вы спасаете, терпите, берёте на себя чужую "
    "ответственность — и не понимаете, почему снова оказываетесь в одном "
    "и том же сценарии.\n\n"
    "Это можно изменить. В работе со мной вы научитесь отличать свои "
    "границы от чужих, перестанете нести то, что вам не принадлежит, "
    "и откроете для себя, каково это — жить для себя, а не для других.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

"self_esteem": (
    "🌱 Самооценка\n\n"
    "«В жизни вроде всё есть, а внутри — пусто.» Это одна из самых "
    "частых фраз, с которыми приходят на консультацию. И за ней почти "
    "всегда стоит одно: человек живёт не своей жизнью.\n\n"
    "Низкая самооценка — это не врождённый дефект. Это результат "
    "усвоенных посланий: «ты недостаточно хорош», «не высовывайся», "
    "«твои желания не важны». Со временем они становятся внутренним "
    "голосом — и начинают управлять выборами, отношениями, карьерой.\n\n"
    "На сессиях мы найдём, откуда этот голос взялся, и начнём "
    "выстраивать новую опору — изнутри, а не из чужих ожиданий. "
    "Потому что устойчивая самооценка — это навык, которому можно научиться.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

"finding_self": (
    "🧭 Поиск себя\n\n"
    "Иногда человек просыпается и понимает: жизнь идёт, а ощущения, "
    "что она — его, нет. Правильная работа, правильные отношения, "
    "правильное поведение — но что-то важное потерялось по дороге.\n\n"
    "Поиск себя — это не инфантильный кризис и не роскошь. Это "
    "необходимость. Когда мы живём в отрыве от собственных ценностей "
    "и желаний, рано или поздно приходит усталость, пустота или "
    "ощущение чужой жизни.\n\n"
    "Вместе мы разберёмся, где вы потеряли себя, что действительно "
    "важно для вас — а не для родителей, общества или партнёра. "
    "И найдём путь обратно — к себе настоящему.\n\n"
    f"Запишитесь на первую сессию — {CONTACT}"
),

# ══════════════════════════════════════════════════════════════════════════════

"contacts": (
    "📩 Контакты\n\n"
    f"💬 Написать лично: {CONTACT}\n\n"
    f"👥 Канал и сообщество: {GROUP}\n\n"
    "Я отвечаю на сообщения в течение дня.\n"
    "Напишите — и мы вместе подберём удобное время для первой встречи 💙"
),

"anon_question": (
    "❓ Анонимный вопрос\n\n"
    "Иногда легче начать разговор анонимно — без имени и объяснений. "
    "Если вас что-то тревожит, но вы пока не готовы говорить открыто — "
    "воспользуйтесь анонимным ботом.\n\n"
    "Что можно написать:\n"
    "✔️ Описать ситуацию, которая беспокоит\n"
    "✔️ Спросить совет в сложном выборе\n"
    "✔️ Получить поддерживающий отклик, когда тяжело\n"
    "✔️ Разобрать чувства, которые сложно назвать вслух\n\n"
    "Бот доступен круглосуточно. "
    "Всё, что вы напишете, останется конфиденциальным.\n\n"
    f"👉 {ANON_BOT}"
),

"requests_section":  "С чем я работаю — выберите тему 👇",
"events_section":    "Выберите категорию 👇",
"no_past_streams":   "Прошедших эфиров пока нет. Следите за обновлениями! 🎥",
"no_upcoming":       "Запланированных событий пока нет. Следите за обновлениями! 📆",
"back_to_main":      "Вы вернулись в главное меню 👇",
"unknown":           "Пожалуйста, воспользуйтесь меню ниже 👇",
}

# ═══ РОУТИНГ ══════════════════════════════════════════════════════════════════

ROUTES = {
    "🪞 Обо мне":           ("about_section",    kb_about,    None),
    "💙 Форматы работы":    ("formats",           kb_main,     "signup_general"),
    "🌿 Запросы":           ("requests_section",  kb_requests, None),
    "📅 Эфиры / События":   ("events_section",    kb_events,   None),
    "📩 Контакты":          ("contacts",          kb_main,     None),
    "❓ Анонимный вопрос":  ("anon_question",     kb_main,     None),

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

    "🎥 Прошедшие эфиры":     ("no_past_streams", kb_events, None),
    "📆 Предстоящие события": ("no_upcoming",      kb_events, None),
}

SIGNUP_REPLIES = {
    "signup_general":      f"Отлично! Напишите мне, договоримся о времени:\n{CONTACT}",
    "signup_relations":    f"Готова работать с темой отношений. Напишите:\n{CONTACT}",
    "signup_anxiety":      f"Готова помочь с тревогой и страхами. Напишите:\n{CONTACT}",
    "signup_crisis":       f"Готова поддержать в кризисный период. Напишите:\n{CONTACT}",
    "signup_codependency": f"Готова работать с созависимостью. Напишите:\n{CONTACT}",
    "signup_self_esteem":  f"Готова помочь с самооценкой. Напишите:\n{CONTACT}",
    "signup_finding_self": f"Готова сопровождать вас на пути к себе. Напишите:\n{CONTACT}",
}

# ═══ ХЭНДЛЕРЫ ═════════════════════════════════════════════════════════════════

async def notify_admin(app, user):
    """Отправляет Зое уведомление о новом лиде."""
    if not ADMIN_ID:
        return
    try:
        username = f"@{user.username}" if user.username else "без username"
        name = user.full_name or "без имени"
        text = (
            f"🔔 Новый пользователь зашёл в бот!\n\n"
            f"👤 Имя: {name}\n"
            f"📎 Username: {username}\n"
            f"🆔 ID: {user.id}"
        )
        await app.bot.send_message(chat_id=int(ADMIN_ID), text=text)
    except Exception as e:
        logger.warning(f"Не удалось отправить уведомление админу: {e}")


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await notify_admin(ctx.application, update.effective_user)
    await update.message.reply_text(TEXTS["welcome"], reply_markup=kb_main())


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Убираем все виды пробелов и нормализуем текст
    raw = update.message.text or ""
    text = raw.strip()

    if text == "⬅️ Назад":
        await update.message.reply_text(TEXTS["back_to_main"], reply_markup=kb_main())
        return

    # Ищем точное совпадение, затем частичное (на случай разных emoji-вариантов)
    route = ROUTES.get(text)
    if route is None:
        for key in ROUTES:
            if key.strip() == text or text in key or key in text:
                route = ROUTES[key]
                break

    if route is None:
        await update.message.reply_text(TEXTS["unknown"], reply_markup=kb_main())
        return

    text_key, keyboard_fn, cb_data = route

    if cb_data:
        await update.message.reply_text(
            TEXTS[text_key],
            reply_markup=signup_btn(cb_data),
        )
        await update.message.reply_text(
            "Выберите следующий раздел 👇",
            reply_markup=keyboard_fn(),
        )
    else:
        await update.message.reply_text(
            TEXTS[text_key],
            reply_markup=keyboard_fn(),
        )


async def on_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает результат теста из мини-апп и уведомляет Зою."""
    data_str = update.effective_message.web_app_data.data
    user = update.effective_user
    try:
        data = json.loads(data_str)
        if data.get("action") == "quiz_result":
            name    = data.get("name", "не указано")
            profile = data.get("profile", "неизвестно")
            total   = data.get("total", "?")
            sc      = data.get("scores", {})

            # Ответ пользователю
            await update.message.reply_text(
                f"Ваш профиль сохранён: {profile} 💙\n\n"
                "Зоя уже видит ваш результат. Если хотите обсудить — напишите ей напрямую.",
                reply_markup=kb_main(),
            )

            # Уведомление Зое
            if ADMIN_ID:
                username = f"@{user.username}" if user.username else "без username"
                dim_lines = "\n".join(
                    f"  {k}: {v}" for k, v in sc.items()
                ) if sc else "—"
                msg = (
                    f"🧠 Новый результат теста!\n\n"
                    f"👤 Имя: {name}\n"
                    f"📎 Username: {username}\n"
                    f"🆔 ID: {user.id}\n\n"
                    f"📊 Профиль: {profile}\n"
                    f"🔢 Общий балл: {total}/36\n\n"
                    f"Измерения:\n{dim_lines}"
                )
                try:
                    await ctx.application.bot.send_message(
                        chat_id=int(ADMIN_ID), text=msg
                    )
                except Exception as e:
                    logger.warning(f"Admin notify failed: {e}")
    except Exception as e:
        logger.error(f"webapp data error: {e}")


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    reply = SIGNUP_REPLIES.get(query.data, f"Для записи напишите мне: {CONTACT}")
    await query.message.reply_text(reply)


# ═══ ЗАПУСК ═══════════════════════════════════════════════════════════════════

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не задан!")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    logger.info("Бот запущен.")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()


# ═══ ОБРАБОТЧИК ДАННЫХ ИЗ МИНИ-АПП «Карта внутреннего мира» ═══════════════════

import json as _json

AXIS_LABELS = {
    'anxiety':     '🌪 Тревога',
    'relations':   '🔗 Отношения',
    'self_esteem': '🪞 Самооценка',
    'meaning':     '🧭 Смысл',
    'boundaries':  '🛡 Границы',
    'somatic':     '🌿 Тело',
    'inner_child': '🌱 Детство',
    'crisis':      '⚡ Кризисы',
}

async def on_webapp_data(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получает результат теста из мини-апп и уведомляет Зою."""
    raw = update.effective_message.web_app_data.data
    user = update.effective_user

    try:
        data = _json.loads(raw)
    except Exception:
        return

    profile_name = data.get('profileName', '—')
    scores       = data.get('scores', {})

    # Строим текст для Зои
    scores_text = '\n'.join(
        f"  {AXIS_LABELS.get(k, k)}: {round((v/6)*100)}%"
        for k, v in scores.items()
    )

    username = f"@{user.username}" if user.username else "без username"
    admin_msg = (
        f"🗺 Новый результат теста!\n\n"
        f"👤 {user.full_name} ({username})\n"
        f"🆔 {user.id}\n\n"
        f"📊 Профиль: {profile_name}\n\n"
        f"Оси:\n{scores_text}"
    )

    if ADMIN_ID:
        try:
            await ctx.application.bot.send_message(int(ADMIN_ID), admin_msg)
        except Exception as e:
            logger.warning(f"Ошибка отправки уведомления: {e}")

    # Ответ пользователю
    user_msg = (
        f"✅ Ваш результат получен!\n\n"
        f"Профиль: *{profile_name}*\n\n"
        f"Зоя свяжется с вами в ближайшее время 💙\n\n"
        f"Написать прямо сейчас: {CONTACT}"
    )
    await update.effective_message.reply_text(user_msg, parse_mode="Markdown")


# Регистрируем хендлер — добавьте эту строку в функцию main() после других add_handler:
# app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, on_webapp_data))
