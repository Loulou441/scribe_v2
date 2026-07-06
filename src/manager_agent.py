from speech_to_text_agent import SpeechToTextAgent 
from summary_agent import SummaryAgent
from moderator_agent import ModeratorAgent
from qa_agent import QAAgent
import argparse
import sys

class ManagerAgent:
	def __init__(self):
		self.speech_to_text_agent_object = SpeechToTextAgent()
		self.summary_agent_object = SummaryAgent()
		self.moderator_agent_object = ModeratorAgent()
		self.last_transcription_text = None


	def summaries_audio(self, audio_file_path):
		transcription_text = self.speech_to_text_agent_object.get_text_from_audio(audio_file_path)
		self.last_transcription_text = transcription_text
		moderation_dict = self.moderator_agent_object.moderate_transcript(transcription_text)

		if moderation_dict["prompt_injection"]:
			raise(Exception(moderation_dict["raison"]))
			return None
		else :
			text_summary_dict = self.summary_agent_object.generate_report(transcription_text)
			md = self.summary_agent_object.format_as_markdown(text_summary_dict)
			chemin = self.summary_agent_object.save_markdown_report(md)
			print(f"Compte rendu sauvegardé dans le fichier : {chemin}")
			return text_summary_dict 
		
	def interactive_qa(self, transcription_text, report):
		"""
		Lance une boucle interactive permettant de poser des questions sur le
		compte rendu (et la transcription associée), avec conservation de
		l'historique de conversation le temps de la session.
		"""
		qa_agent = QAAgent(transcription_text, report)

		print("\nMode interactif activé. Posez vos questions sur le compte rendu.")
		print("Tapez 'exit' ou 'quit' pour arrêter.\n")
 
		while True:
			try:
				question = input("> ").strip()
			except (EOFError, KeyboardInterrupt):
				print("\nFin du mode interactif.")
				break
 
			if not question:
				continue
 
			if question.lower() in ("exit", "quit"):
				print("Fin du mode interactif.")
				break
 
			moderation_dict = self.moderator_agent_object.moderate_transcript(question)
			if moderation_dict["prompt_injection"]:
				print(f"⚠️  Question rejetée : {moderation_dict['raison']}\n")
				continue
 
			try:
				answer = qa_agent.ask(question)
			except RuntimeError as e:
				print(e)
				continue
 
			print(answer)
			print()

	
def parse_args():
    parser = argparse.ArgumentParser(
        description="Transcrit un fichier audio puis génère un compte rendu structuré."
    )
    parser.add_argument(
        "audio_file_path",
        nargs="?",
        default="./audio_samples/test_audio_stt.mp4",
        help="Chemin vers le fichier audio à traiter (par défaut : ./audio_samples/test_audio_stt.mp4)",
    )

    parser.add_argument(
        "--chat", "-i",
        action="store_true",
        help="Lance un mode interactif après la génération du compte rendu, pour poser des questions dessus.",
    )

    return parser.parse_args()

if __name__ == "__main__":
	args = parse_args()
	manager_agent_object = ManagerAgent()
 
	try:
		text_summary_dict = manager_agent_object.summaries_audio(args.audio_file_path)
	except (FileNotFoundError, RuntimeError) as e:
		print(e)
		sys.exit(1)
 
	for key, value in text_summary_dict.items():
		print(f"{key}: {value}")
		print("---")

	if args.chat:
		manager_agent_object.interactive_qa(
		manager_agent_object.last_transcription_text,
		text_summary_dict,
	)
