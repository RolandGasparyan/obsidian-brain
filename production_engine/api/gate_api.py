"""
Gate.io API Client - Async API wrapper for Gate.io
"""

import os
import time
import hmac
import hashlib
import json
import aiohttp
from typing import Dict, Any, Optional

class GateIOAPI:
    def __init__(self):
        self.api_key = os.getenv("GATE_API_KEY", "")
        self.api_secret = os.getenv("GATE_API_SECRET", "")
        self.base_url = "https://api.gateio.ws/api/v4"
        self.futures_url = "https://api.gateio.ws/api/v4/futures/usdt"
        
    def _sign(self, method: str, url: str, query_string: str = "", body: str = "") -> Dict[str, str]:
        """Generate authentication signature"""
        t = str(int(time.time()))
        m = hashlib.sha512()
        m.update((body or "").encode("utf-8"))
        hashed_payload = m.hexdigest()
        s = f"{method}\n{url}\n{query_string}\n{hashed_payload}\n{t}"
        sign = hmac.new(self.api_secret.encode("utf-8"), s.encode("utf-8"), hashlib.sha512).hexdigest()
        
        return {
            "KEY": self.api_key,
            "Timestamp": t,
            "SIGN": sign,
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, params: Dict = None, body: Dict = None, is_futures: bool = True) -> Optional[Dict]:
        """Make authenticated API request"""
        base = self.futures_url if is_futures else self.base_url
        url = f"{base}{endpoint}"
        
        query_string = "&".join([f"{k}={v}" for k, v in (params or {}).items()])
        body_str = json.dumps(body) if body else ""
        
        headers = self._sign(method, f"/api/v4/futures/usdt{endpoint}" if is_futures else f"/api/v4{endpoint}", query_string, body_str)
        
        full_url = f"{url}?{query_string}" if query_string else url
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, full_url, headers=headers, data=body_str if body else None) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error = await response.text()
                        print(f"API Error: {response.status} - {error}")
                        return None
        except Exception as e:
            print(f"Request error: {e}")
            return None
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get futures account balance"""
        result = await self._request("GET", "/accounts")
        if result:
            return {"available": result.get("available", 0), "total": result.get("total", 0)}
        return {"available": 0, "total": 0}
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker for a symbol"""
        result = await self._request("GET", f"/tickers", {"contract": symbol})
        if result and len(result) > 0:
            return result[0]
        return None
    
    async def get_positions(self) -> list:
        """Get all open positions"""
        result = await self._request("GET", "/positions")
        return result or []
    
    async def create_order(self, symbol: str, side: str, size: float, leverage: int = 10) -> Optional[Dict]:
        """Create a futures order"""
        await self._request("POST", f"/positions/{symbol}/leverage", body={"leverage": str(leverage)})
        
        ticker = await self.get_ticker(symbol)
        if not ticker:
            return None
            
        price = float(ticker.get("last", 0))
        contract_size = self._get_contract_size(symbol, size, price)
        
        if side == "short":
            contract_size = -abs(contract_size)
        else:
            contract_size = abs(contract_size)
        
        order = {
            "contract": symbol,
            "size": contract_size,
            "price": "0",
            "tif": "ioc"
        }
        
        result = await self._request("POST", "/orders", body=order)
        return result
    
    def _get_contract_size(self, symbol: str, size_usd: float, price: float) -> int:
        """Calculate contract size"""
        min_sizes = {
            "BTC_USDT": 0.001,
            "ETH_USDT": 0.01,
            "SOL_USDT": 1,
            "XRP_USDT": 100,
            "AVAX_USDT": 1
        }
        
        min_size = min_sizes.get(symbol, 1)
        calculated = size_usd / price
        
        if calculated < min_size:
            calculated = min_size
            
        if symbol in ["XRP_USDT"]:
            return int(calculated)
        elif symbol in ["BTC_USDT", "ETH_USDT"]:
            return round(calculated, 3)
        else:
            return int(calculated)
    
    async def close_position(self, symbol: str) -> Optional[Dict]:
        """Close a position"""
        positions = await self.get_positions()
        for pos in positions:
            if pos.get("contract") == symbol and pos.get("size", 0) != 0:
                size = -pos["size"]
                order = {
                    "contract": symbol,
                    "size": size,
                    "price": "0",
                    "tif": "ioc"
                }
                return await self._request("POST", "/orders", body=order)
        return None
    
    async def withdraw(self, currency: str, amount: float, address: str, chain: str = "TRC20") -> Optional[Dict]:
        """Withdraw to external wallet"""
        body = {
            "currency": currency,
            "amount": str(amount),
            "address": address,
            "chain": chain
        }
        return await self._request("POST", "/withdrawals", body=body, is_futures=False)
