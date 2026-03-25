"""
test_accuracy.py
Run: python test_accuracy.py
Output: accuracy score + list of photos AI got wrong
"""

import pandas as pd
import os
from utils.llm_utils import describe_photo

PHOTOS_DIR = "assets/test_photos"
LABELS_CSV = "assets/test_photos_labels.csv"

def run_accuracy_test():
    df = pd.read_csv(LABELS_CSV, index_col=0)  # photo_id as index
    results = []

    print(f"\n🔍 Testing {len(df)} photos...\n")

    for _, row in df.iterrows():
        filename = str(row["filename"]).strip()
        filepath = os.path.join(PHOTOS_DIR, filename)

        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename} — skipping")
            continue

        with open(filepath, "rb") as f:
            image_bytes = f.read()

        ext = filename.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"

        try:
            result = describe_photo(image_bytes, mime_type=mime)
            ai_flag = result.get("hazard_flag", False)
            manual_flag = str(row["manual_hazard_label"]).strip().lower() == "true"
            correct = ai_flag == manual_flag

            results.append({
                "filename": filename,
                "manual": manual_flag,
                "ai": ai_flag,
                "correct": correct,
                "ai_description": result.get("description", "")[:80]
            })

            status = "✅" if correct else "❌"
            print(f"{status} {filename[:40]:<40} manual={manual_flag} | ai={ai_flag}")

        except Exception as e:
            print(f"❌ Error on {filename}: {e}")

    if results:
        correct_count = sum(1 for r in results if r["correct"])
        total = len(results)
        accuracy = (correct_count / total) * 100

        print(f"\n{'='*50}")
        print(f"📊 ACCURACY RESULTS")
        print(f"{'='*50}")
        print(f"Correct : {correct_count}/{total}")
        print(f"Accuracy: {accuracy:.1f}%")
        print(f"Target  : 70%")
        print(f"Result  : {'✅ PASS' if accuracy >= 70 else '❌ BELOW TARGET'}")

        wrong = [r for r in results if not r["correct"]]
        if wrong:
            print(f"\n❌ Photos AI got wrong ({len(wrong)}):")
            for r in wrong:
                print(f"  - {r['filename']} (manual={r['manual']}, ai={r['ai']})")

        out = pd.DataFrame(results)
        out.to_csv("assets/accuracy_results.csv", index=False)
        print(f"\n💾 Results saved to assets/accuracy_results.csv")

if __name__ == "__main__":
    run_accuracy_test()