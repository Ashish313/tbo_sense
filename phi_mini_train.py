from datasets import load_dataset

# You can create a dataset from JSON or JSONL
dataset = load_dataset("json", data_files="tool_call_dataset.jsonl", split="train")

# Format for SFT
def format_example(example):
    return {
        "text": example["input"]
    }

dataset = dataset.map(format_example)

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
import torch

# model_id = "microsoft/phi-3-mini-128k-instruct"
model_id = "meta-llama/Meta-Llama-3-8B-Instruct"

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    trust_remote_code=True
).to(device)

# Enable LoRA
peft_config = LoraConfig(
    r=8,
    lora_alpha=32,
    lora_dropout=0.1,
    bias="none",
    task_type=TaskType.CAUSAL_LM,
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj"
    ]
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()

from trl import SFTTrainer, SFTConfig
from transformers import TrainingArguments

sft_config = SFTConfig(
    output_dir="./llama3-tools",
    max_seq_length=8192,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=100,
    learning_rate=5e-5,
    logging_steps=10,
    save_steps=100,
    optim="adamw_torch",
    bf16=False,
    fp16=False,
    packing=False,
    report_to=None
)

trainer = SFTTrainer(
    model=model,
    train_dataset=dataset,
    args=sft_config,
    # formatting_func=formatting_func
)

trainer.train()
trainer.save_model("./llama3-tools")

# model.save_pretrained("./llama3-tools-vllm")
# tokenizer.save_pretrained("./llama3-tools-vllm")