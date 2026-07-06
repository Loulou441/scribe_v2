"""
Module de questions-réponses interactives sur une transcription et son compte rendu,
avec conservation de l'historique de conversation.
"""

from pathlib import Path
from groq import APIError, APIConnectionError, RateLimitError
from agent import Agent
from config import LLM_MODEL

PROMPT__QA_PATH = Path(__file__).parent / "prompts_LLM" / "qa_system_prompt.txt"

class QAAgent(Agent):

    def __init__(self, transcription: str, report: dict):
        super().__init__()
        system_prompt = self._build_system_prompt(transcription, report)
        self.messages = [{"role": "system", "content": system_prompt}]

    def _load_prompt_template(self) -> str:
        if not PROMPT__QA_PATH.is_file():
            raise FileNotFoundError(f"Fichier de prompt système introuvable : {PROMPT__QA_PATH}")
        return PROMPT__QA_PATH.read_text(encoding="utf-8")

    def _build_system_prompt(self, transcription: str, report: dict) -> str:
        template = self._load_prompt_template()

        points_cles = report.get("points_cles", [])
        decisions_actions = report.get("decisions_actions", [])

        points_cles_str = "\n".join(f"- {p}" for p in points_cles) if points_cles else "(aucun)"
        decisions_actions_str = "\n".join(f"- {d}" for d in decisions_actions) if decisions_actions else "(aucune)"

        return (
            template
            .replace("{{TRANSCRIPTION}}", transcription)
            .replace("{{TITRE}}", report.get("titre", ""))
            .replace("{{RESUME}}", report.get("resume", ""))
            .replace("{{POINTS_CLES}}", points_cles_str)
            .replace("{{DECISIONS_ACTIONS}}", decisions_actions_str)
        )

    def ask(self, question: str) -> str:
        """
        Ajoute la question à l'historique, interroge le LLM, ajoute la réponse
        à l'historique et la retourne.
        """
        self.messages.append({"role": "user", "content": question})

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                temperature=0.0,
                messages=self.messages,
            )
        except (APIError, APIConnectionError, RateLimitError) as e:
            self.messages.pop()
            raise RuntimeError(f"Échec de la réponse via l'API Groq : {e}") from e

        answer = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def reset_history(self):
        """Repart de zéro en ne conservant que le prompt système initial."""
        self.messages = [self.messages[0]]