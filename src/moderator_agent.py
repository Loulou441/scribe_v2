from config import LLM_MODEL
from agent import Agent
from speech_to_text_agent import SpeechToTextAgent
import json


class ModeratorAgent(Agent):
	def __init__(self):
		super().__init__()


	def moderate_transcript(self, transcription_text):

		chat_completion = self.client.chat.completions.create(
			messages=[
				{
					"role": "system",
					"content": Agent.read_file("./src/prompts_LLM/moderator_prompt_system.txt")
				},
				{
					"role": "user",
					"content": transcription_text,
				}
			],
			model=LLM_MODEL,
			response_format={"type": "json_object"},
			temperature=0,
		)

		moderation = json.loads(chat_completion.choices[0].message.content)

		return moderation


if __name__ == "__main__":
	moderator_agent = ModeratorAgent()
	speech_to_text_agent = SpeechToTextAgent()
	
	transcription_text = speech_to_text_agent.get_text_from_audio("./audio_samples/test_audio_stt.mp4")

	moderation = moderator_agent.moderate_transcript(transcription_text)

	print(moderation)

	prompt_injection_text = speech_to_text_agent.get_text_from_audio("./audio_samples/test_injection_text.mp4")

	injection_moderation = moderator_agent.moderate_transcript(prompt_injection_text)

	print(injection_moderation)