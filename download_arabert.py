import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch

def download_arabert():
    # Define the model name and save path
    model_name = "aubmindlab/bert-base-arabertv2"
    save_path = Path("data/embeddings/arabert")
    
    print(f"Downloading AraBERT model from {model_name}...")
    
    try:
        # Download and save the tokenizer
        print("Downloading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(save_path)
        
        # Download and save the model
        print("Downloading model...")
        model = AutoModel.from_pretrained(model_name)
        model.save_pretrained(save_path)
        
        print(f"\nAraBERT model has been successfully downloaded and saved to: {save_path}")
        print("\nModel files downloaded:")
        for file in save_path.glob("*"):
            print(f"- {file.name}")
            
    except Exception as e:
        print(f"Error downloading AraBERT: {str(e)}")
        raise

if __name__ == "__main__":
    download_arabert() 