"""Download just the pinned checkpoint before offline serving."""
from huggingface_hub import snapshot_download
from release import RELEASE

snapshot_download(RELEASE["model_repo"], revision=RELEASE["model_revision"],
                  allow_patterns=[RELEASE["checkpoint"] + "/*"])
