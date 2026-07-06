from speech_to_text_agent import SpeechToTextAgent 
from summary_agent import SummaryAgent
import argparse
import sys

class ManagerAgent:
	def __init__(self):
		self.speech_to_text_agent_object = SpeechToTextAgent()
		self.summary_agent_object = SummaryAgent()


	def summaries_audio(self, audio_file_path):
		transcription_text = self.speech_to_text_agent_object.get_text_from_audio(audio_file_path)
		return self.summary_agent_object.generate_report(transcription_text)
	
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
