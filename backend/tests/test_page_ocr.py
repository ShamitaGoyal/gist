
from pathlib import Path
from rapidocr import RapidOCR

# Input image generated in our previous step
image_path = "data/evaluation_results/page4.png"

# Where OCR results will be saved
output_path = Path("data/evaluation_results/page4_ocr.txt")

# Initialize the OCR engine
ocr = RapidOCR()

# Extract text from the image
result = ocr(image_path)

# RapidOCR returns a RapidOCROutput object, not a list.
# The recognized strings are in result.txts.
recognized_lines = []

for text in result.txts or []:
    recognized_lines.append(text)

# Save extracted text
output_path.write_text("\n".join(recognized_lines), encoding="utf-8")

print("OCR completed!")
print(f"Extracted {len(recognized_lines)} text regions.")
print(f"Results saved to: {output_path}")

print("\n--- OCR PREVIEW ---\n")
print("\n".join(recognized_lines[:30]))
