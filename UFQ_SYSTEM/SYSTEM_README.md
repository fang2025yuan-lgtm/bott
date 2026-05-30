# UFQ UNIFIED SYSTEM

## Tizim Haqida (About the System)

UFQ UNIFIED SYSTEM - bu ikki Telegram botni birlashtirgan yagona platforma:

- **Team Bot** - Jamoalar, a'zolar, vazifalar, taklifnomalar boshqaruvi
- **Event Bot** - Tadbirlar, ro'yxatdan o'tish, chipta generatsiya, QR skanerlash

Ikkala bot **bitta SQLite ma'lumotlar bazasidan** foydalanadi. Bu yondashuv foydalanuvchilarning jamoalararo tadbirlarda ishtirok etishini ta'minlaydi.

---

## Arxitektura (Architecture)

```
+-------------------+         +-------------------------+         +-------------------+
|                   |         |                         |         |                   |
|   UFQ TEAM BOT    |         |    SHARED DATABASE      |         |  UFQ EVENT BOT    |
|                   |         |                         |         |                   |
|  - Jamoa yaratish |  <----> |  ufq_system.db          | <---->  |  - Tadbir yaratish|
|  - A'zo qo'shish  |         |                         |         |  - Ro'yxatdan     |
|  - Vazifa berish  |         |  Jadvallar:             |         |    o'tish         |
|  - CP tayinlash   |         |  - clubs                |         |  - Chipta olish   |
|  - Taklifnoma     |         |  - users                |         |  - QR skanerlash  |
|  - Hisobot        |         |  - roles                |         |  - Ball to'plash  |
|                   |         |  - invites              |         |  - Reyting         |
|  Texnologiya:     |         |  - tasks                |         |                   |
|  - aiogram 3.4    |         |  - task_submissions     |         |  Texnologiya:     |
|  - aiosqlite      |         |  - events               |         |  - aiogram 3.4    |
|  - Redis FSM      |         |  - registrations        |         |  - SQLAlchemy 2.0 |
|                   |         |  - tickets              |         |  - aiosqlite      |
+-------------------+         +-------------------------+         +-------------------+
        |                                                                   |
        |                     +-------------------+                         |
        +-------------------> |   Redis Server    | <-----------------------+
                              | (FSM storage -    |   (Event bot: memory FSM)
                              |  team bot only)   |
                              +-------------------+
```

### Fayl Tuzilmasi

```
/home/ubuntu/UFQ_SYSTEM/
|-- team_bot/
|   |-- bot/
|   |   |-- __init__.py
|   |   |-- config.py          # BOT_TOKEN, ADMIN_ID, DB_PATH
|   |   |-- main.py            # Botni ishga tushirish
|   |   |-- database/
|   |   |   |-- __init__.py
|   |   |   |-- db.py          # aiosqlite CRUD + migration
|   |   |-- handlers/
|   |   |   |-- __init__.py
|   |   |   |-- start.py       # /start buyrug'i
|   |   |   |-- admin.py       # Admin paneli
|   |   |   |-- cp.py          # Club President funksiyalari
|   |   |   |-- member.py      # A'zo funksiyalari
|   |   |-- keyboards/
|   |       |-- __init__.py
|   |       |-- reply.py       # Reply tugmalar
|   |       |-- inline.py      # Inline tugmalar
|   |-- requirements.txt
|   |-- .env
|   |-- venv/
|
|-- event_bot/
|   |-- bot/
|   |   |-- __init__.py
|   |   |-- config.py          # BOT_TOKEN, SUPER_ADMIN_ID, DB_PATH
|   |   |-- main.py            # Botni ishga tushirish
|   |   |-- database/
|   |   |   |-- __init__.py
|   |   |   |-- db.py          # SQLAlchemy engine
|   |   |   |-- models.py      # Event, Registration, Ticket
|   |   |   |-- crud.py        # CRUD (raw SQL + SQLAlchemy)
|   |   |-- handlers/
|   |   |   |-- __init__.py
|   |   |   |-- start.py       # /start + ro'yxatdan o'tish
|   |   |   |-- admin.py       # Admin/CP panel
|   |   |   |-- events.py      # Tadbirlar ro'yxati
|   |   |   |-- user.py        # Foydalanuvchi profili
|   |   |   |-- scanner.py     # QR skanerlash
|   |   |-- keyboards/
|   |   |   |-- __init__.py
|   |   |   |-- menus.py       # Tugmalar
|   |   |-- middlewares/
|   |   |   |-- __init__.py
|   |   |   |-- check_sub.py   # Kanal obuna tekshiruvi
|   |   |-- utils/
|   |       |-- __init__.py
|   |       |-- ticket_generator.py  # Chipta rasm generatsiya
|   |       |-- status_manager.py    # Ball/status hisoblash
|   |-- requirements.txt
|   |-- .env
|   |-- venv/
|
|-- shared/
|   |-- ufq_system.db          # Umumiy SQLite baza
|
|-- SYSTEM_README.md
|-- deploy.sh
```

---

## Ma'lumotlar Bazasi Sxemasi (Database Schema)

### `clubs` jadvali (Team Bot yaratadi)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| name | TEXT NOT NULL | Klub nomi |
| description | TEXT | Tavsif |
| created_at | TEXT | Yaratilgan sana |

### `roles` jadvali (Team Bot yaratadi)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| club_id | INTEGER | Klub ID (FK -> clubs) |
| name | TEXT NOT NULL | Rol nomi |

### `users` jadvali (Ikkala bot foydalanadi)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| telegram_id | INTEGER UNIQUE | Telegram ID |
| full_name | TEXT | To'liq ism |
| club_id | INTEGER | Klub ID (FK -> clubs) |
| role_id | INTEGER | Rol ID (FK -> roles) |
| is_cp | INTEGER DEFAULT 0 | Club President (1=ha, 0=yo'q) |
| joined_at | TEXT | Qo'shilgan sana |
| total_points | INTEGER DEFAULT 0 | Umumiy ballar (Event Bot yozadi) |
| user_status | TEXT DEFAULT 'BRONZE' | Status: BRONZE/SILVER/GOLD/PLATINUM |
| username | TEXT | Telegram username |

### `invites` jadvali (Team Bot)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| club_id | INTEGER | Klub ID |
| code | TEXT UNIQUE | Taklifnoma kodi |
| created_by | INTEGER | Yaratuvchi (telegram_id) |
| used_by | INTEGER | Ishlatuvchi (telegram_id) |
| created_at | TEXT | Yaratilgan sana |
| used_at | TEXT | Ishlatilgan sana |

### `tasks` jadvali (Team Bot)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| club_id | INTEGER | Klub ID |
| title | TEXT | Vazifa sarlavhasi |
| description | TEXT | Tavsif |
| deadline | TEXT | Muddat |
| created_by | INTEGER | Yaratuvchi |
| created_at | TEXT | Yaratilgan sana |
| status | TEXT DEFAULT 'active' | Holat |

### `task_submissions` jadvali (Team Bot)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| task_id | INTEGER | Vazifa ID (FK -> tasks) |
| user_id | INTEGER | Foydalanuvchi telegram_id |
| submitted_at | TEXT | Topshirilgan sana |
| file_id | TEXT | Telegram fayl ID |
| status | TEXT DEFAULT 'pending' | Holat: pending/approved/rejected |
| reviewed_by | INTEGER | Tekshiruvchi |
| reviewed_at | TEXT | Tekshirilgan sana |

### `events` jadvali (Event Bot yaratadi)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| title | TEXT NOT NULL | Tadbir nomi |
| description | TEXT | Tavsif |
| date | TEXT | Sana |
| location | TEXT | Joy |
| max_participants | INTEGER | Maksimal ishtirokchilar |
| club_id | INTEGER | Klub ID (tashkilotchi klub) |
| created_by | INTEGER | Yaratuvchi telegram_id |
| status | TEXT DEFAULT 'upcoming' | Holat: upcoming/ongoing/completed/cancelled |
| points | INTEGER DEFAULT 10 | Beriluvchi ball |
| created_at | TEXT | Yaratilgan sana |

### `registrations` jadvali (Event Bot)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| user_id | INTEGER | Foydalanuvchi telegram_id |
| event_id | INTEGER | Tadbir ID (FK -> events) |
| status | TEXT DEFAULT 'registered' | Holat: registered/attended/cancelled |
| registered_at | TEXT | Ro'yxatdan o'tgan sana |

### `tickets` jadvali (Event Bot)

| Ustun | Tur | Tavsif |
|-------|-----|--------|
| id | INTEGER PRIMARY KEY | Avtomatik ID |
| user_id | INTEGER | Foydalanuvchi telegram_id |
| event_id | INTEGER | Tadbir ID (FK -> events) |
| ticket_code | TEXT UNIQUE | Chipta kodi (UUID) |
| qr_data | TEXT | QR ma'lumotlari |
| is_used | INTEGER DEFAULT 0 | Ishlatilganmi |
| created_at | TEXT | Yaratilgan sana |

---

## Botlar Orasidagi Bog'lanish (Connection Between Bots)

### Ma'lumot Oqimi (Data Flow)

1. **Team Bot jamoalarni yaratadi** -> `clubs` jadvaliga yozadi
2. **Team Bot foydalanuvchilarni qo'shadi** -> `users` jadvaliga yozadi
3. **Event Bot klublarni o'qiydi** -> `clubs` jadvalidan SELECT qiladi
4. **Event Bot foydalanuvchilarni tekshiradi** -> `users` jadvalidan SELECT qiladi
5. **Event Bot ballarni yozadi** -> `users.total_points` ni UPDATE qiladi
6. **Team Bot ballarni ko'rsatadi** -> `users.total_points` ni SELECT qiladi

### Rollar Sinxronizatsiyasi

| Team Bot Holati | Event Bot Roli | Qanday aniqlanadi |
|-----------------|----------------|-------------------|
| `ADMIN_ID` (config) | SUPER_ADMIN | `SUPER_ADMIN_ID == telegram_id` |
| `is_cp = 1` (users jadvali) | PRESIDENT | `SELECT is_cp FROM users WHERE telegram_id=?` |
| Oddiy a'zo | USER | Yuqoridagilardan hech biri emas |

### Muhim Qoidalar

- **ADMIN_ID** = **SUPER_ADMIN_ID**: Ikkala botda bir xil admin
- **is_cp=1** bo'lgan foydalanuvchi avtomatik ravishda Event Botda tadbir yarata oladi
- **Har qanday foydalanuvchi** (hatto boshqa klubdan) **har qanday tadbirga** yozilishi mumkin
- **Ballar** Event Bot tomonidan yoziladi, lekin ikkala botda ko'rinadi
- **Status** (BRONZE/SILVER/GOLD/PLATINUM) ballar asosida hisoblanadi

### Ball -> Status Jadvali

| Status | Ball Oralig'i |
|--------|--------------|
| BRONZE | 0 - 15 ball |
| SILVER (Kumush) | 16 - 50 ball |
| GOLD (Oltin) | 51 - 120 ball |
| PLATINUM | 121+ ball |

---

## Rollar Xaritasi (Role Mapping)

```
+----------------------------+-----------------------------+
|       TEAM BOT             |        EVENT BOT            |
+----------------------------+-----------------------------+
| ADMIN_ID (config.py)       | SUPER_ADMIN                |
| - Barcha klublarni boshqar | - Barcha tadbirlarni boshqar|
| - CP tayinlash             | - Statistika ko'rish       |
| - Hisobotlar               | - Har qanday tadbir yaratish|
+----------------------------+-----------------------------+
| is_cp = 1 (users jadvali) | PRESIDENT                  |
| - O'z klubini boshqarish   | - O'z klubi uchun tadbir   |
| - A'zolarga vazifa berish  |   yaratish                 |
| - Taklifnoma yaratish      | - Ishtirokchilarni boshqar |
+----------------------------+-----------------------------+
| Oddiy a'zo                 | USER                       |
| - Vazifalarni bajarish     | - Tadbirlarga yozilish     |
| - Profil ko'rish           | - Chipta olish             |
|                            | - QR ko'rsatish            |
+----------------------------+-----------------------------+
```

---

## Deploy Qo'llanmasi (Deploy Guide)

### Talab Qilinadigan Narsalar

- Ubuntu 20.04+ server
- Python 3.10+
- sudo huquqlari
- Telegram Bot API tokenlar (BotFather orqali olinadi)
- Internet ulash (paketlar o'rnatish uchun)

### 1-Qadam: Fayllarni serverga yuklash

```bash
# ZIP faylni serverga ko'chirish
scp UFQ_SYSTEM.zip ubuntu@SERVER_IP:~/

# Serverga kirish
ssh ubuntu@SERVER_IP

# Arxivni ochish
unzip UFQ_SYSTEM.zip
cd UFQ_SYSTEM
```

### 2-Qadam: Deploy skriptini ishga tushirish

```bash
chmod +x deploy.sh
./deploy.sh
```

### 3-Qadam: So'ralgan ma'lumotlarni kiritish

1. **Team Bot Token** - BotFatherdan olingan Team Bot tokeni
2. **Event Bot Token** - BotFatherdan olingan Event Bot tokeni
3. **Admin Telegram ID** - Bosh admin (sizning) Telegram ID raqamingiz
4. **Event Bot Username** - Event bot username (@ belgisisiz)
5. **Majburiy kanallar** - Obuna tekshiruvi uchun kanallar (masalan: @kanal1,@kanal2)

### 4-Qadam: Tekshirish

```bash
# Botlar holatini tekshirish
sudo systemctl status ufq-team-bot
sudo systemctl status ufq-event-bot

# Loglarni kuzatish
sudo journalctl -u ufq-team-bot -f
sudo journalctl -u ufq-event-bot -f
```

---

## Muammolarni Hal Qilish (Troubleshooting)

### Bot ishga tushmayapti

```bash
# Loglarni tekshiring
sudo journalctl -u ufq-team-bot -n 50 --no-pager
sudo journalctl -u ufq-event-bot -n 50 --no-pager

# .env faylni tekshiring
cat /home/ubuntu/UFQ_SYSTEM/team_bot/.env
cat /home/ubuntu/UFQ_SYSTEM/event_bot/.env
```

### "Token invalid" xatoligi

- BotFatherdan yangi token oling
- .env fayldagi tokenni yangilang:
```bash
nano /home/ubuntu/UFQ_SYSTEM/team_bot/.env
sudo systemctl restart ufq-team-bot
```

### "Database is locked" xatoligi

Bu ikkala bot bir vaqtda bazaga yozmoqchi bo'lganda sodir bo'lishi mumkin. SQLite WAL rejimi bu muammoni kamaytiradi. Agar davom etsa:

```bash
# Ikkala botni to'xtating
sudo systemctl stop ufq-team-bot
sudo systemctl stop ufq-event-bot

# Bazani tekshiring
sqlite3 /home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db "PRAGMA integrity_check;"

# Botlarni qayta ishga tushiring
sudo systemctl start ufq-team-bot
sudo systemctl start ufq-event-bot
```

### Redis ulanmayapti (Team Bot)

```bash
# Redis holatini tekshiring
sudo systemctl status redis-server

# Redis qayta ishga tushiring
sudo systemctl restart redis-server
sudo systemctl restart ufq-team-bot
```

### Bazani qo'lda tiklash

```bash
# Zaxiralar ro'yxati
ls -la /home/ubuntu/ufq_db_backup/

# Tiklash
sudo systemctl stop ufq-team-bot
sudo systemctl stop ufq-event-bot
cp /home/ubuntu/ufq_db_backup/ufq_system_YYYYMMDD_HHMMSS.db \
   /home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db
sudo systemctl start ufq-team-bot
sudo systemctl start ufq-event-bot
```

### Event Bot klublarni ko'rmayapti

Event Bot klublarni to'g'ridan-to'g'ri `clubs` jadvalidan o'qiydi. Agar klublar ko'rinmasa:

```bash
# Bazada klublar borligini tekshiring
sqlite3 /home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db "SELECT * FROM clubs;"
```

Agar bo'sh bo'lsa, avval Team Bot orqali klub yarating.

### Yangilash (Update)

```bash
# Botlarni to'xtating
sudo systemctl stop ufq-team-bot
sudo systemctl stop ufq-event-bot

# Yangi fayllarni ko'chiring (bazani o'chirmang!)
cp -r /yangi/joy/team_bot/bot/* /home/ubuntu/UFQ_SYSTEM/team_bot/bot/
cp -r /yangi/joy/event_bot/bot/* /home/ubuntu/UFQ_SYSTEM/event_bot/bot/

# Botlarni qayta ishga tushiring
sudo systemctl restart ufq-team-bot
sudo systemctl restart ufq-event-bot
```

---

## Texnik Tafsilotlar (Technical Details)

### Texnologiyalar

| Komponent | Team Bot | Event Bot |
|-----------|----------|-----------|
| Framework | aiogram 3.4.1 | aiogram 3.4.1 |
| Database Driver | aiosqlite 0.20.0 | SQLAlchemy 2.0.25 + aiosqlite |
| FSM Storage | Redis 5.0.1 | Memory (default) |
| Env Management | python-dotenv 1.0.1 | python-dotenv 1.0.1 |
| QR/Ticket | - | qrcode 7.4.2 + Pillow 10.2.0 |
| Python | 3.10+ | 3.10+ |

### Baza Ulanishi

- **Team Bot**: To'g'ridan-to'g'ri `aiosqlite.connect(DB_PATH)` orqali
- **Event Bot**: SQLAlchemy async engine (`sqlite+aiosqlite:///DB_PATH`) + ba'zi so'rovlar uchun raw `aiosqlite`

### Xavfsizlik

- Bot tokenlari `.env` fayllarida saqlanadi (gitda emas)
- Admin ID faqat config orqali o'rnatiladi
- Foydalanuvchilar faqat o'z klubidagi vazifalarga kirishi mumkin
- Tadbirlar uchun kanal obuna tekshiruvi mavjud

### Ma'lumotlar Bazasi Xususiyatlari

- **SQLite WAL rejimi**: Bir vaqtda o'qish/yozish imkoniyati
- **Migration**: Team Bot ishga tushganda avtomatik `ALTER TABLE` orqali yangi ustunlar qo'shiladi
- **Backup**: Deploy skripti avtomatik zaxira oladi

---

## Tez-tez So'raladigan Savollar (FAQ)

**S: Ikkala bot uchun bitta token ishlatsa bo'ladimi?**
J: Yo'q. Har bir bot uchun alohida token kerak. BotFatherda ikkita bot yarating.

**S: Agar Team Bot to'xtasa, Event Bot ishlashda davom etadimi?**
J: Ha. Ikkala bot mustaqil ishlaydi. Faqat bazadagi ma'lumotlarni ulashadi.

**S: Yangi klub qo'shsam, Event Botda avtomatik ko'rinadimi?**
J: Ha. Event Bot har safar klublar ro'yxatini so'raganda bazadan yangi ma'lumot oladi.

**S: CP (Club President) qanday tayinlanadi?**
J: Team Bot admin paneli orqali. Admin foydalanuvchini CP qilganda, `users.is_cp = 1` bo'ladi va Event Botda avtomatik PRESIDENT huquqi beriladi.

**S: Ball (points) qanday ishlaydi?**
J: Foydalanuvchi tadbirga borsa va QR skaner orqali tasdiqlansa, `users.total_points` ga tadbir balli qo'shiladi. Bu ikkala botda ko'rinadi.
