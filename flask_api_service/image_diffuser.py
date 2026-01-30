import base64
import io

import torch
from diffusers import FluxPipeline
# QwenImageEditPipeline, DiffusionPipeline
import os

image_pipe = FluxPipeline.from_pretrained("black-forest-labs/FLUX.1-schnell",
                                    torch_dtype=torch.bfloat16)
image_pipe.enable_model_cpu_offload()

def generate_image_base64(query: str):

    image = image_pipe(
        prompt=query,
        # num_inference_steps=steps,
        guidance_scale=0.0,
        width=480,
        height=640
    ).images[0]

    # Convert PIL → PNG → Base64
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    b64_str = base64.b64encode(buf.read()).decode("utf-8")
    return b64_str


# IMG_MODEL_ID = os.environ.get("MODEL_ID", "Qwen/Qwen-Image-Edit")
# IMG_DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
# IMG_DTYPE = os.environ.get("DTYPE", "bfloat16")
#
# image_edit_pipe = QwenImageEditPipeline.from_pretrained(
#     "Qwen/Qwen-Image-Edit",
#     torch_dtype=torch.bfloat16,
#     # NO variant, NO quant_config
# )
#
# # Optional memory savers
# image_edit_pipe.enable_model_cpu_offload()
# image_edit_pipe.enable_attention_slicing(1)
