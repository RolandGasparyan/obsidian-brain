#!/usr/bin/env python3
"""
Trading Guru - Trinity of Profit Shorts-Only Gods Mode
Main application entry point for high-frequency trading.
"""

import argparse
import sys

sys.path.insert(0, '/home/runner/workspace')

from trading_guru.core.orchestrator import GodsModeOrchestrator
from trading_guru.core.config import config

def print_banner():
    """Print the Trading Guru banner."""
    banner = """
    
██╗   ██╗████████╗ ██████╗ █████╗ ██████╗ ██╗███╗   ██╗ ██████╗ 
██║   ██║╚══██╔══╝██╔═══██╗██╔══██╗██╔══██╗██║████╗  ██║██╔════╝ 
██║   ██║   ██║   ██║   ██║███████║██║  ██║██║██╔██╗ ██║██║  ███╗
██║   ██║   ██║   ██║   ██║██╔══██║██║  ██║██║██║╚██╗██║██║   ██║
╚██████╔╝   ██║   ╚██████╔╝██║  ██║██████╔╝██║██║ ╚████║╚██████╔╝
 ╚═════╝    ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝ ╚═╝╚═╝  ╚═══╝ ╚═════╝ 

           TRINITY OF PROFIT SHORTS-ONLY MODE
    """
    print(banner)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Trading Guru - Trinity of Profit Shorts-Only Gods Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--mode",
        default="trinity",
        help="Trading mode to run"
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=config.STARTING_BUDGET,
        help="Starting budget for trading"
    )
    parser.add_argument(
        "--risk",
        default=config.RISK_PROFILE,
        choices=["TRINITY_OF_PROFIT", "aggressive", "moderate", "conservative"],
        help="Risk profile"
    )
    
    args = parser.parse_args()
    
    print_banner()
    print(f"Initializing {config.RISK_PROFILE} SHORTS-ONLY GODS MODE...")
    print(f"   - Budget: ${args.budget:,.2f}")
    print(f"   - Risk Profile: {args.risk.upper()}")
    print(f"   - LLM Model: {config.LLM_MODEL}")
    print(f"   - Max Leverage: {config.MAX_LEVERAGE}x")
    print(f"   - Min Entry Size: ${config.MIN_ENTRY_SIZE_USD:.2f}")
    print("\n--- SYSTEM IS NOW LIVE ---")
    
    config.STARTING_BUDGET = args.budget
    config.RISK_PROFILE = args.risk
    
    orchestrator = GodsModeOrchestrator()
    
    try:
        orchestrator.run_loop()
    except KeyboardInterrupt:
        print("\n--- System shutting down (Keyboard Interrupt) ---")
        print(f"Final Daily PNL: ${orchestrator.state.daily_pnl:.2f}")
    except Exception as e:
        print(f"\n--- CRITICAL ERROR ---")
        print(f"An unhandled exception occurred: {e}")
        print("System stopped.")

if __name__ == "__main__":
    main()
