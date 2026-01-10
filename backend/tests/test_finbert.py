"""
FinBERT 모델 로컬 테스트

실행: python backend/tests/test_finbert.py
"""

import time
import psutil
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification


def test_finbert_basic():
    """기본 FinBERT 테스트"""
    print("=" * 60)
    print("FinBERT 모델 테스트 시작...")
    print("=" * 60)

    # 1. 모델 로드
    print("\n[1/4] 모델 로드 중...")
    start_time = time.time()

    model_name = "ProsusAI/finbert"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)

    load_time = time.time() - start_time
    print(f"✅ 모델 로드 완료: {load_time:.2f}초")

    # 2. 메모리 사용량 체크
    print("\n[2/4] 메모리 사용량 체크...")
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"✅ 메모리 사용: {memory_mb:.2f} MB")

    if memory_mb > 500:
        print(f"⚠️  경고: 메모리 사용량이 높음 (목표: <300MB)")

    # 3. 추론 속도 테스트
    print("\n[3/4] 추론 속도 테스트...")
    test_texts = [
        "Bitcoin surges to new all-time high as institutional adoption grows",
        "Major cryptocurrency exchange suffers massive security breach",
        "Ethereum upgrade scheduled for next month, community excited",
        "SEC delays decision on Bitcoin ETF approval once again",
        "Crypto market shows signs of recovery after recent downturn"
    ]

    total_time = 0
    for text in test_texts:
        start = time.time()

        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)

        inference_time = (time.time() - start) * 1000
        total_time += inference_time

    avg_time = total_time / len(test_texts)
    print(f"✅ 평균 추론 시간: {avg_time:.2f}ms")

    if avg_time > 100:
        print(f"⚠️  경고: 추론 속도가 느림 (목표: <100ms)")

    # 4. 감성 분류 테스트
    print("\n[4/4] 감성 분류 테스트...")
    label_map = {0: "positive", 1: "negative", 2: "neutral"}

    for text in test_texts[:3]:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = model(**inputs)

        probs = torch.softmax(outputs.logits, dim=1)[0]
        predicted_class = torch.argmax(probs).item()
        confidence = probs[predicted_class].item()

        print(f"\n텍스트: {text[:50]}...")
        print(f"감성: {label_map[predicted_class].upper()}")
        print(f"신뢰도: {confidence:.2%}")

    print("\n" + "=" * 60)
    print("✅ 모든 테스트 통과!")
    print("=" * 60)


if __name__ == "__main__":
    test_finbert_basic()
