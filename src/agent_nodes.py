# agent_nodes.py
import os
import uuid
from typing import TypedDict, Optional
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import re # Import regular expression module

from utils import download_from_gcs, upload_to_gcs, extract_audio_from_video, GCS_BUCKET_NAME

# --- Configuration ---
# GCP_PROJECT_ID is still defined here for reference, but not directly passed to ChatGoogleGenerativeAI
GCP_PROJECT_ID = "dogwood-site-467123-v3" # <<< Ensure this is your correct project ID
GEMINI_MODEL_NAME = "gemini-1.5-flash" # Use 'gemini-1.5-pro' for higher quality, 'gemini-1.5-flash' for speed/cost

# TEMPORARY API KEY FOR LOCAL TESTING
# IMPORTANT: GENERATE THIS API KEY IN GOOGLE CLOUD CONSOLE (APIs & Services -> Credentials -> Create Credentials -> API Key)
# AND REPLACE "YOUR_GENERATED_GEMINI_API_KEY_HERE" WITH YOUR ACTUAL KEY.
# DO NOT COMMIT THIS KEY TO VERSION CONTROL! THIS IS FOR LOCAL DEVELOPMENT ONLY.
# For production, rely on Application Default Credentials or Service Accounts.
GOOGLE_API_KEY = "YOUR_GENERATED_GEMINI_API_KEY_HERE" # <<< PASTE YOUR API KEY HERE


# Initialize Google Cloud API clients
# These clients will now use GOOGLE_APPLICATION_CREDENTIALS for authentication in Docker
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

# Initialize LangChain's wrapper for Gemini API
# FIX: Removed the 'project_id' argument from ChatGoogleGenerativeAI initialization.
# When GOOGLE_APPLICATION_CREDENTIALS is set, the project is inferred from the service account key.
gemini_llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL_NAME,
    temperature=0.7, # Controls randomness: 0.0 (deterministic) to 1.0 (creative)
    max_output_tokens=1024, # Limit output length for feedback
    google_api_key=GOOGLE_API_KEY # Explicitly pass the API key here
)

# --- LangGraph State Definition ---
class PublicSpeakingState(TypedDict):
    video_gcs_uri: str # GCS URI of the original uploaded video
    extracted_audio_gcs_uri: Optional[str] # GCS URI of the audio extracted from video
    transcript: Optional[str] # Text transcript of the speech
    feedback_text: Optional[str] # AI-generated textual feedback
    feedback_audio_gcs_uri: Optional[str] # GCS URI of the synthesized audio feedback

# --- LangGraph Node Functions ---

def node_extract_audio(state: PublicSpeakingState) -> PublicSpeakingState:
    """
    LangGraph Node: Extracts audio from the video stored in GCS,
    saves it locally, then uploads the extracted audio back to GCS.
    """
    video_uri = state['video_gcs_uri']
    unique_id = uuid.uuid4().hex
    local_video_path = f"/tmp/{unique_id}_input_video.mp4"
    local_audio_path = f"/tmp/{unique_id}_extracted_audio.wav"

    print(f"Node: Extracting audio from {video_uri}...")
    try:
        download_from_gcs(video_uri, local_video_path)
        extracted_audio_path = extract_audio_from_video(local_video_path, local_audio_path)

        audio_gcs_uri = upload_to_gcs(extracted_audio_path, f"extracted_audio/{unique_id}.wav")

        os.remove(local_video_path)
        os.remove(local_audio_path)

        return {**state, "extracted_audio_gcs_uri": audio_gcs_uri}
    except Exception as e:
        print(f"Error in node_extract_audio: {e}")
        raise

def node_transcribe_audio(state: PublicSpeakingState) -> PublicSpeakingState:
    """
    LangGraph Node: Transcribes audio from GCS using Google Cloud Speech-to-Text API.
    """
    audio_gcs_uri = state.get('extracted_audio_gcs_uri')
    if not audio_gcs_uri:
        raise ValueError("No extracted audio URI found in state for transcription.")

    audio = speech.RecognitionAudio(uri=audio_gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_automatic_punctuation=True,
        model="video",
        profanity_filter=True,
    )

    print(f"Node: Transcribing audio from {audio_gcs_uri} using Speech-to-Text...")
    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=300)

    transcript_parts = []
    for result in response.results:
        transcript_parts.append(result.alternatives[0].transcript)

    full_transcript = " ".join(transcript_parts)
    print(f"Transcription complete. Length: {len(full_transcript)} characters.")

    return {**state, "transcript": full_transcript}

def node_coach_feedback(state: PublicSpeakingState) -> PublicSpeakingState:
    """
    LangGraph Node: Uses Google Gemini (via LangChain) to generate public speaking feedback.
    """
    transcript = state.get('transcript')
    if not transcript:
        raise ValueError("No transcript available for coaching feedback generation.")

    prompt = f"""
    You are an expert public speaking coach. Your goal is to provide constructive, actionable, and encouraging feedback on the following public speaking transcript.
    The feedback should be suitable for audio delivery, so keep sentences clear and concise.

    Focus on these three main sections:
    1.  **Strengths:** Identify 2-3 specific positive aspects of the speaker's delivery based on the transcript. Examples: "Your opening was engaging," "You used clear and concise language," "Your points flowed logically."
    2.  **Areas for Improvement:** Identify 2-3 specific, actionable suggestions for improvement. Examples: "Consider reducing filler words like 'um' or 'uh'," "Try varying your vocal pace to emphasize key points," "Ensure your conclusion clearly summarizes your main message."
    3.  **Overall Encouragement:** End with a brief, positive, and motivating statement.

    The transcript of the speech is enclosed in triple backticks:
    ```
    {transcript}
    ```
    Please provide your feedback in a natural, conversational, and supportive tone.
    """
    print("Node: Generating coaching feedback with Gemini...")
    messages = [HumanMessage(content=prompt)]
    response = gemini_llm.invoke(messages)
    feedback_text = response.content
    print("Gemini feedback text generated.")

    return {**state, "feedback_text": feedback_text}

def node_synthesize_audio_feedback(state: PublicSpeakingState) -> PublicSpeakingState:
    """
    LangGraph Node: Converts the textual feedback into natural-sounding audio
    using Google Cloud Text-to-Speech API and uploads it to GCS.
    Removes markdown bold formatting (**) before synthesis.
    """
    feedback_text = state.get('feedback_text')
    if not feedback_text:
        raise ValueError("No feedback text found in state for audio synthesis.")

    # FIX: Remove markdown bold (**) before sending to Text-to-Speech
    # This ensures the asterisks are not read aloud.
    clean_feedback_text = re.sub(r'\*\*', '', feedback_text)

    synthesis_input = texttospeech.SynthesisInput(text=clean_feedback_text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-F",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.05,
        pitch=0.0,
    )

    print("Node: Synthesizing audio feedback using Text-to-Speech...")
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    unique_id = uuid.uuid4().hex
    local_feedback_audio_path = f"/tmp/{unique_id}_feedback.mp3"
    with open(local_feedback_audio_path, "wb") as out:
        out.write(response.audio_content)
    print(f"Audio content saved locally to '{local_feedback_audio_path}'")

    feedback_audio_gcs_uri = upload_to_gcs(local_feedback_audio_path, f"feedback_audio/{unique_id}.mp3")
    os.remove(local_feedback_audio_path)

    return {**state, "feedback_audio_gcs_uri": feedback_audio_gcs_uri}

# Example usage (for testing individual nodes, not typical LangGraph flow)
if __name__ == "__main__":
    print("--- Testing agent_nodes.py functions (individual calls) ---")
    # This requires you to have a video file uploaded to GCS and its URI.
    # For a full test, it's better to run `app_gradio.py` or `agent_graph.py`.

    # Dummy state for testing
    dummy_video_uri = f"gs://{GCS_BUCKET_NAME}/test_videos/sample_speech.mp4" # <<< Ensure this video exists in your bucket!

    # IMPORTANT: ONLY FOR TESTING INDIVIDUAL NODES.
    # For a full run, the GCS_BUCKET_NAME in utils.py should be set.
    # This is a placeholder for local testing if you don't want to use a real video.
    # If you are running app_gradio.py, this section is not directly used.
    if "your-public-speaking-coach-bucket" in GCS_BUCKET_NAME:
        print("Please update GCS_BUCKET_NAME in utils.py with your actual bucket name for full testing.")
        print("Skipping individual node tests as GCS_BUCKET_NAME is a placeholder.")
    else:
        initial_dummy_state = PublicSpeakingState(video_gcs_uri=dummy_video_uri)
        try:
            # Test node_extract_audio
            print("\nTesting node_extract_audio...")
            state_after_extract = node_extract_audio(initial_dummy_state.copy())
            print(f"Extracted audio URI: {state_after_extract['extracted_audio_gcs_uri']}")

            # Test node_transcribe_audio
            print("\nTesting node_transcribe_audio...")
            state_after_transcribe = node_transcribe_audio(state_after_extract.copy())
            print(f"Transcript: {state_after_transcribe['transcript'][:200]}...")

            # Test node_coach_feedback
            print("\nTesting node_coach_feedback...")
            state_after_coach = node_coach_feedback(state_after_transcribe.copy())
            print(f"Feedback Text: {state_after_coach['feedback_text'][:200]}...")

            # Test node_synthesize_audio_feedback
            print("\nTesting node_synthesize_audio_feedback...")
            state_after_synthesize = node_synthesize_audio_feedback(state_after_coach.copy())
            print(f"Feedback Audio URI: {state_after_synthesize['feedback_audio_gcs_uri']}")

            # Clean up GCS objects created during this test
            # from utils import delete_gcs_blob
            # delete_gcs_blob(state_after_extract['extracted_audio_gcs_uri'])
            # delete_gcs_blob(state_after_synthesize['feedback_audio_gcs_uri'])

        except Exception as e:
            print(f"\nError during individual node testing: {e}")
            print("Please ensure you have valid Google Cloud credentials, project ID, bucket, and a sample video in your GCS bucket.")
            print("Also, ensure FFmpeg is installed if testing locally.")

    print("\n--- agent_nodes.py tests finished ---")
