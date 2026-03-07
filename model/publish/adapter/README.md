---
library_name: peft
license: other
base_model: deepseek-ai/deepseek-coder-6.7b-instruct
tags:
- axolotl
- base_model:adapter:deepseek-ai/deepseek-coder-6.7b-instruct
- lora
- transformers
datasets:
- custom
pipeline_tag: text-generation
model-index:
- name: bridge-cli
  results: []
---

<!-- This model card has been generated automatically according to the information the Trainer had access to. You
should probably proofread and complete it, then remove this comment. -->

[<img src="https://raw.githubusercontent.com/axolotl-ai-cloud/axolotl/main/image/axolotl-badge-web.png" alt="Built with Axolotl" width="200" height="32"/>](https://github.com/axolotl-ai-cloud/axolotl)
<details><summary>See axolotl config</summary>

axolotl version: `0.15.0`
```yaml
# Bridge CLI - Spring Boot Fine-Tuning Configuration
# Optimized for RunPod with budget GPU (RTX 4090/A5000 24GB)
# Using QLoRA for memory efficiency

base_model: deepseek-ai/deepseek-coder-6.7b-instruct
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer
trust_remote_code: true

# QLoRA Configuration (enables training on 24GB GPU)
load_in_4bit: true
adapter: qlora
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target_linear: true
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

# Dataset Configuration
datasets:
  - path: /workspace/datasets/spring-boot-dataset.jsonl
    type: alpaca
  - path: /workspace/datasets/react-dataset.jsonl
    type: alpaca

dataset_prepared_path: /workspace/prepared_data
val_set_size: 0.05
output_dir: /workspace/outputs/bridge-cli

# Training Parameters
sequence_len: 2048
sample_packing: true
pad_to_sequence_len: true

micro_batch_size: 4
gradient_accumulation_steps: 4
num_epochs: 3
learning_rate: 0.0002
lr_scheduler: cosine
warmup_ratio: 0.03
optimizer: adamw_8bit

# Memory Optimization
gradient_checkpointing: true
flash_attention: false
bf16: auto
tf32: false

# Training Settings
train_on_inputs: false
group_by_length: false
logging_steps: 10
save_strategy: steps
save_steps: 100
eval_steps: 100

# Weights & Biases (optional - remove if not using)
# wandb_project: bridge-cli
# wandb_run_id: spring-boot-finetune

# Early stopping
early_stopping_patience: 3

# For debugging - set to true to test config
debug: false

# Special tokens
special_tokens:
  pad_token: "<|pad|>"

```

</details><br>

# Bridge CLI - Fine-tuned Code Generation Model

This model is a fine-tuned version of [deepseek-ai/deepseek-coder-6.7b-instruct](https://huggingface.co/deepseek-ai/deepseek-coder-6.7b-instruct) on custom Java/Spring Boot (2,307 examples) and React/TypeScript (4,041 examples) datasets in Alpaca instruction format.
It achieves the following results on the evaluation set:
- Loss: 0.4579
- Ppl: 1.5808
- Memory/max Active (gib): 6.45
- Memory/max Allocated (gib): 6.45
- Memory/device Reserved (gib): 10.47

## Model description

More information needed

## Intended uses & limitations

More information needed

## Training and evaluation data

More information needed

## Training procedure

### Training hyperparameters

The following hyperparameters were used during training:
- learning_rate: 0.0002
- train_batch_size: 4
- eval_batch_size: 4
- seed: 42
- gradient_accumulation_steps: 4
- total_train_batch_size: 16
- optimizer: Use OptimizerNames.ADAMW_8BIT with betas=(0.9,0.999) and epsilon=1e-08 and optimizer_args=No additional optimizer arguments
- lr_scheduler_type: cosine
- lr_scheduler_warmup_steps: 6
- training_steps: 222

### Training results

| Training Loss | Epoch  | Step | Validation Loss | Ppl     | Active (gib) | Allocated (gib) | Reserved (gib) |
|:-------------:|:------:|:----:|:---------------:|:-------:|:------------:|:---------------:|:--------------:|
| No log        | 0      | 0    | 3.3726          | 29.1542 | 6.36         | 6.36            | 12.58          |
| 0.4787        | 1.3356 | 100  | 0.5115          | 1.6679  | 6.45         | 6.45            | 10.47          |
| 0.4037        | 2.6711 | 200  | 0.4579          | 1.5808  | 6.45         | 6.45            | 10.47          |


### Framework versions

- PEFT 0.18.1
- Transformers 5.3.0
- Pytorch 2.10.0+cu128
- Datasets 4.5.0
- Tokenizers 0.22.2