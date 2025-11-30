import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from datasets import load_dataset, DatasetDict
dataset_matrix = load_dataset('path/to/matrix/dataset')
dataset_isis = load_dataset('path/to/isis/dataset')

dataset = DatasetDict({
    'train': dataset_matrix['train'].concatenate(dataset_isis['train']),
    'test': dataset_matrix['test'].concatenate(dataset_isis['test']),
})

model_name = "bert-base-uncased"
model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)


def tokenize_function(examples):
    return tokenizer(examples['text'], padding="max_length", truncation=True)


tokenized_datasets = dataset.map(tokenize_function, batched=True)

training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
)

trainer.train()

trainer.save_model("fine-tuned-model")
