import os

class Config:
    # General Settings
    PROJECT_NAME = "Trading Guru - Trinity of Profit Shorts"
    BASE_CURRENCY = "USDT"
    
    # API Keys (Read from Replit Secrets/Environment)
    OPENAI_API_KEY = os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL")
    LLM_MODEL = "gpt-4o-mini"
    
    # Trading Parameters
    STARTING_BUDGET = 100.0
    RISK_PROFILE = "TRINITY_OF_PROFIT"
    MAX_LEVERAGE = 50 
    MIN_ENTRY_SIZE_USD = 1.0
    
    # Strategy Parameters
    MIN_CONFLUENCE_SCORE = 85
    ROTATION_THRESHOLD = 50
    
    # Timeouts
    SCAN_INTERVAL_SECONDS = 30
    ROTATION_CHECK_SECONDS = 5
    
    # Trading Direction
    TRADING_DIRECTION = "SHORT_ONLY"
    
    # Mock Data Flag - SET TO FALSE FOR REAL API CALLS
    MOCK_DATA = False

config = Config()
