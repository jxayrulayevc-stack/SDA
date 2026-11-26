# Steam Guard Telegram Bot

Аналог Steam Desktop Authenticator в Telegram: бот выдаёт Steam Guard-коды для
нескольких аккаунтов по загруженным `.maFile`. Работает через long polling —
входящие порты не нужны.

**Репозиторий публичный. Никаких секретов в нём нет и быть не должно.**
Все секреты создаются вручную на сервере и хранятся вне каталога репозитория.

## Возможности

- `/start`, `/help` — справка;
- `/accounts` — inline-список аккаунтов; нажатие на логин показывает текущий код;
- кнопка «🔄 Обновить» в сообщении с кодом;
- `/code <логин>` — быстрый доступ к коду;
- отправка `.maFile`/`.json` — добавление аккаунта (файл удаляется из чата);
- `/delete` — удаление с подтверждением;
- синхронизация времени с Steam (`QueryTime`) при старте и раз в час, fallback на системное время;
- автоудаление сообщения с кодом через `CODE_TTL_SECONDS` (по умолчанию 60 сек);
- доступ только для администраторов из `ADMIN_IDS`, остальные обновления игнорируются;
- rate limit на запросы кодов.

Алгоритм генерации реализован самостоятельно (`core/steam_guard.py`), без Steam-библиотек.

## Структура

```
bot/        aiogram-хендлеры, middleware, клавиатуры (только вызовы services)
core/       генерация кода и синхронизация времени
storage/    SQLite-репозиторий и Fernet-шифрование
services/   бизнес-логика, не зависит от Telegram (готово к будущему API)
scripts/    генерация ключа, проверка на секреты
tests/      pytest
```

## Установка на Ubuntu 24.04

```bash
# как пользователь ubuntu
cd /home/ubuntu
git clone <URL-вашего-публичного-репозитория> steam-guard-bot
cd steam-guard-bot
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
chmod +x deploy.sh
git config core.hooksPath .githooks
```

### Каталог данных и конфиг

```bash
sudo mkdir -p /home/ubuntu/steam-guard-bot-data
sudo chown ubuntu:ubuntu /home/ubuntu/steam-guard-bot-data
chmod 700 /home/ubuntu/steam-guard-bot-data
cp .env.example /home/ubuntu/steam-guard-bot-data/.env
chmod 600 /home/ubuntu/steam-guard-bot-data/.env
```

Заполните `/home/ubuntu/steam-guard-bot-data/.env` вручную:

- `BOT_TOKEN` — токен, выданный @BotFather;
- `ADMIN_IDS` — Telegram ID администраторов через запятую;
- `ENCRYPTION_KEY` — сгенерированный ключ (см. ниже);
- `CODE_TTL_SECONDS` — время жизни сообщения с кодом.

Значения из задания/личные данные **не следует записывать в репозиторий, README,
коммиты или тесты** — только в этот файл на сервере.

Генерация ключа шифрования (вывод никуда не копируйте, кроме `.env`):

```bash
.venv/bin/python scripts/generate_key.py
```

При старте бот проверяет права `.env` и БД и пишет предупреждение в журнал,
если права отличаются от `600`.

### systemd

```bash
sudo cp steam-guard-bot.service /etc/systemd/system/steam-guard-bot.service
sudo systemctl daemon-reload
sudo systemctl enable steam-guard-bot
sudo systemctl start steam-guard-bot
sudo systemctl status steam-guard-bot --no-pager
sudo journalctl -u steam-guard-bot -n 20 --no-pager
```

`enable` включает автозапуск после перезагрузки VM. Сервис изолирован: свой venv,
свой токен, свои данные, `Restart=always`, `MemoryMax=200M`. Другие боты
(FunPay и т.д.) не затрагиваются.

Обновление:

```bash
./deploy.sh
```

### Первый аккаунт

1. Откройте чат с ботом как администратор.
2. Отправьте файл `.maFile` (или `.json`) documents-сообщением.
3. Бот проверит структуру, зашифрует всё содержимое, сохранит запись, удалит
   сообщение с файлом и ответит «Аккаунт <логин> добавлен».
4. `/accounts` → нажмите на логин → получите код и остаток секунд.
5. При повторной отправке того же логина бот спросит, заменить ли запись.

Файл принимается только с расширением `.maFile`/`.json` и размером до 100 КБ.
Содержимое файла и секреты никогда не попадают в ответы бота или в логи.

## Безопасность

- **Всё содержимое maFile шифруется Fernet** (`ENCRYPTION_KEY` только на сервере).
  В открытом виде в БД хранится только логин — он нужен для списка аккаунтов.
- `.env`, БД и ключ находятся **только на VM**, в
  `/home/ubuntu/steam-guard-bot-data` (вне репозитория). Права: каталог `700`,
  файлы `600`. `git clone/pull` не приносит секреты на сервер — их создают вручную.
- `.gitignore` исключает `.env`, `*.env`, `data/`, `*.db`, `*.sqlite*`,
  `*.maFile`, `*.key`, `*.pem`, логи и кэши.
- Pre-commit хук (`git config core.hooksPath .githooks`) запускает
  `scripts/check_secrets.py` и блокирует коммит с паттернами токена Telegram,
  `shared_secret`, `identity_secret`, `revocation_code`, Fernet-ключом и
  запрещёнными файлами. Полная проверка дерева:
  `python3 scripts/check_secrets.py --all`.
- Логирование: только логин аккаунта и действие. Секреты, maFile и коды в логи
  не пишутся.
- Rate limit: не более `CODE_RATE_LIMIT` запросов кодов за `RATE_LIMIT_WINDOW`
  секунд на администратора (по умолчанию 10/60).

### Backup зашифрованной БД

Бэкап — это пара: зашифрованная БД **и** `ENCRYPTION_KEY` (ключ хранится отдельно
и надёжно, например в менеджере паролей). Копию БД можно делать на работающем
сервисе (`sqlite3 accounts.db ".backup ..."` или `cp`), но файл должен оставаться
с правами `600`. Без ключа восстановление невозможно; потеря ключа означает
необходимость заново импортировать maFile.

### При утечке

- **Утёк токен бота:** немедленно перевыпустите токен через @BotFather, обновите
  `BOT_TOKEN` в `.env` на сервере и перезапустите сервис. Удалите токен из всех
  чатов/логов/истории, где он мог появиться.
- **Утёк `ENCRYPTION_KEY` или maFile:** считайте аккаунты скомпрометированными.
  Сгенерируйте новый ключ, вставьте его в `.env`, удалите старую БД и
  переимпортируйте maFile заново (при необходимости с новыми секретами Steam).
  Старые зашифрованные записи с новым ключом не расшифруются.
- **Секрет попал в git:** после удаления из файла случайно попавший секрет
  остаётся в истории коммитов — ротируйте credentials и очищайте историю.
- Сообщите об уязвимости по инструкции в [SECURITY.md](SECURITY.md).

## Будущее HTTP API

Слои разделены: `services/` не знает о Telegram, поэтому HTTP API сможет
использовать те же `AccountService`, `Encryptor` и `SteamTimeSync`. API должен
слушать только `127.0.0.1` и выставляться наружу через reverse proxy с токеном.
Сейчас API не реализован.

## Тесты

```bash
.venv/bin/pytest
python3 scripts/check_secrets.py --all
```

Лицензия: MIT (см. [LICENSE](LICENSE)).
