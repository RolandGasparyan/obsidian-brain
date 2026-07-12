#!/usr/bin/env python3
"""
====================================================================
AI RACE SCORING ENGINE
GODS LEVEL DAILY COMPETITION SCORING SYSTEM
====================================================================
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import json


@dataclass
class Trade:
    symbol: str
    entry_price: float
    exit_price: float
    size: float
    leverage: int
    pnl: float
    pnl_percent: float
    is_winner: bool
    confidence: int
    reasoning_quality: int  # 1-10
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AIDailyStats:
    name: str
    max_drawdown_percent: float = 0.0
    correct_no_trade: int = 0  # NO TRADE when market was bad
    total_no_trade: int = 0
    trades: List[Trade] = field(default_factory=list)
    
    @property
    def total_trades(self) -> int:
        return len(self.trades)
    
    @property
    def winning_trades(self) -> int:
        return sum(1 for t in self.trades if t.is_winner)
    
    @property
    def losing_trades(self) -> int:
        return sum(1 for t in self.trades if not t.is_winner)
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return (self.winning_trades / self.total_trades) * 100
    
    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)
    
    @property
    def avg_confidence(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return sum(t.confidence for t in self.trades) / self.total_trades
    
    @property
    def avg_reasoning_quality(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return sum(t.reasoning_quality for t in self.trades) / self.total_trades


class AIRaceScoringEngine:
    """
    GODS LEVEL SCORING ENGINE
    
    Scoring Philosophy:
    - Intelligence > Activity
    - Discipline > Frequency
    - Quality > Quantity
    - Survival > Aggression
    """
    
    # Score weights
    WEIGHTS = {
        'pnl': 30,              # 30% - Profitability
        'win_rate': 20,         # 20% - Win rate
        'discipline': 25,       # 25% - Discipline (correct NO TRADEs)
        'drawdown': 15,         # 15% - Risk management
        'reasoning': 10         # 10% - Reasoning quality
    }
    
    def __init__(self):
        self.daily_results = {}
        self.leaderboard = []
    
    def pnl_score(self, stats: AIDailyStats) -> float:
        """
        PnL Score: +10 per $1 profit, -15 per $1 loss
        Max: 100, Min: -100
        """
        pnl = stats.total_pnl
        
        if pnl >= 0:
            score = min(100, pnl * 10)
        else:
            score = max(-100, pnl * 15)
        
        return score * (self.WEIGHTS['pnl'] / 100)
    
    def win_rate_score(self, stats: AIDailyStats) -> float:
        """
        Win Rate Score:
        - 80%+ = 100 points
        - 60-80% = 60-80 points
        - 40-60% = 40-60 points
        - <40% = 0-40 points
        """
        if stats.total_trades == 0:
            return 50 * (self.WEIGHTS['win_rate'] / 100)  # Neutral if no trades
        
        wr = stats.win_rate
        score = min(100, wr * 1.25)  # Scale win rate to 0-100
        
        return score * (self.WEIGHTS['win_rate'] / 100)
    
    def discipline_score(self, stats: AIDailyStats) -> float:
        """
        Discipline Score:
        - Correct NO TRADE decisions when market was bad
        - +15 per correct NO TRADE
        - "NO TRADE is a powerful strategic decision"
        """
        if stats.total_no_trade == 0:
            return 50 * (self.WEIGHTS['discipline'] / 100)
        
        accuracy = (stats.correct_no_trade / stats.total_no_trade) * 100
        
        # Bonus for high correct NO TRADE count
        bonus = min(20, stats.correct_no_trade * 2)
        
        score = min(100, accuracy + bonus)
        
        return score * (self.WEIGHTS['discipline'] / 100)
    
    def drawdown_score(self, stats: AIDailyStats) -> float:
        """
        Drawdown Score:
        - 0% drawdown = 100 points
        - 1% drawdown = 90 points
        - 3% drawdown = 70 points
        - 5% drawdown = 50 points
        - 10%+ drawdown = 0 points
        """
        dd = stats.max_drawdown_percent
        
        if dd <= 0:
            score = 100
        elif dd <= 1:
            score = 100 - (dd * 10)
        elif dd <= 3:
            score = 90 - ((dd - 1) * 10)
        elif dd <= 5:
            score = 70 - ((dd - 3) * 10)
        elif dd <= 10:
            score = 50 - ((dd - 5) * 10)
        else:
            score = 0
        
        return score * (self.WEIGHTS['drawdown'] / 100)
    
    def reasoning_score(self, stats: AIDailyStats) -> float:
        """
        Reasoning Quality Score:
        - Based on average reasoning quality (1-10)
        - Scaled to 0-100
        """
        if stats.total_trades == 0:
            return 50 * (self.WEIGHTS['reasoning'] / 100)
        
        avg_quality = stats.avg_reasoning_quality
        score = avg_quality * 10  # Scale 1-10 to 10-100
        
        return score * (self.WEIGHTS['reasoning'] / 100)
    
    def total_score(self, stats: AIDailyStats) -> float:
        """
        Calculate total race score for an AI model
        """
        pnl = self.pnl_score(stats)
        win = self.win_rate_score(stats)
        discipline = self.discipline_score(stats)
        dd = self.drawdown_score(stats)
        reasoning = self.reasoning_score(stats)
        
        total = pnl + win + discipline + dd + reasoning
        
        return round(total, 2)
    
    def score_breakdown(self, stats: AIDailyStats) -> dict:
        """
        Get detailed score breakdown
        """
        return {
            'name': stats.name,
            'total_score': self.total_score(stats),
            'breakdown': {
                'pnl_score': round(self.pnl_score(stats), 2),
                'win_rate_score': round(self.win_rate_score(stats), 2),
                'discipline_score': round(self.discipline_score(stats), 2),
                'drawdown_score': round(self.drawdown_score(stats), 2),
                'reasoning_score': round(self.reasoning_score(stats), 2)
            },
            'stats': {
                'total_trades': stats.total_trades,
                'winning_trades': stats.winning_trades,
                'losing_trades': stats.losing_trades,
                'win_rate': round(stats.win_rate, 1),
                'total_pnl': round(stats.total_pnl, 2),
                'max_drawdown': round(stats.max_drawdown_percent, 2),
                'correct_no_trades': stats.correct_no_trade,
                'total_no_trades': stats.total_no_trade
            }
        }
    
    def update_leaderboard(self, all_stats: List[AIDailyStats]) -> List[tuple]:
        """
        Update and return the race leaderboard
        """
        self.leaderboard = []
        
        for stats in all_stats:
            score = self.total_score(stats)
            self.leaderboard.append((stats.name, score, stats))
        
        # Sort by score descending
        self.leaderboard.sort(key=lambda x: x[1], reverse=True)
        
        return self.leaderboard
    
    def print_leaderboard(self, all_stats: List[AIDailyStats]):
        """
        Print formatted race leaderboard
        """
        self.update_leaderboard(all_stats)
        
        print("\n" + "="*70)
        print("🏆 AI MODELS TRADING RACE - DAILY LEADERBOARD")
        print("="*70)
        
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
        
        for i, (name, score, stats) in enumerate(self.leaderboard):
            medal = medals[i] if i < len(medals) else f"{i+1}."
            
            print(f"\n{medal} {name}")
            print(f"   📊 Score: {score:.1f} points")
            print(f"   💰 PnL: ${stats.total_pnl:.2f} | Win Rate: {stats.win_rate:.0f}%")
            print(f"   📈 Trades: {stats.total_trades} | DD: {stats.max_drawdown_percent:.1f}%")
            print(f"   🧠 Correct NO TRADEs: {stats.correct_no_trade}/{stats.total_no_trade}")
        
        print("\n" + "="*70)
        
        # Winner announcement
        if self.leaderboard:
            winner = self.leaderboard[0]
            print(f"\n🏆 TODAY'S LEADER: {winner[0]} with {winner[1]:.1f} points!")
        
        print("="*70 + "\n")
    
    def save_results(self, all_stats: List[AIDailyStats], filename: str = "race_results.json"):
        """
        Save race results to JSON
        """
        self.update_leaderboard(all_stats)
        
        results = {
            "date": datetime.now().isoformat(),
            "race": "AI Models Trading Race",
            "leaderboard": []
        }
        
        for i, (name, score, stats) in enumerate(self.leaderboard):
            results["leaderboard"].append({
                "rank": i + 1,
                "name": name,
                "score": score,
                "breakdown": self.score_breakdown(stats)
            })
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return results


# AI Models list
AI_MODELS = [
    "GPT-5",
    "Claude",
    "DeepSeek",
    "Llama",
    "Gemini",
    "Mistral",
    "Qwen",
    "Grok"
]


def run_race_day():
    """
    Run daily race scoring
    """
    engine = AIRaceScoringEngine()
    all_stats = []

    for model in AI_MODELS:
        stats = AIDailyStats(
            name=model,
            max_drawdown_percent=1.0,
            correct_no_trade=6,
            total_no_trade=8,
            trades=[]
        )
        all_stats.append(stats)

    # Print leaderboard
    engine.print_leaderboard(all_stats)
    
    # Save results
    engine.save_results(all_stats)
    
    return engine.leaderboard


if __name__ == "__main__":
    run_race_day()
