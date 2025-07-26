# utils.py
import os
import uuid
from google.cloud import storage
from pydub import AudioSegment
from pydub.utils import mediainfo

# --- Configuration ---
# IMPORTANT: Replace with your actual GCS bucket name
# This bucket will store uploaded videos, extracted audio, and generated feedback audio.
GCS_BUCKET_NAME = "your-public-speaking-coach-bucket" # <<< IMPORTANT: Replace with your GCS bucket name

# Initialize Google Cloud Storage client
# This client will automatically use Application Default Credentials (ADC)
# if you've run `gcloud auth application-default login` locally,
# or a service account if deployed on GCP services like Cloud Run.
storage_client = storage.Client()

def upload_to_gcs(local_file_path: str, destination_blob_name: str) -> str:
    """
    Uploads a local file to a Google Cloud Storage bucket.

    Args:
        local_file_path (str): The path to the file on your local machine.
        destination_blob_name (str): The desired path/name for the file in GCS.

    Returns:
        str: The GCS URI (gs://bucket-name/blob-name) of the uploaded file.
    """
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file_path)
    print(f"File '{local_file_path}' uploaded to 'gs://{GCS_BUCKET_NAME}/{destination_blob_name}'")
    return f"gs://{GCS_BUCKET_NAME}/{destination_blob_name}"

def download_from_gcs(gcs_uri: str, local_file_path: str):
    """
    Downloads a file from a Google Cloud Storage bucket to a local path.

    Args:
        gcs_uri (str): The GCS URI (gs://bucket-name/blob-name) of the file to download.
        local_file_path (str): The local path where the file should be saved.
    """
    # Parse bucket name and blob name from GCS URI
    path_parts = gcs_uri.replace("gs://", "").split("/", 1)
    bucket_name = path_parts[0]
    blob_name = path_parts[1] if len(path_parts) > 1 else "" # Handle root-level blobs

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.download_to_filename(local_file_path)
    print(f"File '{gcs_uri}' downloaded to '{local_file_path}'")

def extract_audio_from_video(video_path: str, output_audio_path: str) -> str:
    """
    Extracts audio from a video file, resamples it to 16kHz, and saves it as a WAV file.
    Requires `ffmpeg` to be installed and accessible in your system's PATH.
    """
    try:
        audio = AudioSegment.from_file(video_path)
        
        # --- FIX: Explicitly resample audio to 16kHz for Speech-to-Text compatibility ---
        if audio.frame_rate != 16000:
            print(f"Resampling audio from {audio.frame_rate}Hz to 16000Hz for Speech-to-Text compatibility...")
            audio = audio.set_frame_rate(16000)
        # --- END FIX ---

        audio.export(output_audio_path, format="wav")
        print(f"Audio extracted and resampled from '{video_path}' to '{output_audio_path}'")
        return output_audio_path
    except Exception as e:
        print(f"Error extracting or resampling audio from video '{video_path}': {e}")
        print("Please ensure FFmpeg is installed and in your system's PATH.")
        raise

def delete_gcs_blob(gcs_uri: str):
    """
    Deletes a blob from a Google Cloud Storage bucket.
    Useful for cleaning up temporary files.

    Args:
        gcs_uri (str): The GCS URI (gs://bucket-name/blob-name) of the blob to delete.
    """
    path_parts = gcs_uri.replace("gs://", "").split("/", 1)
    bucket_name = path_parts[0]
    blob_name = path_parts[1] if len(path_parts) > 1 else ""

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    try:
        blob.delete()
        print(f"Deleted GCS blob: {gcs_uri}")
    except Exception as e:
        print(f"Could not delete GCS blob '{gcs_uri}': {e}")

# Example usage (for testing this file independently)
if __name__ == "__main__":
    print("--- Testing utils.py functions ---")

    # --- Test GCS Upload/Download/Delete ---
    test_local_file = "test_upload_file.txt"
    with open(test_local_file, "w") as f:
        f.write("This is a test file for GCS operations.")

    test_gcs_blob_name = f"test_uploads/{uuid.uuid4().hex}_test_file.txt"
    uploaded_gcs_uri = upload_to_gcs(test_local_file, test_gcs_blob_name)

    downloaded_local_file = "test_download_file.txt"
    download_from_gcs(uploaded_gcs_uri, downloaded_local_file)

    with open(downloaded_local_file, "r") as f:
        content = f.read()
        print(f"Downloaded content: '{content}'")

    delete_gcs_blob(uploaded_gcs_uri)
    os.remove(test_local_file)
    os.remove(downloaded_local_file)
    print("GCS operations test complete.")

    # --- Test Audio Extraction (requires a sample video file) ---
    print("\n--- Testing Audio Extraction ---")
    # IMPORTANT: For this test, you need a short MP4 video file
    # in the same directory as this script, e.g., 'sample_video.mp4'.
    # You can download a short public domain video or create one.
    sample_video_path = "sample_video.mp4" # <<< Replace with your actual sample video path
    extracted_audio_output_path = "extracted_audio_test.wav"

    if os.path.exists(sample_video_path):
        try:
            extracted_path = extract_audio_from_video(sample_video_path, extracted_audio_output_path)
            print(f"Successfully extracted audio to: {extracted_path}")
            os.remove(extracted_audio_output_path) # Clean up
        except Exception as e:
            print(f"Skipping audio extraction test due to error: {e}")
    else:
        print(f"Skipping audio extraction test: '{sample_video_path}' not found. Please create one to test.")

    print("--- utils.py tests finished ---")
