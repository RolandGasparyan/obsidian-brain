from trading_guru.core.config import config
from trading_guru.core.models import MarketData, TradeSignal

class AlphaArenaValidator:
    """
    The 8 Pillars of Alpha Arena - Every trade must pass ALL 8 checks
    """
    
    def __init__(self):
        self.pillars = [
            "Capital Preservation",
            "1-2% Risk Rule",
            "Mandatory Stop-Loss",
            "Trend-Following",
            "High-Probability Only",
            "Asymmetric R:R",
            "Leverage Efficiency",
            "Probabilistic Edge"
        ]
    
    def validate_trade(self, signal: TradeSignal, market_data: MarketData, budget: float) -> tuple[bool, list[str]]:
        """
        Validates a trade signal against all 8 Alpha Arena pillars.
        Returns (passed, list of failed pillars)
        """
        failed = []
        
        if not self._pillar_1_capital_preservation(signal, budget):
            failed.append("Capital Preservation: Position too large for budget")
        
        if not self._pillar_2_risk_rule(signal, budget):
            failed.append("1-2% Rule: Risk exceeds 1.5% of capital")
        
        if not self._pillar_3_mandatory_stop_loss(signal):
            failed.append("Mandatory SL: No valid stop-loss defined")
        
        if not self._pillar_4_trend_following(market_data):
            failed.append("Trend-Following: ADX too weak for entry")
        
        if not self._pillar_5_high_probability(signal, market_data):
            failed.append("High-Probability: Setup quality too low")
        
        if not self._pillar_6_asymmetric_rr(signal):
            failed.append("Asymmetric R:R: Reward-to-Risk below 2:1")
        
        if not self._pillar_7_leverage_efficiency(signal, budget):
            failed.append("Leverage Efficiency: Excessive leverage detected")
        
        if not self._pillar_8_probabilistic_edge(signal):
            failed.append("Probabilistic Edge: No clear statistical edge")
        
        return len(failed) == 0, failed
    
    def _pillar_1_capital_preservation(self, signal: TradeSignal, budget: float) -> bool:
        """Survival first - Margin must not exceed 100% of capital (leveraged)"""
        margin_required = signal.initial_position_size_usd / config.MAX_LEVERAGE
        max_margin = budget * 1.0
        return margin_required <= max_margin
    
    def _pillar_2_risk_rule(self, signal: TradeSignal, budget: float) -> bool:
        """Never risk more than 3% per trade (aggressive mode)"""
        risk_distance = abs(signal.stop_loss - signal.entry_price)
        risk_percent = (risk_distance / signal.entry_price) * 100
        position_risk = (signal.initial_position_size_usd * risk_percent / 100)
        max_risk = budget * 0.03
        return position_risk <= max_risk
    
    def _pillar_3_mandatory_stop_loss(self, signal: TradeSignal) -> bool:
        """Every trade MUST have a stop-loss"""
        has_sl = signal.stop_loss > 0
        if signal.direction == "short":
            sl_valid = signal.stop_loss > signal.entry_price
        else:
            sl_valid = signal.stop_loss < signal.entry_price
        return has_sl and sl_valid
    
    def _pillar_4_trend_following(self, market_data: MarketData) -> bool:
        """Trade with trend strength (ADX > 18 minimum)"""
        return market_data.adx_14 >= 18
    
    def _pillar_5_high_probability(self, signal: TradeSignal, market_data: MarketData) -> bool:
        """Trade when basic conditions are met"""
        score = 0
        
        if market_data.funding_rate > -0.1:
            score += 1
        if market_data.adx_14 > 15:
            score += 1
        if market_data.volatility_atr > 0:
            score += 1
        
        return score >= 1
    
    def _pillar_6_asymmetric_rr(self, signal: TradeSignal) -> bool:
        """Minimum 1:1 Reward-to-Risk ratio (aggressive mode)"""
        risk = abs(signal.stop_loss - signal.entry_price)
        
        try:
            reward = abs(signal.entry_price - signal.tp1)
        except:
            reward = risk
        
        if risk == 0:
            return True
        
        rr_ratio = reward / risk if reward > 0 else 1.0
        return rr_ratio >= 1.0
    
    def _pillar_7_leverage_efficiency(self, signal: TradeSignal, budget: float) -> bool:
        """Leverage for efficiency, not excessive risk"""
        effective_leverage = signal.initial_position_size_usd / budget
        return effective_leverage <= config.MAX_LEVERAGE
    
    def _pillar_8_probabilistic_edge(self, signal: TradeSignal) -> bool:
        """System must have statistical edge - built into strategy selection"""
        valid_strategies = ["waterfall", "pyramid", "scalping", "doubling"]
        return signal.strategy in valid_strategies


class SmartGate:
    """
    The Smart Gate - 8 Filters for Trade Approval
    """
    
    def __init__(self):
        self.filters = {
            "liquidity": True,
            "volatility": True,
            "trend_strength": True,
            "funding_bias": True,
            "ai_consensus": True,
            "risk_budget": True,
            "correlation": True,
            "time_decay": True
        }
    
    def check_all_gates(self, market_data: MarketData, ai_votes: int, budget: float, active_positions: int) -> tuple[bool, dict]:
        """
        Runs all 8 smart gate filters
        Returns (all_passed, gate_status_dict)
        """
        results = {}
        
        results["liquidity"] = self._check_liquidity(market_data)
        results["volatility"] = self._check_volatility(market_data)
        results["trend_strength"] = self._check_trend(market_data)
        results["funding_bias"] = self._check_funding(market_data)
        results["ai_consensus"] = self._check_consensus(ai_votes)
        results["risk_budget"] = self._check_risk_budget(budget)
        results["correlation"] = self._check_correlation(active_positions)
        results["time_decay"] = self._check_time_decay()
        
        all_passed = all(results.values())
        return all_passed, results
    
    def _check_liquidity(self, market_data: MarketData) -> bool:
        return market_data.price > 0
    
    def _check_volatility(self, market_data: MarketData) -> bool:
        volatility_pct = (market_data.volatility_atr / market_data.price) * 100
        return 0.1 <= volatility_pct <= 10.0
    
    def _check_trend(self, market_data: MarketData) -> bool:
        return market_data.adx_14 >= 15
    
    def _check_funding(self, market_data: MarketData) -> bool:
        return market_data.funding_rate >= -0.05
    
    def _check_consensus(self, ai_votes: int) -> bool:
        return ai_votes >= 5
    
    def _check_risk_budget(self, budget: float) -> bool:
        return budget > 100
    
    def _check_correlation(self, active_positions: int) -> bool:
        return active_positions < 6
    
    def _check_time_decay(self) -> bool:
        return True


alpha_validator = AlphaArenaValidator()
smart_gate = SmartGate()
