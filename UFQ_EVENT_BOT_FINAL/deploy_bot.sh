#!/bin/bash
set -e

echo "================================================="
echo "   UFQ EVENT BOT PREMIUM v2.0 - AUTO DEPLOY      "
echo "================================================="
echo ""

INSTALL_DIR="/home/ubuntu/UFQ_EVENT_BOT_FINAL"
BACKUP_DIR="/home/ubuntu/ufq_db_backup"
SERVICE_NAME="ufq-event-bot"
ZIP_URL="https://github.com/fang2025yuan-lgtm/bott/raw/main/UFQ_EventBot_PREMIUM_v2.0.zip"
TMP_ZIP="/tmp/ufq_bot_download.zip"

# 1. Eski versiyani tekshirish va zaxiralash
echo ">>> [1/7] Eski versiyani tekshirish..."
if [ -d "$INSTALL_DIR" ]; then
    echo "    Eski versiya topildi."
    sudo systemctl stop $SERVICE_NAME 2>/dev/null || true
    sudo systemctl disable $SERVICE_NAME 2>/dev/null || true
    sudo rm -f /etc/systemd/system/${SERVICE_NAME}.service

    # DB zaxiralash
    if [ -f "$INSTALL_DIR/ufq_events.db" ]; then
        echo "    Ma'lumotlar bazasi zaxiralanmoqda..."
        mkdir -p "$BACKUP_DIR"
        cp "$INSTALL_DIR/ufq_events.db" "$BACKUP_DIR/ufq_events_$(date +%Y%m%d_%H%M%S).db"
        cp "$INSTALL_DIR/ufq_events.db" "$BACKUP_DIR/ufq_events_latest.db"
        echo "    ✅ Zaxira yaratildi: $BACKUP_DIR/"
    fi

    # Eski .env ni saqlash (agar mavjud bo'lsa)
    if [ -f "$INSTALL_DIR/.env" ]; then
        cp "$INSTALL_DIR/.env" "/tmp/ufq_old_env_backup"
        echo "    Eski .env zaxiralandi."
    fi

    sudo rm -rf "$INSTALL_DIR"
    echo "    Eski versiya tozalandi."
fi

# 2. GitHub dan yuklab olish
echo ""
echo ">>> [2/7] GitHub dan eng so'nggi versiya yuklanmoqda..."
sudo apt-get update -y -qq
sudo apt-get install -y -qq wget unzip python3-venv python3-pip

wget -q --show-progress -O "$TMP_ZIP" "$ZIP_URL"
if [ ! -f "$TMP_ZIP" ]; then
    echo "❌ XATOLIK: ZIP faylni yuklab bo'lmadi!"
    echo "   URL: $ZIP_URL"
    exit 1
fi

# 3. Unzip va joylashtirish
echo ""
echo ">>> [3/7] Fayllar ochilib joylashtirilmoqda..."
unzip -q -o "$TMP_ZIP" -d /home/ubuntu/
rm -f "$TMP_ZIP"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ XATOLIK: Unzip muvaffaqiyatsiz! '$INSTALL_DIR' topilmadi."
    exit 1
fi
echo "    ✅ Fayllar joylashtirildi: $INSTALL_DIR"

# 4. Sozlamalarni kiritish
echo ""
echo ">>> [4/7] Bot sozlamalari..."
echo ""

# Agar eski .env mavjud bo'lsa, qayta ishlatishni taklif qilish
USE_OLD_ENV=false
if [ -f "/tmp/ufq_old_env_backup" ]; then
    echo "    Eski sozlamalar topildi. Qayta ishlatishni xohlaysizmi?"
    read -p "    Eski sozlamalarni ishlatish? (Ha/Yo'q) [Ha]: " use_old
    use_old=${use_old:-Ha}
    if [[ "$use_old" =~ ^[Hh] ]]; then
        cp "/tmp/ufq_old_env_backup" "$INSTALL_DIR/.env"
        USE_OLD_ENV=true
        echo "    ✅ Eski sozlamalar tiklandi."
    fi
fi

if [ "$USE_OLD_ENV" = false ]; then
    echo "    Quyidagi ma'lumotlarni kiriting:"
    echo ""
    read -p "    1. Bot Token (@BotFather dan): " bot_token
    read -p "    2. Super Admin Telegram ID: " admin_id
    read -p "    3. Majburiy kanallar (vergul bilan, masalan: -1001234,@kanal): " channels
    read -p "    4. Bot Username (@ belgisisiz, masalan: ufq_events_bot): " bot_username
    bot_username=${bot_username:-ufq_events_bot}

    cat > "$INSTALL_DIR/.env" << EOF
BOT_TOKEN=$bot_token
SUPER_ADMIN_ID=$admin_id
CHANNELS=$channels
BOT_USERNAME=$bot_username
DATABASE_URL=sqlite+aiosqlite:///ufq_events.db
EOF
    echo "    ✅ .env fayli yaratildi."
fi

rm -f /tmp/ufq_old_env_backup

# 5. Python muhitini tayyorlash
echo ""
echo ">>> [5/7] Python muhiti tayyorlanmoqda..."
rm -rf "$INSTALL_DIR/venv"
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q
echo "    ✅ Barcha kutubxonalar o'rnatildi."

# 6. Ma'lumotlar bazasini tiklash
echo ""
echo ">>> [6/7] Ma'lumotlar bazasi tiklanmoqda..."
if [ -f "$BACKUP_DIR/ufq_events_latest.db" ]; then
    cp "$BACKUP_DIR/ufq_events_latest.db" "$INSTALL_DIR/ufq_events.db"
    echo "    ✅ Ma'lumotlar bazasi tiklandi."
else
    echo "    ℹ️ Zaxira topilmadi. Yangi baza yaratiladi."
fi

# Fayl huquqlari
sudo chown -R $(whoami):$(whoami) "$INSTALL_DIR"

# 7. Systemd xizmati
echo ""
echo ">>> [7/7] Systemd xizmati sozlanmoqda..."
cat << EOF | sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null
[Unit]
Description=UFQ Event Bot PREMIUM v2.0
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python -m bot.main
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME

# Tekshirish
echo ""
sleep 3
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "========================================================="
    echo ""
    echo "   ✅ BOT MUVAFFAQIYATLI ISHGA TUSHDI!"
    echo ""
    echo "   Telegramga kirib /start bosing."
    echo ""
    echo "   Foydali komandalar:"
    echo "     sudo systemctl status $SERVICE_NAME"
    echo "     sudo journalctl -u $SERVICE_NAME -f"
    echo "     sudo systemctl restart $SERVICE_NAME"
    echo ""
    echo "========================================================="
else
    echo "❌ XATOLIK: Bot ishga tushmadi!"
    echo ""
    echo "Loglarni tekshiring:"
    sudo journalctl -u $SERVICE_NAME -n 30 --no-pager
fi
