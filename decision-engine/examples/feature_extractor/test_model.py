import torch

from decision_engine.feature_extractor.classifier.model import RequestClassifier

model = RequestClassifier()
model.eval()

input_ids = torch.randint(0, 100, (2, 128))
attention_mask = torch.ones((2, 128), dtype=torch.long)

with torch.no_grad():
    result = model(
        input_ids=input_ids,
        attention_mask=attention_mask,
    )

for name, logits in result["logits"].items():
    print(name, logits.shape)
