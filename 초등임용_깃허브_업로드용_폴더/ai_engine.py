import os
import json
import re
import random
import time
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GAKNON_MATRIX_PATH = os.path.join(BASE_DIR, "data", "music_gaknon_matrix.json")

try:
    with open(GAKNON_MATRIX_PATH, "r", encoding="utf-8") as f:
        GAKNON_DATA = json.load(f)
except Exception:
    GAKNON_DATA = {}

FALLBACK_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-lite",
    "gemini-2.5-pro",
    "gemini-1.5-pro"
]

def get_gemini_client(api_key: str):
    return genai.Client(api_key=api_key.strip())

def extract_json(text: str):
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
            
    m_list = re.search(r"(\[[\s\S]*\])", text)
    if m_list:
        try:
            return json.loads(m_list.group(1).strip())
        except Exception:
            pass

    m_dict = re.search(r"(\{[\s\S]*\})", text)
    if m_dict:
        try:
            return json.loads(m_dict.group(1).strip())
        except Exception:
            pass

    raise ValueError(f"AI 응답에서 JSON 형식을 추출할 수 없습니다: {text[:250]}")

def get_supported_models(api_key: str) -> list[str]:
    """Dynamically queries Google GenAI for available models supporting generateContent."""
    if not api_key or not api_key.strip():
        return FALLBACK_MODELS
    
    try:
        client = get_gemini_client(api_key)
        discovered = []
        for m in client.models.list():
            actions = getattr(m, "supported_actions", []) or []
            if "generateContent" in actions:
                name = m.name
                if name.startswith("models/"):
                    name = name[len("models/"):]
                if any(ex in name.lower() for ex in ["embed", "imagen", "aqa", "tts", "whisper"]):
                    continue
                discovered.append(name)
        
        if discovered:
            def model_sort_key(name):
                nl = name.lower()
                if "2.5-flash" in nl:
                    return 0
                if "2.0-flash" in nl and "lite" not in nl:
                    return 1
                if "1.5-flash" in nl:
                    return 2
                if "flash" in nl:
                    return 3
                if "2.5-pro" in nl:
                    return 4
                if "1.5-pro" in nl:
                    return 5
                if "pro" in nl:
                    return 6
                return 10
            
            discovered.sort(key=model_sort_key)
            return discovered
    except Exception as e:
        print(f"Error querying models.list: {e}")
        
    return FALLBACK_MODELS

def test_api_connection(api_key: str, model_name: str = None) -> tuple[bool, str, str]:
    if not api_key or not api_key.strip():
        return False, "API 키가 입력되지 않았습니다.", ""
        
    client = get_gemini_client(api_key)
    models_to_try = [model_name] if model_name else []
    models_to_try += get_supported_models(api_key)
    
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]
    
    last_err = ""
    for m in models_to_try:
        try:
            resp = client.models.generate_content(
                model=m,
                contents="OK",
                config=types.GenerateContentConfig(max_output_tokens=5)
            )
            if resp and resp.text:
                return True, f"연결 성공! ({m} 정상 작동)", m
        except Exception as e:
            last_err = str(e)
            continue
            
    return False, f"연결 실패: {last_err}", ""

def generate_ai_questions(api_key: str, q_type: str, tier: str, domain: str, count: int, model_name: str = None):
    client = get_gemini_client(api_key)
    
    tier_key_map = {
        "A등급 (초빈출)": "A_tier_절대빈출",
        "B등급 (유력 출제)": "B_tier_유력출제",
        "C등급 (세부 각론)": "C_tier_잠재각론",
        "D등급 (교육과정)": "D_tier_지엽성취기준"
    }
    
    context_data = GAKNON_DATA.get("abcd_gaknon_matrix", {})
    if tier in tier_key_map:
        tier_items = context_data.get(tier_key_map[tier], [])
    else:
        tier_items = []
        for v in context_data.values():
            if isinstance(v, list):
                tier_items.extend(v)
                
    if domain and domain != "전체":
        domain_filtered = [item for item in tier_items if domain in str(item.get("domain", "")) or domain in str(item.get("key_concepts", ""))]
        if domain_filtered:
            tier_items = domain_filtered
            
    sample_size = min(len(tier_items), 8)
    sampled_context = random.sample(tier_items, sample_size) if sample_size > 0 else tier_items
    random_seed_str = f"출제세션-{int(time.time()*1000) % 100000}-{random.randint(100, 999)}"

    system_instruction = f"""
당신은 대한민국 '초등교원 임용후보자 선정경쟁시험(초등 임용고시)' 1차 교육과정 음악과의 최고 권위 수석 출제위원입니다.
반드시 제공된 [초등 음악 각론 및 기출 지식 베이스]를 바탕으로, 실제 임용고시의 엄격한 출제 기준과 루브릭에 맞추어 완전히 새롭고 참신한 변형 문제를 생성해야 합니다.

[출제 요구 조건]
1. 요청 문제 형태: {q_type}
2. 중요도 등급: {tier}
3. 세부 영역: {domain}
4. 생성할 문항 수: {count}개
5. 매번 완전히 다른 제재곡과 악보/교사대화/조건을 조합하여 중복 없는 새로운 미기출 문제를 창작하십시오.

[반드시 준수할 JSON 출력 스키마]
반드시 다음 JSON 배열 형식만 출력하십시오:
[
  {{
    "id": "AI_Q1",
    "type": "개념 빈칸 채우기 (단답형) | 완전 서술형 | 실전 기출 대문항 세트",
    "tier": "{tier}",
    "domain": "{domain}",
    "title": "문항 핵심 주제명",
    "points": 1.0 또는 2.0 또는 4.0,
    "question": "단일 문항 발문 (단답형이나 서술형일 때 작성, 세트형이면 null)",
    "dialogue": "실전 기출 대문항 세트일 때 교사 대화문 HTML (단일 문항이면 null)",
    "sub_questions": [
      {{
        "sub_no": "1)",
        "type": "단답형 또는 서술형",
        "question": "소문항 발문",
        "answer": "공식 모범답안",
        "keywords": ["필수키워드1", "필수키워드2"],
        "rubric": [["조건 설명", ["필수단어1", "필수단어2"]]],
        "points": 1.0 또는 2.0
      }}
    ],
    "answer": "단일 문항 공식 모범답안 (세트형이면 null)",
    "keywords": ["필수키워드1", "필수키워드2"],
    "rubric": [
      ["조건 1 설명 (배점)", ["키워드A", "동의어A"]],
      ["조건 2 설명 (배점)", ["키워드B", "동의어B"]]
    ]
  }}
]
"""

    prompt = f"""
[무작위 출제 시드]: {random_seed_str}
다음 [선별된 음악 각론 지식 베이스 요약]을 참고하여 고품질의 새로운 {count}문항을 생성해 주십시오:
{json.dumps(sampled_context, ensure_ascii=False, indent=2)}
"""

    # Build candidate models list
    models_to_try = [model_name] if model_name else []
    models_to_try += get_supported_models(api_key)
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    attempts = {}
    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8,
                    response_mime_type="application/json"
                )
            )
            raw_text = response.text or ""
            data = extract_json(raw_text)
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list) and len(data) > 0:
                return data, m
        except Exception as e:
            attempts[m] = str(e)
            continue

    raise RuntimeError(f"모든 AI 모델 호출 실패:\n" + "\n".join(f"• {m}: {err}" for m, err in attempts.items()))

def evaluate_with_ai(api_key: str, question: str, model_answer: str, rubric_list: list, user_answer: str, max_points: float, model_name: str = None):
    if not user_answer or not user_answer.strip():
        return {
            "score": 0.0,
            "score_ratio": 0.0,
            "critique": "답안이 작성되지 않았습니다.",
            "passed_points": [],
            "deductions": ["답안 미입력"]
        }
        
    client = get_gemini_client(api_key)
    
    prompt = f"""
당신은 대한민국 초등교원 임용시험 1차 교육과정 수석 채점관입니다.
다음 문제와 루브릭(채점 기준표), 모범답안을 기준으로 수험생의 답안을 엄격하게 칼채점하십시오.

[문제 정보]
- 문제: {question}
- 공식 모범답안: {model_answer}
- 세부 루브릭 기준: {json.dumps(rubric_list, ensure_ascii=False)}
- 만점: {max_points}점

[수험생 입력 답안]
{user_answer}

[출력 요구 JSON 포맷]
{{
  "earned_points": 획득점수(float, 0.0 ~ {max_points}),
  "passed_criteria": ["충족한 조건 설명1", "충족한 조건 설명2"],
  "deducted_criteria": ["감점 사유 및 누락 조건1", "감점 사유 및 누락 조건2"],
  "evaluator_feedback": "수험생을 위한 2~3문장의 날카롭고 유익한 총평 피드백"
}}
"""

    models_to_try = [model_name] if model_name else []
    models_to_try += get_supported_models(api_key)
    seen = set()
    models_to_try = [m for m in models_to_try if m and not (m in seen or seen.add(m))]

    attempts = {}
    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            raw_text = response.text or ""
            res = extract_json(raw_text)
            earned = float(res.get("earned_points", 0.0))
            earned = max(0.0, min(max_points, earned))
            
            return {
                "score": earned,
                "score_ratio": earned / max_points if max_points > 0 else 1.0,
                "critique": res.get("evaluator_feedback", ""),
                "passed_points": res.get("passed_criteria", []),
                "deductions": res.get("deducted_criteria", [])
            }
        except Exception as e:
            attempts[m] = str(e)
            continue

    raise RuntimeError(f"AI 채점 모델 호출 실패:\n" + "\n".join(f"• {m}: {err}" for m, err in attempts.items()))

print("ai_engine test script successfully compiled!")
