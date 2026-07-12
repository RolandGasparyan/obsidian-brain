"""
Trading Guru Base Agent
Abstract base class for all AI trading agents.
"""

import os
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
from openai import OpenAI

from ..core.config import AgentConfig, config
from ..core.models import AgentAnalysis


class BaseAgent(ABC):
    """Abstract base class for all trading agents."""
    
    def __init__(self, agent_config: AgentConfig):
        self.config = agent_config
        self.name = agent_config.name
        self.role = agent_config.role
        self.model = agent_config.model
        self.temperature = agent_config.temperature
        self.max_tokens = agent_config.max_tokens
        
        # Initialize OpenAI client
        self.client = OpenAI()  # Uses environment variables
        
        # System prompt (to be defined by subclasses)
        self.system_prompt = ""
        
        # Analysis history
        self.analysis_history = []
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass
    
    @abstractmethod
    def format_analysis_prompt(self, market_data: dict, **kwargs) -> str:
        """Format the analysis prompt with market data."""
        pass
    
    @abstractmethod
    def parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data."""
        pass
    
    async def analyze(self, market_data: dict, **kwargs) -> AgentAnalysis:
        """Perform analysis on the provided market data."""
        try:
            # Get prompts
            system_prompt = self.get_system_prompt()
            user_prompt = self.format_analysis_prompt(market_data, **kwargs)
            
            # Call LLM
            response = await self._call_llm(system_prompt, user_prompt)
            
            # Parse response
            parsed = self.parse_response(response)
            
            # Create analysis object
            analysis = AgentAnalysis(
                agent_name=self.name,
                agent_role=self.role,
                timestamp=datetime.now(),
                signal=parsed.get("signal", "neutral"),
                confidence=parsed.get("confidence", 0.5),
                reasoning=parsed.get("reasoning", ""),
                key_findings=parsed.get("key_findings", []),
                entry_price=parsed.get("entry_price"),
                stop_loss=parsed.get("stop_loss"),
                target_1=parsed.get("target_1"),
                target_2=parsed.get("target_2"),
                metadata=parsed.get("metadata", {})
            )
            
            # Store in history
            self.analysis_history.append(analysis)
            
            return analysis
            
        except Exception as e:
            # Return neutral analysis on error
            return AgentAnalysis(
                agent_name=self.name,
                agent_role=self.role,
                timestamp=datetime.now(),
                signal="neutral",
                confidence=0.0,
                reasoning=f"Error during analysis: {str(e)}",
                key_findings=[f"Analysis failed: {str(e)}"],
                metadata={"error": str(e)}
            )
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM with the given prompts."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"LLM call failed: {str(e)}")
    
    def _extract_json_from_response(self, response: str) -> dict:
        """Extract JSON from LLM response."""
        try:
            # Try to find JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return {}
    
    def _extract_price_from_text(self, text: str, keyword: str) -> Optional[float]:
        """Extract a price value from text near a keyword."""
        import re
        
        # Look for patterns like "$95,000" or "95000" near the keyword
        pattern = rf'{keyword}[:\s]*\$?([\d,]+\.?\d*)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            price_str = match.group(1).replace(',', '')
            try:
                return float(price_str)
            except ValueError:
                pass
        
        return None
    
    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "name": self.name,
            "role": self.role,
            "model": self.model,
            "enabled": self.config.enabled,
            "analyses_performed": len(self.analysis_history)
        }
    
    def clear_history(self):
        """Clear analysis history."""
        self.analysis_history = []
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"
