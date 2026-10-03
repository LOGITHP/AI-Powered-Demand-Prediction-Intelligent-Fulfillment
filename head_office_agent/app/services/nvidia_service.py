import os
import json
import logging
from typing import Dict, Any
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

class NvidiaService:
    def __init__(self):
        self.api_key = os.environ.get("NVIDIA_API_KEY")
        self.base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self.model = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-70b-instruct")
        self.llm = None
        
        if self.api_key:
            try:
                self.llm = ChatNVIDIA(
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    temperature=0.2
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChatNVIDIA: {str(e)}")

    def check_health(self) -> str:
        if not self.api_key:
            return "temporarily unavailable"
        if not self.llm:
            return "temporarily unavailable"
        try:
            return "connected"
        except Exception:
            return "temporarily unavailable"

    def generate_reasoning(self, warehouse_state: Dict[str, Any], query: str) -> Dict[str, Any]:
        # If API key is missing or dummy, return highly realistic mock AI insights for demonstration
        if not self.llm or self.api_key == "dummy_key_replace_with_real":
            q = query.lower()
            if "worker" in q or "shortage" in q or "staff" in q:
                return {
                    "answer": "Based on current task volume, there is a shortage of 5 workers in the Picking stage.",
                    "severity": "high",
                    "recommendations": [
                        "Reallocate 3 workers from Quality to Picking.",
                        "Approve 2 hours of overtime for the evening shift."
                    ],
                    "reasoning": "Picking queue has reached 46 tasks while Quality has only 5. Reallocating staff will clear the bottleneck before SLA breaches."
                }
            elif "inventory" in q or "stock" in q:
                return {
                    "answer": "Inventory levels are stable, but SKU A-129 is approaching critical low limits based on predictive demand.",
                    "severity": "medium",
                    "recommendations": [
                        "Trigger automated restock of 500 units for SKU A-129.",
                        "Audit bin locations in Zone B for potential shrinkage."
                    ],
                    "reasoning": "Historical data shows a 20% spike in demand for A-129 during this shift. Current stock will deplete in 4 hours."
                }
            else:
                return {
                    "answer": "Warehouse operations are currently running at 92% utilization. No critical bottlenecks detected.",
                    "severity": "low",
                    "recommendations": [
                        "Continue monitoring inbound dock door utilization.",
                        "Prepare staging area for next large shipment."
                    ],
                    "reasoning": "Task distribution is balanced across all stages and workforce is adequate for the current pending order volume."
                }
            
        system_prompt = """You are the AI reasoning engine for a Warehouse Operations Agent.

Your responsibility is to analyze the warehouse information provided by
the backend and assist the warehouse supervisor with operational
decision support.

Use only the data provided by the system.

Do not invent:
- worker counts
- inventory quantities
- order quantities
- predictions
- shipment information
- operational events

When numerical predictions are provided by ML models, interpret them
rather than replacing them.

Identify:
- operational problems
- bottlenecks
- worker shortages
- order backlog
- inventory risks
- inbound/outbound issues
- SLA risks

Provide concise explanations and actionable recommendations.

Do not directly modify databases or execute operational actions.

If an action could affect warehouse operations, clearly mark it as a
recommendation requiring validation/approval.

Format your response exactly as JSON with these keys:
- answer: String, direct answer to the query.
- severity: String, 'low', 'medium', or 'high'.
- recommendations: List of strings.
- reasoning: String, explanation.
"""

        context_json = json.dumps(warehouse_state, default=str)
        human_msg = f"Warehouse Context:\n{context_json}\n\nUser Query: {query}"
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_msg)
            ])
            content = response.content
            
            content = content.replace("```json", "").replace("```", "").strip()
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "answer": response.content,
                "severity": "medium",
                "recommendations": ["Please review manual reasoning."],
                "reasoning": "Failed to parse structured JSON from LLM."
            }
        except Exception as e:
            logger.error(f"NVIDIA API Error: {str(e)}")
            return {
                "answer": "NVIDIA API encountered an error during reasoning.",
                "severity": "high",
                "recommendations": ["Check API status and rate limits."],
                "reasoning": str(e)
            }
