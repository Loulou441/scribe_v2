"""
Module de transcription audio via l'API Speech-to-Text de Groq.
"""

from pathlib import Path
from groq import APIError, APIConnectionError, RateLimitError
from config import STT_MODEL
from agent import Agent

class SpeechToTextAgent(Agent):
    def __init__(self):
        super().__init__()

    # Open the audio file
    def get_text_from_audio(self, audio_file_path):
        path = Path(audio_file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Fichier audio introuvable : {audio_file_path}") 
        try:
            with open(audio_file_path, "rb") as file:
                # Create a transcription of the audio file
                transcription = self.client.audio.transcriptions.create(
                    file=file, # Required audio file
                    model=STT_MODEL, # Required model to use for transcription
                    response_format="verbose_json",  # Optional
                    timestamp_granularities = ["word", "segment"], # Optional (must set response_format to "json" to use and can specify "word", "segment" (default), or both)
                    language="fr",  # Optional
                    temperature=0.0  # Optional
                )
        except (APIError, APIConnectionError, RateLimitError) as e:
            raise RuntimeError(f"Échec de la transcription via l'API Groq : {e}") from e

        return transcription.text

if __name__ == "__main__":
    try:
        speech_to_text_agent = SpeechToTextAgent()
        audio_file_path = "./audio_samples/test_audio_stt.mp4"
        texte = speech_to_text_agent.get_text_from_audio(audio_file_path)
        print("Transcription :", texte)
    except FileNotFoundError as e:
        print(e)
    except RuntimeError as e:
        print(e)
