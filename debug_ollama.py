"""Debug script to check Ollama API response."""
import ollama
import json

client = ollama.Client()

print("Testing Ollama list() response:")
print("=" * 50)

response = client.list()

print(f"Response type: {type(response)}")
print(f"\nResponse content:")
print(json.dumps(response, indent=2, default=str))

print("\n" + "=" * 50)
print("Extracting model names:")

if hasattr(response, "models"):
    models = response.models
    print(f"Found {len(models)} models:")
    for model in models:
        print(f"  - Model type: {type(model)}")
        print(f"  - Model attributes: {dir(model)}")
        if hasattr(model, "model"):
            print(f"    Name: {model.model}")
        elif hasattr(model, "name"):
            print(f"    Name: {model.name}")
        print()
