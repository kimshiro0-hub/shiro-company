import random
import sys
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
    print("경고: pyperclip 모듈이 설치되어 있지 않습니다. 클립보드 복사 기능이 비활성화됩니다.")
    print("클립보드 기능을 사용하려면 'pip install pyperclip'을 실행해주세요.")

class NovelAIPromptGenerator:
    def __init__(self):
        self.history = []
        self.character_genders = ["female", "male", "androgynous"]
        self.character_ages = ["young", "teenager", "adult", "elderly"]
        self.character_appearances = [
            "long hair", "short hair", "braids", "ponytail", "blue eyes", "red eyes", "green eyes",
            "glasses", "scarf", "hat", "dress", "suit", "casual clothes", "uniform",
            "muscular build", "slim figure", "curvy", "petite", "tall", "short"
        ]
        self.character_personalities = [
            "shy", "confident", "energetic", "calm", "mysterious", "cheerful", "serious",
            "playful", "elegant", "determined", "dreamy"
        ]

        self.background_places = [
            "forest", "city street", "beach", "futuristic laboratory", "cozy cafe",
            "ancient temple", "moonlit garden", "spaceship interior", "mountain peak",
            "underwater city", "desert outpost", "magical academy"
        ]
        self.background_times = [
            "daytime", "night", "sunrise", "sunset", "twilight", "rainy day", "snowy evening"
        ]
        self.background_atmospheres = [
            "peaceful", "chaotic", "mysterious", "romantic", "adventurous", "melancholy",
            "vibrant", "eerie", "futuristic", "fantasy"
        ]

        # Sora 형의 요청에 따라 'high resolution', 'detailed' 추가 및 정리
        self.style_tags = [
            "masterpiece", "best quality", "high quality", "ultra detailed", 
            "high resolution", "detailed", "absurdres", "intricate details", 
            "highly detailed", "dynamic lighting", "sharp focus", "volumetric lighting", 
            "photorealistic", "cinematic lighting", "vivid colors", "pastel colors", 
            "monochromatic", "digital art", "illustration", "anime style", "manga style", 
            "oil painting", "watercolor"
        ]

        self.negative_prompt_base = [
            "lowres", "bad anatomy", "bad hands", "text", "error", "missing fingers",
            "extra digit", "fewer digits", "cropped", "worst quality", "low quality",
            "normal quality", "jpeg artifacts", "signature", "watermark", "username",
            "blurry", "out of focus", "(bad-artist:1.2)", "(bad_prompt:1.2)", "mutation",
            "deformed", "ugly", "disfigured"
        ]

    def combine_prompt_parts(self, parts):
        """Combines a list of prompt parts into a single string."""
        return ", ".join(filter(None, parts)) # filter(None) removes empty strings

    def select_random_elements(self, elements, count):
        """Selects a specified number of random unique elements from a list."""
        return random.sample(elements, min(count, len(elements)))

    def generate_character(self):
        gender = random.choice(self.character_genders)
        age = random.choice(self.character_ages)
        
        # Using select_random_elements with random counts for flexibility
        appearances_count = random.randint(2, min(4, len(self.character_appearances)))
        appearances = self.select_random_elements(self.character_appearances, appearances_count)
        
        personalities_count = random.randint(1, min(2, len(self.character_personalities)))
        personalities = self.select_random_elements(self.character_personalities, personalities_count)
        
        character_parts = [gender, age] + appearances + personalities
        return self.combine_prompt_parts(character_parts)

    def generate_background(self):
        place = random.choice(self.background_places)
        time = random.choice(self.background_times)
        
        atmospheres_count = random.randint(1, min(2, len(self.background_atmospheres)))
        atmospheres = self.select_random_elements(self.background_atmospheres, atmospheres_count)
        
        background_parts = [place, time] + atmospheres
        return self.combine_prompt_parts(background_parts)

    def get_style_tags(self):
        """Returns a string of common style tags, ensuring 'masterpiece' is always included."""
        
        # 'masterpiece'는 항상 포함되도록 보장
        guaranteed_tags = ["masterpiece"]
        
        # 'masterpiece'를 제외한 태그 풀에서 추가 태그 선택
        pool_for_random = [tag for tag in self.style_tags if tag != "masterpiece"]
        
        # 전체 태그 수는 4~7개. 'masterpiece'가 1개 있으니 3~6개를 추가로 선택
        num_additional_tags = random.randint(3, min(6, len(pool_for_random)))
        
        additional_selected_tags = self.select_random_elements(pool_for_random, num_additional_tags)
        
        final_tags = guaranteed_tags + additional_selected_tags
        random.shuffle(final_tags) # 태그 순서를 무작위로 섞음
        
        return self.combine_prompt_parts(final_tags)

    def get_negative_prompt(self):
        """Returns a predefined string of negative prompts."""
        return self.combine_prompt_parts(self.negative_prompt_base)

    def generate_full_prompt(self):
        char_prompt = self.generate_character()
        bg_prompt = self.generate_background()
        style_prompt = self.get_style_tags()
        
        positive_parts = [char_prompt, bg_prompt, style_prompt]
        positive_prompt = self.combine_prompt_parts(positive_parts)
        
        negative_prompt = self.get_negative_prompt()
        
        return {
            "positive": positive_prompt,
            "negative": negative_prompt
        }

    def copy_to_clipboard(self, text):
        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(text)
                print("프롬프트가 클립보드에 복사되었습니다!")
            except pyperclip.PyperclipException as e:
                print(f"클립보드 복사 실패: {e}")
        else:
            print("pyperclip 모듈이 설치되어 있지 않아 클립보드 복사 기능을 사용할 수 없습니다.")

    def save_to_history(self, prompt_data):
        self.history.append(prompt_data)
        print("프롬프트가 히스토리에 저장되었습니다.")

    def show_history(self):
        if not self.history:
            print("저장된 프롬프트가 없습니다.")
            return

        print("\n--- 프롬프트 히스토리 ---")
        for i, prompt in enumerate(self.history):
            print(f"\n[{i+1}]")
            print(f"  긍정 프롬프트: {prompt['positive']}")
            print(f"  부정 프롬프트: {prompt['negative']}")
        print("-------------------------\n")

    def display_menu(self):
        print("\n--- NovelAI 프롬프트 생성기 ---")
        print("1. 캐릭터 프롬프트 생성")
        print("2. 배경/상황 프롬프트 생성")
        print("3. 전체 프롬프트 생성 (캐릭터 + 배경 + 스타일 + 부정)")
        print("4. 히스토리 보기")
        print("5. 종료")
        print("-------------------------------")

    def run(self):
        while True:
            self.display_menu()
            choice = input("메뉴를 선택하세요: ").strip()

            if choice == '1':
                char_prompt = self.generate_character()
                print(f"\n생성된 캐릭터 프롬프트:\n{char_prompt}\n")
                if input("클립보드에 복사하시겠습니까? (y/n): ").lower() == 'y':
                    self.copy_to_clipboard(char_prompt)
                
            elif choice == '2':
                bg_prompt = self.generate_background()
                print(f"\n생성된 배경/상황 프롬프트:\n{bg_prompt}\n")
                if input("클립보드에 복사하시겠습니까? (y/n): ").lower() == 'y':
                    self.copy_to_clipboard(bg_prompt)

            elif choice == '3':
                full_prompt = self.generate_full_prompt()
                print("\n--- 생성된 전체 프롬프트 ---")
                print(f"긍정 프롬프트: {full_prompt['positive']}")
                print(f"부정 프롬프트: {full_prompt['negative']}")
                print("----------------------------\n")
                
                if input("클립보드에 긍정 프롬프트를 복사하시겠습니까? (y/n): ").lower() == 'y':
                    self.copy_to_clipboard(full_prompt['positive'])
                
                if input("이 프롬프트를 히스토리에 저장하시겠습니까? (y/n): ").lower() == 'y':
                    self.save_to_history(full_prompt)

            elif choice == '4':
                self.show_history()

            elif choice == '5':
                print("프롬프트 생성기를 종료합니다.")
                break
            else:
                print("잘못된 선택입니다. 다시 시도해주세요.")


if __name__ == "__main__":
    generator = NovelAIPromptGenerator()
    generator.run()
    input("종료하려면 Enter를 누르세요...")