#!/bin/bash
set -e

echo "================================================="
echo "   UFQ EVENT BOT (FINAL) - DEPLOY SCRIPT         "
echo "================================================="

# Eski botni to'xtatish va o'chirish
echo ">>> Eski bot versiyasini tekshirish..."
if [ -d "/home/ubuntu/UFQ_EVENT_BOT_FINAL" ]; then
    echo "Eski versiya topildi. To'xtatish va o'chirish..."
    sudo systemctl stop ufq-event-bot 2>/dev/null || true
    sudo systemctl disable ufq-event-bot 2>/dev/null || true
    sudo rm -f /etc/systemd/system/ufq-event-bot.service
    # Ma'lumotlar bazasini zaxiralash
    if [ -f "/home/ubuntu/UFQ_EVENT_BOT_FINAL/ufq_events.db" ]; then
        echo ">>> Ma'lumotlar bazasi zaxiralanmoqda..."
        mkdir -p /home/ubuntu/ufq_db_backup
        cp /home/ubuntu/UFQ_EVENT_BOT_FINAL/ufq_events.db /home/ubuntu/ufq_db_backup/ufq_events_backup.db
        echo "Zaxira yaratildi: /home/ubuntu/ufq_db_backup/ufq_events_backup.db"
    fi
    sudo rm -rf /home/ubuntu/UFQ_EVENT_BOT_FINAL
    echo "Eski versiya tozalandi."
fi

# Joriy papkani aniqlash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "Botni ishga tushirish uchun ma'lumotlarni kiriting:"
read -p "1. Telegram Bot Tokenini kiriting: " bot_token
read -p "2. SUPER_ADMIN Telegram ID raqamini kiriting: " admin_id
read -p "3. Majburiy kanallarni kiriting (Vergul bilan ajrating, misol: -1001234,@kanal): " channels
read -p "4. Bot Username (@ belgisisiz, masalan: ufq_events_bot): " bot_username
bot_username=${bot_username:-ufq_events_bot}

# .env faylini yaratish
cat << EOF > "$SCRIPT_DIR/.env"
BOT_TOKEN=$bot_token
SUPER_ADMIN_ID=$admin_id
CHANNELS=$channels
BOT_USERNAME=$bot_username
DATABASE_URL=sqlite+aiosqlite:///ufq_events.db
EOF

echo ">>> Xizmatlar to'xtatilmoqda..."
sudo systemctl stop ufq-event-bot 2>/dev/null || true

echo ">>> Python muhiti tayyorlanmoqda..."
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip

rm -rf "$SCRIPT_DIR/venv"
python3 -m venv "$SCRIPT_DIR/venv"
"$SCRIPT_DIR/venv/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

# Ma'lumotlar bazasini tiklash
if [ -f "/home/ubuntu/ufq_db_backup/ufq_events_backup.db" ]; then
    echo ">>> Ma'lumotlar bazasi tiklanmoqda..."
    cp /home/ubuntu/ufq_db_backup/ufq_events_backup.db "$SCRIPT_DIR/ufq_events.db"
    echo "Ma'lumotlar bazasi tiklandi."
fi

echo ">>> Fayl huquqlari to'g'rilanmoqda..."
sudo chown -R $(whoami):$(whoami) "$SCRIPT_DIR"

echo ">>> Systemd sozlanmoqda..."
cat << EOF | sudo tee /etc/systemd/system/ufq-event-bot.service
[Unit]
Description=UFQ Event Bot (FINAL)
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/venv/bin/python -m bot.main
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ufq-event-bot
sudo systemctl restart ufq-event-bot

echo ">>> Tizim tekshirilmoqda..."
sleep 3
if ! sudo systemctl is-active --quiet ufq-event-bot; then
    echo "❌ XATOLIK YUZ BERDI!"
    sudo journalctl -u ufq-event-bot -n 20 --no-pager
else
    echo "========================================================="
    echo " ✅ BOT ISHGA TUSHDI! Telegramga kirib /start bosing."
    echo "========================================================="
fi
