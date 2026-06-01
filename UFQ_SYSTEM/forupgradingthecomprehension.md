# UFQ UNIFIED SYSTEM — TO'LIQ TIZIM HUJJATI
## forupgradingthecomprehension

---

## 1. UMUMIY TUSHUNCHA

UFQ Unified System — bu **2 ta Telegram bot** dan iborat birlashtirilgan tizim:

| Bot | Vazifasi | Token |
|-----|----------|-------|
| **UFQ Team Bot** | Jamoa boshqaruvi: klublar, a'zolar, vazifalar, taklifnomalar | Alohida token |
| **UFQ Event Bot** | Tadbirlar boshqaruvi: tadbir yaratish, ro'yxatdan o'tish, QR chipta, skanerlash, ball berish | Alohida token |

**Asosiy g'oya:** Ikkala bot **bitta SQLite baza** (`ufq_system.db`) dan foydalanadi. Team Bot foydalanuvchilar va klublarni yaratadi, Event Bot o'sha ma'lumotlarni o'qiydi va tadbirlar uchun ishlatadi.

---

## 2. ARXITEKTURA DIAGRAMMASI

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SERVERDA ISHLAYDI                             │
│                                                                     │
│  ┌─────────────────┐         ┌──────────────────┐                  │
│  │   TEAM BOT      │         │    EVENT BOT     │                  │
│  │   (Process 1)   │         │    (Process 2)   │                  │
│  │                 │         │                  │                  │
│  │ aiogram 3.4     │         │ aiogram 3.4      │                  │
│  │ aiosqlite       │         │ SQLAlchemy 2.0   │                  │
│  │ Redis (FSM)     │         │ aiosqlite (raw)  │                  │
│  └────────┬────────┘         └────────┬─────────┘                  │
│           │                           │                            │
│           │     ┌─────────────────┐   │                            │
│           └────>│  ufq_system.db  │<──┘                            │
│                 │  (SHARED DB)    │                                 │
│                 │                 │                                 │
│                 │  Jadvallar:     │                                 │
│                 │  - clubs        │  <-- Team Bot yozadi            │
│                 │  - users        │  <-- Ikkala bot yozadi          │
│                 │  - roles        │  <-- Team Bot yozadi            │
│                 │  - invites      │  <-- Team Bot yozadi            │
│                 │  - tasks        │  <-- Team Bot yozadi            │
│                 │  - task_subs    │  <-- Team Bot yozadi            │
│                 │  - events       │  <-- Event Bot yozadi           │
│                 │  - registrations│  <-- Event Bot yozadi           │
│                 │  - tickets      │  <-- Event Bot yozadi           │
│                 └─────────────────┘                                 │
│                                                                     │
│  ┌─────────────────┐                                               │
│  │   Redis Server   │  <-- Team Bot FSM storage                    │
│  └─────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. TEAM BOT — TO'LIQ FUNKSIYALAR

### 3.1 Rollar

| Rol | Kim | Nima qila oladi |
|-----|-----|-----------------|
| **Bosh Prezident (BP)** | ADMIN_ID dagi shaxs | Hammani boshqaradi: klublar ochish/yopish, CP tayinlash, hamma a'zolarni ko'rish, hamma a'zolarni chiqarish, umumiy vazifa berish, umumiy xabar yuborish |
| **Club President (CP)** | Invite orqali tayinlangan | O'z klubidagi a'zolarni boshqarish, lavozim yaratish, vazifa berish, xabar yuborish, invite link berish |
| **A'zo (Member)** | Invite orqali kirgan | Vazifalarni bajarish, profil ko'rish, leaderboard, prezidentga xat yozish |

### 3.2 Kirish Tizimi

Tizimga faqat **invite link** orqali kiriladi:
1. BP admin panelda klubni tanlaydi → CP invite link yaratiladi
2. CP invite linkni tanlangan odamga yuboradi
3. Odam `/start {invite_code}` bosadi → tizimga qo'shiladi

Invite bir martalik — ishlatilgandan keyin yana ishlamaydi.

### 3.3 BP (Bosh Prezident) Funksiyalari

| Tugma/Komanda | Nima qiladi |
|---------------|-------------|
| **Klublar** | Barcha klublarni ko'rsatadi. Nomini o'zgartirish, o'chirish, yangi klub qo'shish mumkin |
| **Taklifnoma (Invite)** | Tanlangan klub uchun CP invite link yaratadi |
| **Barcha a'zolar** | Har bir klubdagi a'zolarni ko'rsatadi. Chiqarish (kick) mumkin |
| **Jamoa statistikasi** | Umumiy: nechta klub, nechta a'zo, nechta vazifa |
| **Xabar yuborish** | Butun jamoaga yoki faqat CP larga ommaviy xabar |
| **Topshiriq berish** | Butun jamoaga yoki faqat CP larga vazifa. Javoblarni ko'rib qabul/rad qiladi |
| **Sozlamalar** | Admin ID va boshqa ma'lumotlar |

### 3.4 CP (Club President) Funksiyalari

| Tugma/Komanda | Nima qiladi |
|---------------|-------------|
| **Lavozimlar** | Klub ichida lavozim (rol) yaratish/o'chirish. Masalan: Mentor, Designer |
| **Jamoa yig'ish** | A'zo invite link yaratish (lavozim bilan yoki oddiy a'zo sifatida) |
| **Mening Jamoam** | Klubdagi barcha a'zolarni ko'rsatish (ism, lavozim, ball) |
| **Ommaviy xabar** | O'z klubi a'zolariga xabar yuborish |
| **Topshiriq berish** | O'z klubi a'zolariga (hammaga yoki bitta shaxsga) vazifa. Javoblarni ko'rib qabul/rad qilish (+10 ball) |
| **Bergan topshiriqlarim** | O'zi yaratgan vazifalar ro'yxati |

### 3.5 A'zo (Member) Funksiyalari

| Tugma/Komanda | Nima qiladi |
|---------------|-------------|
| **Mening Lavozimim** | Ism, lavozim, ball ko'rsatadi |
| **Topshiriqlarim** | Faol topshiriqlar ro'yxati. Har biriga dalil yuborib javob berish mumkin |
| **Liderlar taxtasi** | Klub ichidagi TOP-10 (ball bo'yicha) |
| **Prezidentga xat** | CP ga shaxsiy xabar yuborish |

### 3.6 Vazifa (Task) Tizimi

1. BP yoki CP vazifa yaratadi (sarlavha + tavsif)
2. Tegishli a'zolarga bildirishnoma yuboriladi
3. A'zo "Topshiriqlarim" dan vazifani ko'radi
4. A'zo dalil/javob matnini yozib yuboradi
5. BP/CP xabar oladi: "Qabul qilish (+10 ball)" yoki "Rad etish"
6. Qabul qilinsa: a'zoning `score` va `total_points` ga +10 qo'shiladi, `user_status` yangilanadi
7. Rad etilsa: a'zo qayta urinishi mumkin

---

## 4. EVENT BOT — TO'LIQ FUNKSIYALAR

### 4.1 Rollar (Team Bot dan avtomatik olinadi)

| Event Bot da | Qanday aniqlanadi | Nima qila oladi |
|---|---|---|
| **SUPER_ADMIN** | `telegram_id == SUPER_ADMIN_ID` (.env) | Har qanday tadbir yaratish, barcha klublar tadbirini boshqarish, har qanday QR skanerlash |
| **PRESIDENT** | `is_cp = 1` (users jadvalida) | Faqat o'z klubi uchun tadbir yaratish, o'z klubi tadbirini boshqarish, o'z klubi chiptalarini skanerlash |
| **USER** | Boshqa hamma | Tadbirlarga ro'yxatdan o'tish, chipta olish, profil ko'rish |

### 4.2 Foydalanuvchi Funksiyalari

| Tugma/Komanda | Nima qiladi |
|---------------|-------------|
| **Faol Tadbirlar** | Barcha ochiq (ACTIVE) tadbirlarni ko'rsatadi. Har biriga "Ro'yxatdan O'tish" tugmasi |
| **Liderlar Taxtasi** | Butun tizim bo'yicha TOP-10 (total_points bo'yicha) |
| **Mening Natijalarim** | Shaxsiy profil: ism, status, ball, qatnashgan tadbirlar soni, keyingi statusgacha qolgan ball |
| **/mytickets** | Barcha chiptalarini ko'rsatadi (rasm + PIN + QR) |

### 4.3 Tadbir Yaratish (Admin/President)

| Bosqich | Nima so'raladi |
|---------|----------------|
| 1 | Tadbir sarlavhasi |
| 2 | Tavsif (description) |
| 3 | Post link (yoki '-' o'tkazish) |
| 4 | Ro'yxatdan o'tish balli (masalan: 1) |
| 5 | Davomat balli (masalan: 5) |
| 6 | Sana va vaqt: `DD.MM.YYYY HH:MM` yoki `bugun 18:00` yoki `ertaga 14:00` yoki `-` (sanasiz) |
| 7 | Joylashuv (yoki '-' o'tkazish) |

Yaratilgan tadbir avtomatik ACTIVE holatda bo'ladi.

### 4.4 Ro'yxatdan O'tish va Chipta

1. Foydalanuvchi "Faol Tadbirlar" da tadbirni ko'radi
2. "Ro'yxatdan O'tish" tugmasini bosadi
3. Tizim: `registrations` jadvaliga yozadi + `total_points` ga reg_ball qo'shadi + status yangilaydi
4. QR kod + PIN bilan chipta rasm generatsiya qiladi
5. Chiptani foydalanuvchiga yuboradi

### 4.5 QR Skanerlash va Ball Berish

1. Admin/CP telefonida QR kodni skanerlaydi (kamera bilan)
2. QR deep link: `https://t.me/BOT?start=chk_E{event_id}_U{user_id}_S{hash}`
3. Bot security_hash ni tekshiradi
4. **Vaqt tekshiruvi:** Agar tadbir sanasi qo'yilgan bo'lsa, faqat 2 soat oldindan skanerlash mumkin
5. Chipta is_used = True qilinadi
6. Registration statusi ATTENDED qilinadi
7. `total_points` ga attendance_ball qo'shiladi
8. `user_status` yangilanadi (BRONZE → SILVER → GOLD → PLATINUM)
9. Foydalanuvchiga bildirishnoma yuboriladi

### 4.6 Skanerlash Vaqt Cheklovi

| Holat | Natija |
|-------|--------|
| Tadbir sanasi: 15.06.2025 14:00 | Skanerlash 12:00 dan boshlab ruxsat |
| Hozirgi vaqt: 10:00 (4 soat oldin) | "Bu tadbir hali boshlanmagan!" xatosi |
| Hozirgi vaqt: 13:00 (1 soat oldin) | Skanerlash muvaffaqiyatli |
| Tadbir sanasiz ('-') | Doim skanerlash mumkin |

### 4.7 Kanal Obuna Tekshiruvi (Middleware)

- Har bir xabar/tugmada foydalanuvchi majburiy kanallarga a'zo ekanligini tekshiradi
- A'zo bo'lmasa: kanalga a'zo bo'lish havolasi ko'rsatiladi
- SUPER_ADMIN tekshiruvdan o'tkaziladi
- QR deep link (`/start chk_...`) ham tekshiruvdan o'tkaziladi

### 4.8 Ball va Status Tizimi

| Status | Ball oralig'i | Imtiyozlar |
|--------|--------------|------------|
| BRONZE | 0-15 | Barcha ochiq tadbirlarga kirish |
| SILVER | 16-50 | Oldingi qatorlar + sovg'alar |
| GOLD | 51-120 | VIP tadbirlar + premium materiallar |
| PLATINUM | 121+ | Eksklyuziv networking + sertifikatlar |

**Ball olish yo'llari:**
1. Tadbirga ro'yxatdan o'tish: +reg_ball (odatda 1)
2. Tadbirga qatnashish (QR scan): +att_ball (odatda 5)
3. Team Bot vazifasini bajarish: +10

### 4.9 Klub Boshqaruvi (Admin Panel)

| Funksiya | Kim uchun |
|----------|-----------|
| Tadbirlar ro'yxati | SUPER_ADMIN: hamma, PRESIDENT: faqat o'z klubi |
| Yangi tadbir yaratish | SUPER_ADMIN va PRESIDENT |
| Davomat belgilash | Tadbirni boshqaruvchi (qo'lda: Qatnashdi/Qatnashmadi) |
| QR skanerlash | /scan komandasi |

---

## 5. IKKALA BOT ORASIDAGI BOG'LANISH

### 5.1 Ma'lumot Oqimi

```
TEAM BOT                          EVENT BOT
   |                                 |
   |-- Klub yaratadi --------------->| Event Bot klublarni o'qiydi
   |-- A'zo qo'shadi -------------->| Event Bot foydalanuvchini taniydi
   |-- CP tayinlaydi (is_cp=1) ---->| Event Bot ga PRESIDENT huquqi
   |-- Vazifa tasdiqlaydi (+10) --->| total_points va status yangilanadi
   |                                 |
   |<-- Event Bot ball qo'shadi ----| tadbirga qatnashish
   |<-- Event Bot status yangilaydi | BRONZE->SILVER->GOLD->PLATINUM
   |                                 |
```

### 5.2 Shared Database Mexanizmi

- Ikkala bot **bitta SQLite fayl** ga ulanadi
- **WAL (Write-Ahead Logging)** rejimi yoqilgan — bir vaqtda o'qish/yozish mumkin
- **busy_timeout=5000ms** — agar baza band bo'lsa, 5 soniya kutadi
- **foreign_keys=ON** — ma'lumot yaxlitligi

### 5.3 Foydalanuvchi Hayot Sikli (User Lifecycle)

```
1. BP Team Bot da klub yaratadi
2. BP shu klub uchun CP invite yaratadi
3. CP invite orqali Team Bot ga kiradi (is_cp=1)
4. CP o'z klubi a'zolariga invite yaratadi
5. A'zo invite orqali Team Bot ga kiradi
6. A'zo Event Bot da /start bosadi → avtomatik taniladi (shared DB)
7. A'zo tadbirga ro'yxatdan o'tadi → chipta oladi
8. Tadbir kunida QR skanerlash → ball oladi
9. Ball yetarli bo'lsa status ko'tariladi
10. Team Bot da vazifa bajarsa → yana ball oladi
```

---

## 6. DEPLOY VA SERVER SOZLAMALARI

### 6.1 Server Talablari

| Parametr | Minimal |
|----------|---------|
| OS | Ubuntu 20.04+ |
| RAM | 1 GB |
| Disk | 8 GB |
| Python | 3.10+ |
| Redis | 5.0+ |

### 6.2 O'rnatish

```bash
# 1. ZIP yuklash
wget https://github.com/fang2025yuan-lgtm/bott/raw/feat/unified-dual-bot-system/UFQ_SYSTEM_v3.zip

# 2. Ochish va deploy
unzip -o UFQ_SYSTEM_v3.zip -d UFQ_SYSTEM
cd UFQ_SYSTEM
chmod +x deploy.sh
sudo ./deploy.sh
```

### 6.3 .env Fayllar

**team_bot/.env:**
```
BOT_TOKEN=<team bot token>
ADMIN_ID=<telegram id>
DB_PATH=/home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db
```

**event_bot/.env:**
```
BOT_TOKEN=<event bot token>
SUPER_ADMIN_ID=<telegram id>
CHANNELS=-1003754712535,-1003157594758
BOT_USERNAME=<bot username>
DB_PATH=/home/ubuntu/UFQ_SYSTEM/shared/ufq_system.db
```

### 6.4 Systemd Xizmatlari

| Xizmat | Buyruqlar |
|--------|-----------|
| Team Bot holati | `sudo systemctl status ufq-team-bot` |
| Event Bot holati | `sudo systemctl status ufq-event-bot` |
| Team Bot restart | `sudo systemctl restart ufq-team-bot` |
| Event Bot restart | `sudo systemctl restart ufq-event-bot` |
| Team Bot loglari | `sudo journalctl -u ufq-team-bot -f` |
| Event Bot loglari | `sudo journalctl -u ufq-event-bot -f` |

---

## 7. XAVFSIZLIK

| Himoya | Qanday ishlaydi |
|--------|-----------------|
| Token xavfsizligi | .env faylda, git da EMAS |
| Admin ID | Faqat config da, spoofing mumkin emas |
| Invite bir martalik | Atomic UPDATE (race condition himoyasi) |
| QR chipta | SHA-256 hash + unique PIN |
| Kanal tekshiruvi | Har bir amalda middleware tekshiradi |
| SQL injection | Parameterized queries (?) |
| DB xavfsizligi | WAL + busy_timeout + foreign_keys |

---

## 8. TEXNIK DETALLAR

### 8.1 Team Bot Texnologiya Steki

| Komponent | Versiya | Vazifasi |
|-----------|---------|----------|
| aiogram | 3.4.1 | Telegram Bot API framework |
| aiosqlite | 0.20.0 | Async SQLite driver |
| redis | 5.0.1 | FSM state storage |
| python-dotenv | 1.0.1 | .env faylni o'qish |

### 8.2 Event Bot Texnologiya Steki

| Komponent | Versiya | Vazifasi |
|-----------|---------|----------|
| aiogram | 3.4.1 | Telegram Bot API framework |
| SQLAlchemy | 2.0.25 | ORM (events, registrations, tickets) |
| aiosqlite | 0.20.0 | Raw queries (users, clubs) |
| Pillow | 10.2.0 | Chipta rasm yaratish |
| qrcode | 7.4.2 | QR kod generatsiya |
| python-dotenv | 1.0.1 | .env faylni o'qish |

### 8.3 Database Connection Pattern

```python
# Team Bot: har bir query uchun get_db() context manager
@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA busy_timeout=5000")
        await db.execute("PRAGMA foreign_keys=ON")
        db.row_factory = aiosqlite.Row
        yield db
    finally:
        await db.close()

# Ishlatilishi:
async with get_db() as db:
    cursor = await db.execute("SELECT * FROM users WHERE telegram_id=?", (tg_id,))
    user = await cursor.fetchone()
```

---

## 9. TIZIMNI KENGAYTIRISH (FUTURE)

| G'oya | Qiyinlik | Prioritet |
|-------|----------|-----------|
| PostgreSQL ga o'tish | O'rta | Past (SQLite 1000+ user ga yetarli) |
| Docker Compose | O'rta | O'rta |
| Admin web panel | Yuqori | Past |
| Tadbir eslatmalari (cron) | Past | Yuqori |
| CSV export (hisobot) | Past | O'rta |
| Multi-language support | O'rta | Past |

---

*Bu hujjat UFQ Unified System ning to'liq texnik va funksional tavsifi hisoblanadi.*
*Oxirgi yangilanish: 2026-05-31*
