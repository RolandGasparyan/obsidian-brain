#!/usr/bin/env python3
"""
Test script to verify all 6 AI agents are working with real OpenAI API calls.
"""

import sys
sys.path.insert(0, '/home/runner/workspace')

from trading_guru.core.config import config
from trading_guru.core.models import MarketData
from trading_guru.agents.llm_agent import ALL_AGENTS, get_multi_agent_consensus
import time

def test_individual_agents():
    """Test each agent individually with sample market data."""
    
    print("="*70)
    print("TESTING ALL 6 AI AGENTS - REAL API MODE")
    print(f"Mock Mode: {config.MOCK_DATA}")
    print("="*70)
    
    test_data = MarketData(
        symbol="BTC/USDT",
        price=95000.00,
        volume_24h=5000000000,
        volatility_atr=1500.0,
        adx_14=45.0,
        spread_percent=0.002,
        funding_rate=0.15,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    print(f"\nTest Market Data:")
    print(f"  Symbol: {test_data.symbol}")
    print(f"  Price: ${test_data.price:,.2f}")
    print(f"  Volume: ${test_data.volume_24h:,.0f}")
    print(f"  ATR: {test_data.volatility_atr:.2f}")
    print(f"  ADX: {test_data.adx_14:.1f}")
    print(f"  Funding Rate: {test_data.funding_rate:.4f}%")
    print()
    
    results = []
    
    for i, agent in enumerate(ALL_AGENTS, 1):
        print(f"\n--- Agent {i}/6: {agent.name} ({agent.role}) ---")
        print(f"Specialty: {agent.specialty}")
        
        start = time.time()
        result = agent.analyze(test_data, "Trinity of Profit - SHORT analysis")
        elapsed = time.time() - start
        
        print(f"Score: {result['score']}")
        print(f"Direction: {result['signal'].direction}")
        print(f"Strategy: {result['signal'].strategy}")
        print(f"Confidence: {result['signal'].confidence}")
        print(f"Reasoning: {result['signal'].reasoning[:100]}...")
        print(f"API Time: {elapsed:.2f}s")
        
        results.append({
            "agent": agent.name,
            "score": result["score"],
            "direction": result["signal"].direction,
            "api_time": elapsed
        })
    
    print("\n" + "="*70)
    print("INDIVIDUAL AGENT TEST RESULTS SUMMARY")
    print("="*70)
    
    for r in results:
        status = "OK" if r["direction"] == "short" else "HOLD"
        print(f"  {r['agent']:15} | Score: {r['score']:3} | Direction: {r['direction']:5} | Time: {r['api_time']:.2f}s | [{status}]")
    
    return results

def test_multi_agent_consensus():
    """Test the full multi-agent consensus system."""
    
    print("\n" + "="*70)
    print("TESTING MULTI-AGENT CONSENSUS SYSTEM")
    print("="*70)
    
    test_data = MarketData(
        symbol="ETH/USDT",
        price=3500.00,
        volume_24h=2000000000,
        volatility_atr=150.0,
        adx_14=52.0,
        spread_percent=0.003,
        funding_rate=0.25,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
    )
    
    print(f"\nTest Data: {test_data.symbol} @ ${test_data.price:,.2f}")
    print(f"ADX: {test_data.adx_14:.1f} | Funding: {test_data.funding_rate:.4f}%")
    
    start = time.time()
    consensus = get_multi_agent_consensus(test_data, "Trinity of Profit Analysis")
    elapsed = time.time() - start
    
    print("\n" + "="*70)
    print("CONSENSUS RESULT")
    print("="*70)
    print(f"  Symbol: {consensus['symbol']}")
    print(f"  Consensus: {consensus['consensus'].upper()}")
    print(f"  Average Score: {consensus['avg_score']:.1f}")
    print(f"  Short Votes: {consensus['short_votes']}/6")
    print(f"  Best Signal Strategy: {consensus['best_signal'].strategy}")
    print(f"  Total Time: {elapsed:.2f}s")
    
    return consensus

if __name__ == "__main__":
    print("\n" + "="*70)
    print("TRADING GURU - AI AGENT VERIFICATION TEST")
    print("="*70)
    print(f"Config: MOCK_DATA = {config.MOCK_DATA}")
    print(f"Model: {config.LLM_MODEL}")
    print()
    
    individual_results = test_individual_agents()
    
    consensus_result = test_multi_agent_consensus()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    
    all_working = all(r["score"] > 0 for r in individual_results)
    print(f"All Agents Working: {'YES' if all_working else 'NO'}")
    print(f"Consensus Achieved: {consensus_result['consensus'].upper()}")
    print(f"System Ready: {'YES' if all_working else 'NO'}")
