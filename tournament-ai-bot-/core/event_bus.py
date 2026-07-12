"""
Event Bus System
Institutional-grade event dispatcher
"""

from collections import defaultdict
from typing import Callable, Any


class EventBus:
    def __init__(self):
        # Dictionary of event_type -> list of handlers
        self.listeners = defaultdict(list)

    def register(self, event_type: str, handler: Callable):
        """
        Register a handler for a specific event type
        """
        self.listeners[event_type].append(handler)

    def unregister(self, event_type: str, handler: Callable):
        """
        Remove a handler
        """
        if handler in self.listeners[event_type]:
            self.listeners[event_type].remove(handler)

    def emit(self, event_type: str, data: Any = None):
        """
        Emit event to all registered handlers
        """
        if event_type not in self.listeners:
            return

        for handler in self.listeners[event_type]:
            try:
                handler(data)
            except Exception as e:
                print(f"Event handler error ({event_type}): {e}")

    def clear(self):
        """
        Remove all listeners
        """
        self.listeners.clear()
class EventBus:
    def __init__(self):
        self.listeners = {}

    def register(self, event_type, handler):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def emit(self, event_type, data=None):
        if event_type in self.listeners:
            for handler in self.listeners[event_type]:
                handler(data)
class EventBus:
    def __init__(self):
        self.listeners = {}

    def register(self, event_type, handler):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def emit(self, event_type, data=None):
        if event_type in self.listeners:
            for handler in self.listeners[event_type]:
                handler(data)
class EventBus:
    def __init__(self):
        self.listeners = {}

    def register(self, event_type, handler):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def emit(self, event_type, data=None):
        if event_type in self.listeners:
            for handler in self.listeners[event_type]:
                handler(data)
class EventBus:
    def __init__(self):
        self.listeners = {}

    def register(self, event_type, handler):
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(handler)

    def emit(self, event_type, data=None):
        if event_type in self.listeners:
            for handler in self.listeners[event_type]:
                handler(data)
