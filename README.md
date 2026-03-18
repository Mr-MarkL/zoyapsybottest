# Telegram-бот для психолога Зои Антонец

## Быстрый старт

### 1. Создайте бота в Telegram
- Напишите @BotFather команду `/newbot`
- Получите токен вида `123456789:ABCdef...`

### 2. Установите зависимости
```bash
pip install -r requirements.txt
```

### 3. Настройте переменные окружения
```bash
cp .env.example .env
# Откройте .env и вставьте ваш токен
```

### 4. (Опционально) Отредактируйте bot.py
Найдите блок `НАСТРОЙКИ` в начале файла и измените:
- `CONTACT` — Telegram-ник психолога (например `@zoia_antonets`)
- `SITE` — сайт
- `ANON_BOT_LINK` — ссылка на анонимного бота

### 5. Запустите
```bash
python bot.py
```

---

## Деплой на сервер (Ubuntu / Debian)

### Через systemd (рекомендуется)

Создайте файл сервиса:
```bash
sudo nano /etc/systemd/system/zoia-bot.service
```

Содержимое:
```ini
[Unit]
Description=Zoia Antonets Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/zoia-bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
RestartSec=5
EnvironmentFile=/home/ubuntu/zoia-bot/.env

[Install]
WantedBy=multi-user.target
```

Запустите:
```bash
sudo systemctl daemon-reload
sudo systemctl enable zoia-bot
sudo systemctl start zoia-bot
sudo systemctl status zoia-bot
```

Просмотр логов:
```bash
sudo journalctl -u zoia-bot -f
```

---

## Структура бота

```
/start         — приветствие + главное меню

🪞 Обо мне
  ├── 🧭 Кто я и мой путь
  ├── 🌟 Ценности и принципы
  ├── 🧩 Подход к работе
  └── 🎓 Опыт и образование

💙 Форматы работы   — стоимость и условия

🌿 Запросы
  ├── 💔 Отношения
  ├── 🌧️ Тревога и страхи
  ├── ⚡ Кризисы и потери
  ├── 🔗 Созависимость
  ├── 🌱 Самооценка
  └── 🧭 Поиск себя

📅 Эфиры / События
  ├── 🎥 Прошедшие эфиры
  └── 📆 Предстоящие события

📩 Контакты
❓ Анонимный вопрос
```

## Изменение текстов
Все тексты хранятся в словаре `TEXTS` в файле `bot.py`.
Найдите нужный ключ и отредактируйте значение.

## Добавление новых разделов
1. Добавьте текст в словарь `TEXTS`
2. Добавьте кнопку в нужную клавиатуру (`kb_*` функции)
3. Добавьте запись в словарь `ROUTES`
