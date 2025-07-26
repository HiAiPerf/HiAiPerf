# DEMO.md: AI Public Speaking Coach Demo Guide

This document outlines a suggested structure for demonstrating the AI Public Speaking Coach application. It provides timestamps and descriptions to guide viewers through the key phases of the application's functionality, from user interaction to the underlying AI processes.

**[My PUBLIC DEMO VIDEO YouTube LINK](https://www.youtube.com/watch?v=wHSbIJ175sw&ab_channel=HiAiPerf)**

## Demo Walkthrough

Here's a breakdown of the demo video, highlighting important segments:

* **00:00 – 00:30 - Intro & Setup**

    * Briefly introduce the AI Public Speaking Coach and its purpose.

    * Show the main Gradio UI.

    * Explain the prerequisites (Docker, Google Cloud setup) and the steps taken to get the application running (e.g., `docker build`, `docker run`).

* **00:30 – 01:30 - User Input → Planning**

    * Demonstrate the user uploading or recording a video.

    * Explain how this action triggers the LangGraph agent.

    * Briefly describe the agent's fixed, sequential planning style and how it prepares to execute the workflow (e.g., "The agent's 'planner' decides the fixed steps: extract audio, transcribe, get feedback, synthesize audio.").

    * Show the loading indicator appearing after the "Get Coaching Feedback" button is clicked.

* **01:30 – 02:30 - Tool Calls & Memory**

    * Discuss the "behind-the-scenes" process, referring to the `agent_nodes.py` functions as "tool calls."

    * Highlight the key tool integrations:

        * **FFmpeg:** For audio extraction.

        * **Google Cloud Speech-to-Text API:** For transcription.

        * **Google Gemini:** For generating coaching feedback.

        * **Google Cloud Text-to-Speech API:** For synthesizing audio feedback.

        * **Google Cloud Storage:** For temporary file handling.

    * Explain how the `PublicSpeakingState` acts as the agent's memory, passing data (video URI, audio URI, transcript, feedback text) between these tool calls. You can refer to the console logs (from `docker logs`) to show these steps occurring.

* **02:30 – 03:30 - Final Output & Edge Case Handling**

    * Show the final textual feedback displayed in the UI.

    * Play the synthesized audio feedback.

    * Briefly discuss how the UI handles potential errors (e.g., if a video isn't uploaded, or if an API call fails, referring to the warning/error messages in the UI or console).

    * Conclude with a summary of the value proposition of the AI Public Speaking Coach.

This structure provides a clear narrative for your demo, guiding the viewer through both the user experience and the underlying technical processes. Remember to replace the placeholder video link with your actual demo video!