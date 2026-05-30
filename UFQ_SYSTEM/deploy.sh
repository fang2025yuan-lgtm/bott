#!/bin/bash
# ============================================================
# UFQ UNIFIED SYSTEM - DEPLOY SCRIPT
# Team Bot + Event Bot (Bitta umumiy ma'lumotlar bazasi)
#
# Bu skript ikkala botni avtomatik o'rnatadi:
#   - UFQ Team Bot (jamoa boshqaruvi)
#   - UFQ Event Bot (tadbirlar boshqaruvi)
# Ikkala bot bitta SQLite bazadan foydalanadi.
# ============================================================
set -e

echo "================================================="
echo "   UFQ UNIFIED SYSTEM - DEPLOY SCRIPT            "
echo "   Team Bot + Event Bot (Shared Database)        "
echo "================================================="
echo ""

# ============================================================
# [1] Foydalanuvchidan ma'lumotlarni so'rash
# ============================================================
read -p "1. Team Bot Token: " TEAM_BOT_TOKEN
read -p "2. Event Bot Token: " EVENT_BOT_TOKEN
read -p "3. Bosh Prezident / Super Admin Telegram ID: " ADMIN_ID
read -p "4. Event Bot Username (@ belgisisiz): " BOT_USERNAME
read -p "5. Majburiy kanallar (vergul bilan, masalan: @kanal1,@kanal2): " CHANNELS

# Kiritilgan ma'lumotlarni tekshirish
if [ -z "$TEAM_BOT_TOKEN" ] || [ -z "$EVENT_BOT_TOKEN" ] || [ -z "$ADMIN_ID" ]; then
    echo ""
    echo "XATOLIK: Barcha maydonlar to'ldirilishi shart!"
    echo "  - Team Bot Token, Event Bot Token va Admin ID majburiy."
    exit 1
fi

# Agar BOT_USERNAME kiritilmagan bo'lsa, standart qiymat
if [ -z "$BOT_USERNAME" ]; then
    BOT_USERNAME="ufq_event_bot"
    echo "   (BOT_USERNAME kiritilmadi, standart: $BOT_USERNAME)"
fi

# ============================================================
# O'zgaruvchilar
# ============================================================
INSTALL_DIR="/home/ubuntu/UFQ_SYSTEM"
BACKUP_DIR="/home/ubuntu/ufq_db_backup"
DB_FILE="$INSTALL_DIR/shared/ufq_system.db"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo ">>> [1/8] Eski xizmatlar to'xtatilmoqda..."
# Avvalgi versiyadan qolgan barcha xizmatlarni to'xtatish va o'chirish
sudo systemctl stop ufq-bot 2>/dev/null || true
sudo systemctl stop ufq-event-bot 2>/dev/null || true
sudo systemctl stop ufq-team-bot 2>/dev/null || true
sudo systemctl disable ufq-bot 2>/dev/null || true
sudo systemctl disable ufq-event-bot 2>/dev/null || true
sudo systemctl disable ufq-team-bot 2>/dev/null || true
sudo rm -f /etc/systemd/system/ufq-bot.service
sudo rm -f /etc/systemd/system/ufq-event-bot.service
sudo rm -f /etc/systemd/system/ufq-team-bot.service

echo ">>> [2/8] Mavjud ma'lumotlar bazasi zaxiralanmoqda..."
# Zaxira papkasini yaratish
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Eski Team Bot bazasini zaxiralash (agar mavjud bo'lsa)
if [ -f "/home/ubuntu/UFQ_BOT_V9_FINAL/ufq_jamoa.db" ]; then
    cp "/home/ubuntu/UFQ_BOT_V9_FINAL/ufq_jamoa.db" "$BACKUP_DIR/ufq_jamoa_$TIMESTAMP.db"
    echo "   Zaxira: ufq_jamoa.db -> $BACKUP_DIR/ufq_jamoa_$TIMESTAMP.db"
fi

# Yangi tizim bazasini zaxiralash (agar mavjud bo'lsa)
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_DIR/ufq_system_$TIMESTAMP.db"
    echo "   Zaxira: ufq_system.db -> $BACKUP_DIR/ufq_system_$TIMESTAMP.db"
fi

# Eski Event Bot bazasini zaxiralash (agar mavjud bo'lsa)
if [ -f "/home/ubuntu/UFQ_EVENT_BOT_FINAL/ufq_events.db" ]; then
    cp "/home/ubuntu/UFQ_EVENT_BOT_FINAL/ufq_events.db" "$BACKUP_DIR/ufq_events_$TIMESTAMP.db"
    echo "   Zaxira: ufq_events.db -> $BACKUP_DIR/ufq_events_$TIMESTAMP.db"
fi

echo ">>> [3/8] Eski fayllar tozalanmoqda..."
# Eski versiyalarni o'chirish
sudo rm -rf /home/ubuntu/UFQ_BOT_V9_FINAL
sudo rm -rf /home/ubuntu/UFQ_EVENT_BOT_FINAL
sudo rm -rf "$INSTALL_DIR"

echo ">>> [4/8] Yangi tuzilma yaratilmoqda..."
# Yangi papka tuzilmasini yaratish
mkdir -p "$INSTALL_DIR/team_bot"
mkdir -p "$INSTALL_DIR/event_bot"
mkdir -p "$INSTALL_DIR/shared"

# Skript joylashgan papkadan fayllarni ko'chirish
cp -r "$SCRIPT_DIR/team_bot/"* "$INSTALL_DIR/team_bot/"
cp -r "$SCRIPT_DIR/event_bot/"* "$INSTALL_DIR/event_bot/"
cp "$SCRIPT_DIR/SYSTEM_README.md" "$INSTALL_DIR/" 2>/dev/null || true
cp "$SCRIPT_DIR/deploy.sh" "$INSTALL_DIR/" 2>/dev/null || true

# Mavjud bazani tiklash (agar zaxira mavjud bo'lsa)
if [ -f "$BACKUP_DIR/ufq_jamoa_$TIMESTAMP.db" ]; then
    cp "$BACKUP_DIR/ufq_jamoa_$TIMESTAMP.db" "$DB_FILE"
    echo "   Mavjud baza tiklandi: ufq_jamoa.db -> ufq_system.db"
elif [ -f "$BACKUP_DIR/ufq_system_$TIMESTAMP.db" ]; then
    cp "$BACKUP_DIR/ufq_system_$TIMESTAMP.db" "$DB_FILE"
    echo "   Mavjud baza tiklandi: ufq_system.db"
fi

echo ">>> [5/8] .env fayllar yaratilmoqda..."
# Team Bot uchun .env fayl
cat << EOF > "$INSTALL_DIR/team_bot/.env"
BOT_TOKEN=$TEAM_BOT_TOKEN
ADMIN_ID=$ADMIN_ID
DB_PATH=$DB_FILE
EOF

# Event Bot uchun .env fayl
cat << EOF > "$INSTALL_DIR/event_bot/.env"
BOT_TOKEN=$EVENT_BOT_TOKEN
SUPER_ADMIN_ID=$ADMIN_ID
CHANNELS=$CHANNELS
BOT_USERNAME=$BOT_USERNAME
DB_PATH=$DB_FILE
EOF

echo ">>> [6/8] Python muhiti va paketlar o'rnatilmoqda..."
# Kerakli tizim paketlarini o'rnatish
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip redis-server

# Redis xizmatini yoqish va ishga tushirish
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Team Bot uchun virtual muhit
echo "   Team Bot paketlari o'rnatilmoqda..."
rm -rf "$INSTALL_DIR/team_bot/venv"
python3 -m venv "$INSTALL_DIR/team_bot/venv"
"$INSTALL_DIR/team_bot/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/team_bot/venv/bin/pip" install -r "$INSTALL_DIR/team_bot/requirements.txt"

# Event Bot uchun virtual muhit
echo "   Event Bot paketlari o'rnatilmoqda..."
rm -rf "$INSTALL_DIR/event_bot/venv"
python3 -m venv "$INSTALL_DIR/event_bot/venv"
"$INSTALL_DIR/event_bot/venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/event_bot/venv/bin/pip" install -r "$INSTALL_DIR/event_bot/requirements.txt"

echo ">>> [7/8] Systemd xizmatlari sozlanmoqda..."
# Team Bot systemd xizmati
cat << EOF | sudo tee /etc/systemd/system/ufq-team-bot.service
[Unit]
Description=UFQ Team Bot
After=network.target redis-server.service

[Service]
User=ubuntu
WorkingDirectory=$INSTALL_DIR/team_bot
ExecStart=$INSTALL_DIR/team_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=3
Environment=DB_PATH=$DB_FILE

[Install]
WantedBy=multi-user.target
EOF

# Event Bot systemd xizmati
cat << EOF | sudo tee /etc/systemd/system/ufq-event-bot.service
[Unit]
Description=UFQ Event Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=$INSTALL_DIR/event_bot
ExecStart=$INSTALL_DIR/event_bot/venv/bin/python -m bot.main
Restart=always
RestartSec=3
Environment=DB_PATH=$DB_FILE

[Install]
WantedBy=multi-user.target
EOF

# Systemd yangilash va xizmatlarni ishga tushirish
sudo systemctl daemon-reload
sudo systemctl enable ufq-team-bot
sudo systemctl enable ufq-event-bot
sudo systemctl restart ufq-team-bot
sudo systemctl restart ufq-event-bot

echo ">>> [8/8] Tizim tekshirilmoqda..."
sleep 4

TEAM_OK=false
EVENT_OK=false

if sudo systemctl is-active --quiet ufq-team-bot; then
    TEAM_OK=true
fi
if sudo systemctl is-active --quiet ufq-event-bot; then
    EVENT_OK=true
fi

echo ""
echo "========================================================="
if [ "$TEAM_OK" = true ] && [ "$EVENT_OK" = true ]; then
    echo " MUVAFFAQIYAT! Ikkala bot ham ishga tushdi!"
elif [ "$TEAM_OK" = true ]; then
    echo " OGOHLANTIRISH: Team Bot ishlamoqda, lekin Event Bot ishga tushmadi!"
    echo ""
    echo " Event Bot xatolik loglari:"
    sudo journalctl -u ufq-event-bot -n 10 --no-pager
elif [ "$EVENT_OK" = true ]; then
    echo " OGOHLANTIRISH: Event Bot ishlamoqda, lekin Team Bot ishga tushmadi!"
    echo ""
    echo " Team Bot xatolik loglari:"
    sudo journalctl -u ufq-team-bot -n 10 --no-pager
else
    echo " XATOLIK! Ikkala bot ham ishga tushmadi!"
    echo ""
    echo " Team Bot log:"
    sudo journalctl -u ufq-team-bot -n 10 --no-pager
    echo ""
    echo " Event Bot log:"
    sudo journalctl -u ufq-event-bot -n 10 --no-pager
fi
echo ""
echo " O'rnatish joyi: $INSTALL_DIR"
echo " Ma'lumotlar bazasi: $DB_FILE"
echo " Zaxira papkasi: $BACKUP_DIR"
echo "========================================================="
echo ""
echo " Foydali buyruqlar:"
echo "   sudo systemctl status ufq-team-bot"
echo "   sudo systemctl status ufq-event-bot"
echo "   sudo journalctl -u ufq-team-bot -f"
echo "   sudo journalctl -u ufq-event-bot -f"
echo "   sudo systemctl restart ufq-team-bot"
echo "   sudo systemctl restart ufq-event-bot"
echo "========================================================="

# Fayl egaligini to'g'rilash
sudo chown -R ubuntu:ubuntu "$INSTALL_DIR"
