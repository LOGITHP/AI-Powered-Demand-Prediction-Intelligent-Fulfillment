from abc import ABC, abstractmethod
from typing import Dict, Any, List
import os
import json

class LLMProvider(ABC):
    @abstractmethod
    def generate_response(self, prompt: str) -> str:
        pass

    @abstractmethod
    def select_tool(self, prompt: str, available_tools: List[str]) -> str:
        pass

    @abstractmethod
    def summarize_state(self, state: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    def generate_explanation(self, decision: Dict[str, Any]) -> str:
        pass

    def get_chat_model(self):
        """Underlying LangChain chat model, or None for mock providers."""
        return None

class MockLLMProvider(LLMProvider):
    def generate_response(self, prompt: str) -> str:
        return "This is a mock LLM response based on your query."
        
    def select_tool(self, prompt: str, available_tools: List[str]) -> str:
        return available_tools[0] if available_tools else ""
        
    def summarize_state(self, state: Dict[str, Any]) -> str:
        return "Mock state summary."
        
    def generate_explanation(self, decision: Dict[str, Any]) -> str:
        return "Mock explanation for the given decision."

class NvidiaLLMProvider(LLMProvider):
    def __init__(self):
        from langchain_google_genai import ChatGoogleGenAI
        api_key = os.environ.get("GOOGLE_API_KEY")
        model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        
        self.llm = ChatGoogleGenAI(
            model=model,
            google_api_key=api_key,
            temperature=0.2
        )

    def generate_response(self, prompt: str) -> str:
        response = self.llm.invoke(prompt)
        return response.content

    def get_chat_model(self):
        return self.llm

    def select_tool(self, prompt: str, available_tools: List[str]) -> str:
        system_prompt = f"You are a tool selector. Available tools: {', '.join(available_tools)}. Respond ONLY with the exact name of the best tool for the user's prompt. Do not add any extra text."
        response = self.llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ])
        return response.content.strip()

    def summarize_state(self, state: Dict[str, Any]) -> str:
        state_json = json.dumps(state, default=str)
        prompt = f"Summarize the following warehouse network state concisely in 2-3 sentences:\n\n{state_json}"
        return self.generate_response(prompt)

    def generate_explanation(self, decision: Dict[str, Any]) -> str:
        decision_json = json.dumps(decision, default=str)
        prompt = f"Explain the reasoning behind this decision in a clear, professional paragraph suitable for a human manager to review:\n\n{decision_json}"
        return self.generate_response(prompt)
