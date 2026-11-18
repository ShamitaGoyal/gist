
from rapidocr import RapidOCR

image_path = "data/evaluation_results/page4.png"

ocr = RapidOCR()
result = ocr(image_path)

print("\nOCR RESULT STRUCTURE:\n")
print(result)

print("\nNUMBER OF DETECTED TEXT REGIONS:")
print(len(result))
