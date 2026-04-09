import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


DEFAULT_PROMPT = """A close up of two people staring at a cryptic drawing on a wall, torchlight flickering.
A man murmurs, 'This must be it. That's the secret code.' The woman looks at him and whispering excitedly, 'What did you find?'"""


def build_client() -> genai.Client:
    load_dotenv()

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        print("Using Gemini API key authentication.")
        return genai.Client(api_key=api_key)

    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION")
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
    if use_vertex or (project and location):
        if not project or not location:
            raise SystemExit(
                "Vertex AI mode requires both GOOGLE_CLOUD_PROJECT and "
                "GOOGLE_CLOUD_LOCATION."
            )
        print(f"Using Vertex AI authentication. project={project}, location={location}")
        return genai.Client(vertexai=True, project=project, location=location)

    raise SystemExit(
        "Missing Google credentials.\n"
        "Option 1: set GOOGLE_API_KEY in .env for Gemini API.\n"
        "Option 2: set GOOGLE_GENAI_USE_VERTEXAI=true, GOOGLE_CLOUD_PROJECT, "
        "and GOOGLE_CLOUD_LOCATION for Vertex AI."
    )


def build_config() -> types.GenerateVideosConfig:
    duration_seconds = int(os.getenv("VEO_DURATION_SECONDS", "8"))
    if duration_seconds not in {4, 6, 8}:
        raise SystemExit("VEO_DURATION_SECONDS must be one of: 4, 6, 8")

    negative_prompt = os.getenv("VEO_NEGATIVE_PROMPT")
    config_kwargs = {
        "number_of_videos": 1,
        "duration_seconds": duration_seconds,
    }
    if negative_prompt:
        config_kwargs["negative_prompt"] = negative_prompt

    return types.GenerateVideosConfig(**config_kwargs)


def main() -> None:
    client = build_client()
    model = os.getenv("VEO_MODEL", "veo-3.1-generate-preview")
    prompt = os.getenv("VEO_PROMPT", DEFAULT_PROMPT)
    output_name = os.getenv("VEO_OUTPUT", "dialogue_example.mp4")
    output_path = Path(output_name).expanduser().resolve()

    print(f"Generating video with model={model}")
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=build_config(),
    )

    while not operation.done:
        print("Waiting for video generation to complete...")
        time.sleep(10)
        operation = client.operations.get(operation)

    if not operation.response or not operation.response.generated_videos:
        raise SystemExit(f"Video generation failed or returned empty response: {operation}")

    generated_video = operation.response.generated_videos[0]
    client.files.download(file=generated_video.video)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    generated_video.video.save(output_path)
    print(f"Generated video saved to {output_path}")


if __name__ == "__main__":
    main()
