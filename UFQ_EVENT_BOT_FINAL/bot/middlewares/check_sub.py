from typing import Any, Awaitable, Callable, Dict
import logging
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.config import CHANNELS, SUPER_ADMIN_ID

logger = logging.getLogger(__name__)

class CheckSubMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        
        bot = data['bot']
        user_id = event.from_user.id
        
        if user_id == SUPER_ADMIN_ID:
            return await handler(event, data)
            
        not_subscribed_channels = []
        
        for channel in CHANNELS:
            try:
                member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
                if member.status in ['left', 'kicked', 'banned']:
                    not_subscribed_channels.append(channel)
            except Exception as e:
                logger.error(f"Kanalni tekshirishda xatolik ({channel}): {e}")
                # Xato bo'lsa, kanalga a'zo bo'lmagan deb hisoblash
                not_subscribed_channels.append(channel)
                
        if not_subscribed_channels:
            keyboard = []
            for ch in not_subscribed_channels:
                ch_str = str(ch)
                if ch_str.startswith("@"):
                    url = f"https://t.me/{ch_str.replace('@', '')}"
                else:
                    url = f"https://t.me/c/{ch_str.replace('-100', '')}/1"
                keyboard.append([InlineKeyboardButton(text=f"📢 Kanalga a'zo bo'lish", url=url)])
            
            keyboard.append([InlineKeyboardButton(text="✅ A'zo bo'ldim", callback_data="check_sub")])
            markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            msg_text = "⛔ Tizimdan foydalanish uchun quyidagi majburiy kanallarga a'zo bo'lishingiz shart!"
            
            if isinstance(event, Message):
                await event.answer(msg_text, reply_markup=markup)
            elif isinstance(event, CallbackQuery) and event.data != "check_sub":
                await event.message.answer(msg_text, reply_markup=markup)
                await event.answer()
            elif isinstance(event, CallbackQuery) and event.data == "check_sub":
                await event.answer("Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)
            return 
        
        return await handler(event, data)
