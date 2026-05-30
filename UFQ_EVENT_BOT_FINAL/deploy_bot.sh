#!/bin/bash
set -e

echo "================================================="
echo "   UFQ EVENT BOT (FINAL) - DEPLOY SCRIPT         "
echo "================================================="

cd /home/ubuntu/UFQ_EVENT_BOT_FINAL

echo ""
echo "Botni ishga tushirish uchun ma'lumotlarni kiriting:"
read -p "1. Telegram Bot Tokenini kiriting: " bot_token
read -p "2. SUPER_ADMIN Telegram ID raqamini kiriting: " admin_id
read -p "3. Majburiy kanallarni kiriting (Vergul bilan ajrating, misol: -1001234,@kanal): " channels

cat << 'EOF' > /home/ubuntu/UFQ_EVENT_BOT_FINAL/.env
BOT_TOKEN=$bot_token
SUPER_ADMIN_ID=$admin_id
CHANNELS=$channels
DATABASE_URL=sqlite+aiosqlite:///ufq_events.db
EOF

echo ">>> Xizmatlar to'xtatilmoqda..."
sudo systemctl stop ufq-event-bot 2>/dev/null || true

echo ">>> Python muhiti tayyorlanmoqda..."
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip

rm -rf venv
python3 -m venv venv
/home/ubuntu/UFQ_EVENT_BOT_FINAL/venv/bin/pip install -r requirements.txt

echo ">>> Fayl huquqlari to'g'rilanmoqda..."
sudo chown -R ubuntu:ubuntu /home/ubuntu/UFQ_EVENT_BOT_FINAL

echo ">>> Systemd sozlanmoqda..."
cat << EOF | sudo tee /etc/systemd/system/ufq-event-bot.service
[Unit]
Description=UFQ Event Bot (FINAL)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/UFQ_EVENT_BOT_FINAL
ExecStart=/home/ubuntu/UFQ_EVENT_BOT_FINAL/venv/bin/python -m bot.main
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
