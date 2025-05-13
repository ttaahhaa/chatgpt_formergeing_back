from app.core.document_loader import DocumentLoader

file_path = r"C:\Users\Dell\Documents\production_specs_ai_plateform.pdf"

loader = DocumentLoader()
result = loader.load(file_path)

print("=== Document Loader Result ===")
for key, value in result.items():
    if key == "content":
        print(f"{key}: {str(value)[:500]}...")  # Print only the first 500 chars
    else:
        print(f"{key}: {value}") 