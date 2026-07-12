"""
Auto-Withdraw System - Automatically withdraw profits to cold wallet
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any

class AutoWithdrawSystem:
    def __init__(self, gate_api, config: dict):
        self.gate_api = gate_api
        self.config = config
        self.running = False
        
        self.cold_wallet = config.get("cold_wallet", "")
        self.threshold = config.get("withdraw_threshold", 100)
        self.chain = config.get("withdraw_chain", "TRC20")
        
        self.starting_balance = config.get("starting_balance", 692)
        self.last_check_balance = self.starting_balance
        self.total_withdrawn = 0
        self.withdrawal_history: List[Dict] = []
        
    async def start(self):
        """Start monitoring for withdrawals"""
        self.running = True
        print(f"💰 Auto-Withdraw monitoring started")
        print(f"   Threshold: ${self.threshold}")
        print(f"   Cold Wallet: {self.cold_wallet[:10]}...{self.cold_wallet[-6:]}")
        
        while self.running:
            try:
                await self._check_and_withdraw()
                await asyncio.sleep(300)
            except Exception as e:
                print(f"❌ Auto-withdraw error: {e}")
                await asyncio.sleep(60)
    
    async def _check_and_withdraw(self):
        """Check if withdrawal is needed"""
        try:
            balance = await self.gate_api.get_balance()
            current = float(balance.get("available", 0))
            
            profit = current - self.starting_balance - self.total_withdrawn
            
            if profit >= self.threshold:
                await self._execute_withdrawal(profit)
                
        except Exception as e:
            print(f"❌ Balance check error: {e}")
    
    async def _execute_withdrawal(self, amount: float):
        """Execute withdrawal to cold wallet"""
        if not self.cold_wallet:
            print("⚠️ No cold wallet configured")
            return
            
        print(f"\n💸 WITHDRAWING ${amount:.2f} to cold wallet...")
        
        try:
            result = await self.gate_api.withdraw(
                currency="USDT",
                amount=amount,
                address=self.cold_wallet,
                chain=self.chain
            )
            
            if result:
                self.total_withdrawn += amount
                self.withdrawal_history.append({
                    "amount": amount,
                    "address": self.cold_wallet,
                    "chain": self.chain,
                    "timestamp": datetime.now().isoformat(),
                    "tx_id": result.get("txid", "pending")
                })
                print(f"✅ Withdrawal successful! TX: {result.get('txid', 'pending')}")
            else:
                print(f"❌ Withdrawal failed")
                
        except Exception as e:
            print(f"❌ Withdrawal error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get auto-withdraw status"""
        return {
            "enabled": self.running,
            "cold_wallet": self.cold_wallet,
            "threshold": self.threshold,
            "chain": self.chain,
            "total_withdrawn": self.total_withdrawn,
            "withdrawal_count": len(self.withdrawal_history),
            "last_withdrawal": self.withdrawal_history[-1] if self.withdrawal_history else None
        }
    
    async def stop(self):
        """Stop the auto-withdraw system"""
        self.running = False
        print("💰 Auto-withdraw stopped")
