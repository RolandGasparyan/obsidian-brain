"""
Telegram Bot - Send alerts and notifications
"""

import os
import aiohttp
from typing import Optional

class TelegramBot:
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if self.enabled:
            print(f"✅ Telegram alerts enabled")
        else:
            print(f"⚠️ Telegram alerts disabled (no token/chat_id)")
    
    async def send_alert(self, message: str) -> bool:
        """Send alert message to Telegram"""
        if not self.enabled:
            print(f"[ALERT] {message}")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "HTML"
                }) as response:
                    if response.status == 200:
                        return True
                    else:
                        print(f"Telegram error: {response.status}")
                        return False
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    async def send_trade_alert(self, ai_name: str, action: str, symbol: str, size: float, price: float):
        """Send trade execution alert"""
        emoji = "📈" if action == "LONG" else "📉"
        message = f"{emoji} <b>Trade Executed</b>\n\n"
        message += f"AI: {ai_name}\n"
        message += f"Action: {action} {symbol}\n"
        message += f"Size: ${size:.2f}\n"
        message += f"Price: ${price:.2f}"
        
        await self.send_alert(message)
    
    async def send_profit_alert(self, total_profit: float, best_ai: str, best_profit: float):
        """Send profit milestone alert"""
        message = f"💰 <b>Profit Milestone!</b>\n\n"
        message += f"Total Profit: ${total_profit:.2f}\n"
        message += f"Best AI: {best_ai}\n"
        message += f"Best Profit: ${best_profit:.2f}"
        
        await self.send_alert(message)
    
    async def send_withdrawal_alert(self, amount: float, address: str, tx_id: str):
        """Send withdrawal alert"""
        message = f"💸 <b>Withdrawal Executed</b>\n\n"
        message += f"Amount: ${amount:.2f} USDT\n"
        message += f"To: {address[:10]}...{address[-6:]}\n"
        message += f"TX: {tx_id}"
        
        await self.send_alert(message)
