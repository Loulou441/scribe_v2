"""
Module de génération de compte rendu structuré à partir d'une transcription brute,
via le modèle LLM configuré.
"""
from datetime import datetime
from pathlib import Path
from groq import APIError, APIConnectionError, RateLimitError
from agent import Agent
from config import LLM_MODEL
from speech_to_text_agent import SpeechToTextAgent
import json

PROMPT_PATH = Path(__file__).parent / "prompts_LLM" / "summary_generator_prompt.txt"

class SummaryAgent(Agent):

    def __init__(self):
        super().__init__()

    def load_system_prompt(self) -> str:
        if not PROMPT_PATH.is_file():
            raise FileNotFoundError(f"Fichier de prompt système introuvable : {PROMPT_PATH}")
        return PROMPT_PATH.read_text(encoding="utf-8")

    def generate_report(self, transcription: str) -> str:
        system_prompt = self.load_system_prompt()

        try:
            response = self.client.chat.completions.create(
                model=LLM_MODEL,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription},
                ],
            )
        except (APIError, APIConnectionError, RateLimitError) as e:
            raise RuntimeError(
                f"Échec de la génération du compte rendu via l'API Groq : {e}"
            ) from e

        raw_content = response.choices[0].message.content
    
        try:
            report = json.loads(raw_content)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"La réponse du modèle n'est pas un JSON valide : {e}\nContenu reçu : {raw_content}"
            ) from e
    
        return report

    def format_as_markdown(self,report: dict) -> str:
        """
        Convertit un compte rendu structuré (dict JSON) en Markdown daté et lisible.
        """
        date_str = datetime.now().strftime("%d/%m/%Y à %H:%M")

        titre = report.get("titre", "Compte rendu").strip()
        resume = report.get("resume", "").strip()
        points_cles = report.get("points_cles", [])
        decisions_actions = report.get("decisions_actions", [])

        lignes = [
            f"# {titre}",
            "",
            f"*Généré le {date_str} par Scribe*",
            "",
            "---",
            "",
            "## 📝 Résumé",
            "",
            resume,
            "",
            "## 🔑 Points clés",
            "",
        ]

        if points_cles:
            lignes += [f"- {point}" for point in points_cles]
        else:
            lignes.append("*Aucun point clé identifié.*")

        lignes += ["", "## ✅ Décisions et actions", ""]

        if decisions_actions:
            lignes += [f"- {item}" for item in decisions_actions]
        else:
            lignes.append("*Aucune décision ou action explicite mentionnée dans cet enregistrement.*")

        lignes.append("")

        return "\n".join(lignes)


    def save_markdown_report(self, markdown_text: str, output_dir: str = "comptes_rendus") -> Path:
        """
        Sauvegarde un compte rendu Markdown dans un fichier daté.
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}_compte-rendu.md"
        filepath = output_path / filename
        filepath.write_text(markdown_text, encoding="utf-8")

        return filepath

if __name__ == "__main__":
    try:
        speech_to_text_agent = SpeechToTextAgent()
        summary_agent = SummaryAgent()
        exemple = speech_to_text_agent.get_text_from_audio("./audio_samples/test_audio_stt.mp4")
        compte_rendu = summary_agent.generate_report(exemple)
        md = summary_agent.format_as_markdown(compte_rendu)
        chemin = summary_agent.save_markdown_report(md)
    except (FileNotFoundError, RuntimeError) as e:
        print(e)