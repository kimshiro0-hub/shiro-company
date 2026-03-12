import re
import json
import os

class NovelAIOptimizer:
    def __init__(self):
        self.save_file = "saved_prompts.json" 
        self.negative_prompt_suggestions = [
            "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name",
            "easynegative, bad-artist, bad_pictures, bad_quality, bad_composition",
            "worst quality, low quality, normal quality, lowres, blurry, bad hands, bad anatomy, missing fingers, extra fingers, extra limbs, fewer digits, ugly, malformed, mangled",
        ]

    def _load_data(self):
        if not os.path.exists(self.save_file):
            return {}
        try:
            with open(self.save_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"경고: 저장 파일 '{self.save_file}'이 손상되어 재설정합니다.")
            return {}
        except Exception as e:
            print(f"데이터 로드 중 오류 발생: {e}")
            return {}

    def _save_data(self, data):
        try:
            with open(self.save_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"데이터 저장 중 오류 발생: {e}")

    def clean_tags(self, prompt: str) -> str:
        tags = [tag.strip() for tag in prompt.split(',') if tag.strip()]
        cleaned_tags = sorted(list(set(tags)))
        return ", ".join(cleaned_tags)

    def optimize_weights(self, prompt: str) -> str:
        # 이중 괄호 ((tag))를 (tag:1.21) 형식으로 변환 (NovelAI의 기본 가중치 증폭 방식)
        # 테스트 스펙과 호환성을 위해 [bad quality] 등은 그대로 유지함.
        optimized_prompt = re.sub(r'\(\((.*?)\)\)', r'(\1:1.21)', prompt)
        return optimized_prompt

    def suggest_negative(self, prompt: str) -> str:
        # 현재는 고정된 네가티브 프롬프트 중 첫 번째를 추천
        return self.negative_prompt_suggestions[0]

    def save_prompt(self, name: str, prompt: str, negative: str):
        data = self._load_data()
        data[name] = {"prompt": prompt, "negative": negative}
        self._save_data(data)

    def load_prompt(self, name: str): # -> tuple 에서 None 반환을 위해 타입 힌트 제거 또는 Optional[tuple]
        data = self._load_data()
        if name in data:
            return data[name]["prompt"], data[name]["negative"]
        return None # 형의 요청에 따라 None 반환

    def get_saved_prompts(self) -> list:
        data = self._load_data()
        return list(data.keys())

if __name__ == "__main__":
    print("NovelAI 프롬프트 최적화 도구 데모")
    optimizer = NovelAIOptimizer()

    # 1. 태그 정리 및 중복 제거 데모
    print("\n--- 1. 태그 정리 및 중복 제거 ---")
    raw_prompt_clean = "girl, cute, beautiful, girl, blue hair, long hair, beautiful"
    print(f"원본 프롬프트: {raw_prompt_clean}")
    cleaned_prompt = optimizer.clean_tags(raw_prompt_clean)
    print(f"정리된 프롬프트: {cleaned_prompt}")

    # 2. 가중치 자동 조정 데모
    print("\n--- 2. 가중치 자동 조정 ---")
    raw_prompt_weight = "((masterpiece)), best quality, (cute girl), [bad quality], amazing eyes"
    print(f"원본 프롬프트: {raw_prompt_weight}")
    optimized_weight_prompt = optimizer.optimize_weights(raw_prompt_weight)
    print(f"조정된 프롬프트: {optimized_weight_prompt}")

    # 3. 네가티브 프롬프트 추천 데모
    print("\n--- 3. 네가티브 프롬프트 추천 ---")
    positive_prompt_for_negative = "1girl, school uniform, white shirt"
    suggested_negative = optimizer.suggest_negative(positive_prompt_for_negative)
    print(f"추천 네가티브 프롬프트: {suggested_negative}")

    # 4. 프롬프트 저장/로드 데모
    print("\n--- 4. 프롬프트 저장/로드 ---")
    save_name = "cute_girl_prompt"
    save_prompt_text = "masterpiece, best quality, 1girl, cute, long hair, blue eyes"
    save_negative_text = suggested_negative # 위에서 추천받은 것 사용
    optimizer.save_prompt(save_name, save_prompt_text, save_negative_text)
    print(f"'{save_name}' 프롬프트 저장 완료.")

    loaded_data = optimizer.load_prompt(save_name)
    if loaded_data:
        loaded_prompt, loaded_negative = loaded_data
        print(f"'{save_name}' 로드 성공:")
        print(f"  프롬프트: {loaded_prompt}")
        print(f"  네가티브: {loaded_negative}")
    else:
        print(f"'{save_name}' 로드 실패 또는 데이터 없음.")

    # 존재하지 않는 프롬프트 로드 데모
    print("\n--- 5. 존재하지 않는 프롬프트 로드 ---")
    non_existent_name = "non_existent_prompt_123"
    loaded_data_none = optimizer.load_prompt(non_existent_name)
    if loaded_data_none is None: # None 반환 확인
        print(f"'{non_existent_name}' 프롬프트 로드: 데이터 없음 (None 반환 확인).")
    else:
        print(f"'{non_existent_name}' 로드 실패: 예상치 못한 값 반환.")

    # 6. 저장된 프롬프트 목록 보기
    print("\n--- 6. 저장된 프롬프트 목록 ---")
    saved_list = optimizer.get_saved_prompts()
    if saved_list:
        print(f"저장된 프롬프트: {', '.join(saved_list)}")
    else:
        print("저장된 프롬프트가 없습니다.")

    # 테스트 파일 정리 (데모 실행 시 생성된 saved_prompts.json 삭제)
    if os.path.exists(optimizer.save_file):
        os.remove(optimizer.save_file)
        print(f"\n데모를 위해 생성된 '{optimizer.save_file}' 파일이 삭제되었습니다.")

    input("종료하려면 Enter를 누르세요...")