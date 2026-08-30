import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
import httpx

from app.core.config import settings
from app.schemas.risk import AIAssessmentResultSchema
from app.schemas.assistant import ChatMessagePayload

logger = logging.getLogger("vendorguard.services.llm")


class BaseLLMService(ABC):
    """Abstract interface for LLM provider implementations (OpenAI, Ollama, etc.)."""

    @abstractmethod
    async def analyze_vendor_policy(self, prompt: str) -> AIAssessmentResultSchema:
        """Invokes LLM to return structured risk assessment data matching AIAssessmentResultSchema."""
        pass

    @abstractmethod
    async def generate_assistant_answer(
        self,
        vendor_name: str,
        evidence_text: str,
        user_message: str,
        conversation_history: Optional[List[ChatMessagePayload]] = None
    ) -> str:
        """Invokes LLM with grounded RAG evidence context and conversation history."""
        pass

    @abstractmethod
    async def generate_executive_summary(
        self,
        vendor_name: str,
        overall_score: float,
        risk_tier: str,
        category_scores: Dict[str, float],
        key_findings: List[Dict[str, Any]]
    ) -> str:
        """Synthesizes executive risk report summary."""
        pass


class OpenAILLMService(BaseLLMService):
    """OpenAI API implementation using AsyncOpenAI."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL

    async def analyze_vendor_policy(self, prompt: str) -> AIAssessmentResultSchema:
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "AI assessment unavailable — OpenAI API key is not configured. Please supply OPENAI_API_KEY in environment."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            system_instruction = (
                "You are an expert AI Risk & Security Auditor. "
                "Analyze vendor policy documents and return structured JSON matching the requested schema. "
                "For every finding, provide exact verbatim quotes as evidence from the provided policy text, "
                "specify the document source URL, category (Privacy, Security, Compliance, or Legal), "
                "severity (Low, Medium, High, Critical), confidence (0.0 to 1.0), and actionable recommendation. "
                "Do NOT invent quotes or URLs not present in the supplied policy text."
            )

            response = await client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                response_format=AIAssessmentResultSchema,
                temperature=0.1,
            )

            return response.choices[0].message.parsed

        except Exception as exc:
            logger.error("OpenAI API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"LLM API call failed: {str(exc)}") from exc

    async def generate_assistant_answer(
        self,
        vendor_name: str,
        evidence_text: str,
        user_message: str,
        conversation_history: Optional[List[ChatMessagePayload]] = None
    ) -> str:
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "Assistant unavailable — OpenAI API key is not configured. Please supply OPENAI_API_KEY in environment."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            system_instruction = (
                f"You are VendorGuard AI Assistant, an expert vendor risk analyst.\n"
                f"Your task is to answer user questions about vendor '{vendor_name}'.\n\n"
                f"CRITICAL GROUNDING RULES:\n"
                f"1. Answer ONLY using the provided policy document evidence below.\n"
                f"2. Do NOT invent facts, assume unstated details, or use external knowledge.\n"
                f"3. If the provided policy evidence is insufficient or does not contain the answer, "
                f"explicitly state: 'There is insufficient evidence in the indexed policy documents for this vendor to answer your request.'\n"
                f"4. Keep your answer professional, objective, concise, and focused on security, privacy, and compliance risks.\n\n"
                f"--- RETRIEVED POLICY EVIDENCE FOR {vendor_name.upper()} ---\n"
                f"{evidence_text}\n"
            )

            messages = [{"role": "system", "content": system_instruction}]

            if conversation_history:
                for msg in conversation_history:
                    role = "user" if msg.role == "user" else "assistant"
                    messages.append({"role": role, "content": msg.content})

            messages.append({"role": "user", "content": user_message})

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.1,
            )

            answer_content = response.choices[0].message.content
            return answer_content.strip() if answer_content else "No response generated."

        except Exception as exc:
            logger.error("OpenAI LLM API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Assistant LLM service failure: {str(exc)}") from exc

    async def generate_executive_summary(
        self,
        vendor_name: str,
        overall_score: float,
        risk_tier: str,
        category_scores: Dict[str, float],
        key_findings: List[Dict[str, Any]]
    ) -> str:
        if not self.api_key or not self.api_key.strip():
            return (
                f"Executive Summary for {vendor_name}: Overall Risk Score is {overall_score} ({risk_tier} Risk Tier). "
                f"Category Breakdown: " + ", ".join(f"{k}: {v}" for k, v in category_scores.items()) + ". "
                f"Verified findings: {len(key_findings)} risk item(s) identified."
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            prompt = (
                f"Synthesize an executive security & risk report summary for vendor '{vendor_name}'.\n"
                f"Overall Score: {overall_score}/100\n"
                f"Risk Tier: {risk_tier}\n"
                f"Category Scores: {category_scores}\n"
                f"Key Findings: {key_findings}\n\n"
                f"Provide a 2-3 paragraph executive summary covering risk posture, key vulnerabilities, "
                f"and strategic recommendations for security analysts."
            )

            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a Chief Information Security Officer (CISO) executive reporting assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )

            summary = response.choices[0].message.content
            return summary.strip() if summary else f"Executive report generated for {vendor_name}."

        except Exception as exc:
            logger.warning(f"OpenAI call failed for ExecutiveReportAgent: {str(exc)}. Falling back to structured summary.")
            return (
                f"Executive Summary for {vendor_name}: Overall Risk Score is {overall_score} ({risk_tier} Risk Tier). "
                f"Category Breakdown: " + ", ".join(f"{k}: {v}" for k, v in category_scores.items()) + "."
            )


class OllamaLLMService(BaseLLMService):
    """Local Ollama HTTP API implementation using httpx."""

    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model_name = model_name or settings.OLLAMA_LLM_MODEL

    async def analyze_vendor_policy(self, prompt: str) -> AIAssessmentResultSchema:
        system_instruction = (
            "You are an expert AI Risk & Security Auditor. "
            "Analyze vendor policy documents and return structured JSON matching the requested schema.\n"
            "JSON SCHEMA:\n"
            "{\n"
            '  "summary": "High level executive summary string",\n'
            '  "findings": [\n'
            '    {\n'
            '      "category": "Privacy" | "Security" | "Compliance" | "Legal",\n'
            '      "finding": "Short finding title",\n'
            '      "severity": "Low" | "Medium" | "High" | "Critical",\n'
            '      "evidence": "Exact verbatim quote from provided policy text",\n'
            '      "source_url": "URL string from policy text",\n'
            '      "confidence": 0.0 to 1.0,\n'
            '      "recommendation": "Actionable recommendation string",\n'
            '      "is_verified": true | false\n'
            '    }\n'
            '  ]\n'
            "}\n"
            "For every finding, provide exact verbatim quotes as evidence from the provided policy text. "
            "Do NOT invent quotes or URLs not present in the supplied policy text."
        )

        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )
                res.raise_for_status()
                data = res.json()

            raw_content = data.get("message", {}).get("content", "")
            if not raw_content:
                raise ValueError("Empty response received from Ollama model.")

            # Parse JSON content into Pydantic AIAssessmentResultSchema
            parsed_json = json.loads(raw_content)
            return AIAssessmentResultSchema.model_validate(parsed_json)

        except Exception as exc:
            logger.error("Ollama API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Ollama LLM service failure: {str(exc)}") from exc

    async def generate_assistant_answer(
        self,
        vendor_name: str,
        evidence_text: str,
        user_message: str,
        conversation_history: Optional[List[ChatMessagePayload]] = None
    ) -> str:
        system_instruction = (
            f"You are VendorGuard AI Assistant, an expert vendor risk analyst.\n"
            f"Your task is to answer user questions about vendor '{vendor_name}'.\n\n"
            f"CRITICAL GROUNDING RULES:\n"
            f"1. Answer ONLY using the provided policy document evidence below.\n"
            f"2. Do NOT invent facts, assume unstated details, or use external knowledge.\n"
            f"3. If the provided policy evidence is insufficient or does not contain the answer, "
            f"explicitly state: 'There is insufficient evidence in the indexed policy documents for this vendor to answer your request.'\n"
            f"4. Keep your answer professional, objective, concise, and focused on security, privacy, and compliance risks.\n\n"
            f"--- RETRIEVED POLICY EVIDENCE FOR {vendor_name.upper()} ---\n"
            f"{evidence_text}\n"
        )

        messages = [{"role": "system", "content": system_instruction}]

        if conversation_history:
            for msg in conversation_history:
                role = "user" if msg.role == "user" else "assistant"
                messages.append({"role": role, "content": msg.content})

        messages.append({"role": "user", "content": user_message})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.1}
                    }
                )
                res.raise_for_status()
                data = res.json()

            answer = data.get("message", {}).get("content", "").strip()
            return answer if answer else "No response generated."

        except Exception as exc:
            logger.error("Ollama Assistant API call failed: %s", str(exc), exc_info=True)
            raise RuntimeError(f"Ollama Assistant service failure: {str(exc)}") from exc

    async def generate_executive_summary(
        self,
        vendor_name: str,
        overall_score: float,
        risk_tier: str,
        category_scores: Dict[str, float],
        key_findings: List[Dict[str, Any]]
    ) -> str:
        prompt = (
            f"Synthesize an executive security & risk report summary for vendor '{vendor_name}'.\n"
            f"Overall Score: {overall_score}/100\n"
            f"Risk Tier: {risk_tier}\n"
            f"Category Scores: {category_scores}\n"
            f"Key Findings: {key_findings}\n\n"
            f"Provide a 2-3 paragraph executive summary covering risk posture, key vulnerabilities, "
            f"and strategic recommendations for security analysts."
        )

        messages = [
            {"role": "system", "content": "You are a Chief Information Security Officer (CISO) executive reporting assistant."},
            {"role": "user", "content": prompt}
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0.2}
                    }
                )
                res.raise_for_status()
                data = res.json()

            summary = data.get("message", {}).get("content", "").strip()
            return summary if summary else f"Executive report generated for {vendor_name}."

        except Exception as exc:
            logger.warning(f"Ollama call failed for ExecutiveReportAgent: {str(exc)}. Falling back to structured summary.")
            return (
                f"Executive Summary for {vendor_name}: Overall Risk Score is {overall_score} ({risk_tier} Risk Tier). "
                f"Category Breakdown: " + ", ".join(f"{k}: {v}" for k, v in category_scores.items()) + "."
            )


def get_llm_service(
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> BaseLLMService:
    """Factory function returning the configured LLM provider service."""
    target_provider = provider or (
        "openai" if api_key is not None else settings.AI_PROVIDER
    )
    target_provider = target_provider.lower().strip()

    if target_provider == "ollama":
        return OllamaLLMService(model_name=model_name)
    elif target_provider == "openai":
        return OpenAILLMService(api_key=api_key, model_name=model_name)
    else:
        raise ValueError(
            f"Invalid AI_PROVIDER '{target_provider}'. Supported providers are 'ollama' or 'openai'."
        )
