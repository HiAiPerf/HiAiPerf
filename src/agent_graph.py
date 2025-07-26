# agent_graph.py
# LangGraph Definition)

#This file defines the LangGraph workflow using the nodes from agent_nodes.py.

from langgraph.graph import StateGraph, END
from agent_nodes import (
    PublicSpeakingState,
    node_extract_audio,
    node_transcribe_audio,
    node_coach_feedback,
    node_synthesize_audio_feedback
)

def build_public_speaking_coach_graph():
    """Builds and compiles the LangGraph workflow for the public speaking coach."""
    workflow = StateGraph(PublicSpeakingState)

    # Add nodes to the graph
    workflow.add_node("extract_audio", node_extract_audio)
    workflow.add_node("transcribe_audio", node_transcribe_audio)
    workflow.add_node("coach_feedback", node_coach_feedback)
    workflow.add_node("synthesize_audio_feedback", node_synthesize_audio_feedback)

    # Define the execution flow (edges)
    workflow.set_entry_point("extract_audio")
    workflow.add_edge("extract_audio", "transcribe_audio")
    workflow.add_edge("transcribe_audio", "coach_feedback")
    workflow.add_edge("coach_feedback", "synthesize_audio_feedback")
    workflow.add_edge("synthesize_audio_feedback", END)

    # Compile the graph
    app = workflow.compile()
    return app

if __name__ == "__main__":
    # This block allows you to test the graph standalone (e.g., with a dummy GCS URI)
    print("Building and testing the LangGraph workflow...")
    graph = build_public_speaking_coach_graph()

    # You would typically pass a real GCS URI here for a test
    # For a quick test, let's simulate the input video URI
    initial_state = PublicSpeakingState(video_gcs_uri="gs://your-public-speaking-coach-bucket/test_videos/sample_speech.mp4")

    # To run this, you need a sample_speech.mp4 in your GCS bucket
    # and ensure `ffmpeg` is installed locally if running outside of Cloud Run.
    # Also ensure your GCP_PROJECT_ID and GCS_BUCKET_NAME are set in agent_nodes.py and utils.py

    # The graph.stream() method yields state updates as it progresses
    print("Running graph...")
    try:
        final_state = None
        for s in graph.stream(initial_state):
            print(s) # Print intermediate states
            final_state = s

        print("\n--- Final State ---")
        print(f"Transcript: {final_state['coach_feedback']['transcript']}")
        print(f"Feedback Text: {final_state['coach_feedback']['feedback_text']}")
        print(f"Feedback Audio URI: {final_state['synthesize_audio_feedback']['feedback_audio_gcs_uri']}")
        print("Graph execution complete.")

        # Optional: Delete the temporary GCS files after testing
        # from utils import delete_gcs_blob
        # delete_gcs_blob(final_state['extract_audio']['extracted_audio_gcs_uri'])
        # delete_gcs_blob(final_state['synthesize_audio_feedback']['feedback_audio_gcs_uri'])

    except Exception as e:
        print(f"An error occurred during graph execution: {e}")
        print("Please ensure you have valid Google Cloud credentials, project ID, bucket name, and necessary services enabled.")
        print("Also, check if FFmpeg is installed and accessible if you're testing locally.")
