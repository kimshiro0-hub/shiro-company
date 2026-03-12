import json
import os

class PromptTemplate:
    """
    NovelAI 프롬프트 템플릿을 나타내는 클래스.
    이름, 카테고리, 프롬프트 내용, 태그를 관리합니다.
    """
    def __init__(self, name: str, category: str, prompt_content: str, tags: list = None):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("템플릿 이름은 비어 있을 수 없습니다.")
        if not isinstance(category, str) or not category.strip():
            raise ValueError("카테고리는 비어 있을 수 없습니다.")
        
        self.name = name.strip()
        self.category = category.strip()
        self.prompt_content = prompt_content
        # 태그는 모두 소문자로 저장하고 중복을 제거하며 정렬합니다.
        self.tags = sorted(list(set([t.strip().lower() for t in tags if t.strip()]))) if tags else []

    def to_dict(self) -> dict:
        """클래스 인스턴스를 딕셔너리로 변환하여 JSON 직렬화를 준비합니다."""
        return {
            "name": self.name,
            "category": self.category,
            "prompt_content": self.prompt_content,
            "tags": self.tags
        }

    @classmethod
    def from_dict(cls, data: dict):
        """딕셔너리로부터 PromptTemplate 인스턴스를 생성합니다."""
        return cls(
            name=data["name"],
            category=data["category"],
            prompt_content=data["prompt_content"],
            tags=data.get("tags", [])
        )

    def __str__(self):
        """템플릿의 문자열 표현을 반환합니다."""
        return (f"이름: {self.name}\n"
                f"카테고리: {self.category}\n"
                f"프롬프트: {self.prompt_content}\n"
                f"태그: {', '.join(self.tags) if self.tags else '없음'}")

    def __eq__(self, other):
        """두 템플릿이 동일한지 확인 (이름 기준, 대소문자 구분 없음)."""
        if not isinstance(other, PromptTemplate):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __hash__(self):
        """해시 가능하게 만듭니다 (set에 넣거나 딕셔너리 키로 사용 가능), 이름 기준으로 대소문자 구분 없음."""
        return hash(self.name.lower())


class PromptManager:
    """
    NovelAI 프롬프트 템플릿을 관리하는 클래스.
    추가, 삭제, 검색, 필터링, 저장/로드 기능을 제공합니다.
    """
    def __init__(self, filename: str = "templates.json"):
        self.default_filename = filename
        self.templates: list[PromptTemplate] = []
        self.load_templates(self.default_filename)
    
    def add_template(self, template: PromptTemplate):
        """템플릿을 추가합니다. 이름이 중복되면 기존 템플릿을 교체합니다. (대소문자 구분 없음)."""
        for i, t in enumerate(self.templates):
            if t.name.lower() == template.name.lower(): # 대소문자 구분 없이 중복 이름 체크
                self.templates[i] = template # 교체
                self.save_templates(self.default_filename)
                return
        self.templates.append(template) # 새로 추가
        self.save_templates(self.default_filename)
    
    def search_templates(self, query: str) -> list[PromptTemplate]:
        """이름 또는 프롬프트 내용에서 부분 일치하는 템플릿을 검색합니다. (대소문자 구분 없음)."""
        query_lower = query.lower()
        return [
            t for t in self.templates 
            if query_lower in t.name.lower() or query_lower in t.prompt_content.lower()
        ]
    
    def filter_by_category(self, category: str) -> list[PromptTemplate]:
        """카테고리로 템플릿을 필터링합니다. (대소문자 구분 없음)."""
        category_lower = category.lower()
        return [t for t in self.templates if t.category.lower() == category_lower]
    
    def search_by_tag(self, tag: str) -> list[PromptTemplate]:
        """태그로 템플릿을 검색합니다. (태그는 저장 시 이미 소문자로 처리됨)."""
        tag_lower = tag.lower()
        return [t for t in self.templates if tag_lower in t.tags]
    
    def delete_template(self, name: str) -> bool:
        """이름으로 템플릿을 삭제합니다. (대소문자 구분 없음)."""
        initial_count = len(self.templates)
        self.templates = [t for t in self.templates if t.name.lower() != name.lower()]
        if len(self.templates) < initial_count:
            self.save_templates(self.default_filename)
            return True
        return False
    
    def save_templates(self, filename: str):
        """현재 템플릿 목록을 JSON 파일에 저장합니다."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump([t.to_dict() for t in self.templates], f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"템플릿 저장 중 오류 발생: {e}")
        
    def load_templates(self, filename: str):
        """JSON 파일에서 템플릿을 로드합니다."""
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = [PromptTemplate.from_dict(d) for d in data]
            except json.JSONDecodeError:
                print("경고: JSON 파일이 손상되었거나 비어 있습니다. 새 파일을 시작합니다.")
                self.templates = []
            except Exception as e:
                print(f"템플릿 로드 중 오류 발생: {e}")
                self.templates = []
        else:
            self.templates = []

# 콘솔 기반 인터페이스 헬퍼 함수
def display_template_list(templates: list[PromptTemplate], title: str = "템플릿 목록"):
    """템플릿 목록을 콘솔에 출력합니다."""
    if not templates:
        print(f"\n--- {title}: 없음 ---")
        return
    print(f"\n--- {title} ({len(templates)}개) ---")
    for i, t in enumerate(templates):
        print(f"[{i+1}] {t.name} (카테고리: {t.category}, 태그: {', '.join(t.tags) if t.tags else '없음'})")
    print("--------------------")

def display_template_detail(template: PromptTemplate):
    """템플릿의 상세 정보를 콘솔에 출력합니다."""
    print("\n--- 템플릿 상세 ---")
    print(template)
    print("--------------------")

def get_template_by_name(manager: PromptManager, name: str) -> PromptTemplate | None:
    """이름으로 템플릿을 찾아 반환합니다. (대소문자 구분 없음)."""
    name_lower = name.lower()
    for t in manager.templates:
        if t.name.lower() == name_lower:
            return t
    return None

if __name__ == "__main__":
    manager = PromptManager(filename="novelai_templates.json") # 누나가 더블클릭할 때 기본 파일명 지정

    print("--- NovelAI 프롬프트 템플릿 관리자 (Teo's 버전) ---")
    print("누나가 더블클릭으로 실행할 수 있도록 기본 데모 기능을 제공합니다.")

    while True:
        print("\n--- 메뉴 ---")
        print("1. 템플릿 추가")
        print("2. 전체 템플릿 목록 보기")
        print("3. 템플릿 이름/내용으로 검색")
        print("4. 카테고리로 필터링")
        print("5. 태그로 검색")
        print("6. 템플릿 삭제")
        print("7. 상세 정보 보기")
        print("0. 종료")
        choice = input("선택: ").strip()

        if choice == '1':
            try:
                name = input("템플릿 이름: ").strip()
                if not name: raise ValueError("이름을 입력해주세요.")
                
                category = input("카테고리: ").strip()
                if not category: raise ValueError("카테고리를 입력해주세요.")

                content = input("프롬프트 내용: ").strip()
                if not content: raise ValueError("프롬프트 내용을 입력해주세요.")
                
                tags_input = input("태그 (쉼표로 구분, 예: anime, girl, cute): ")
                tags = [t.strip() for t in tags_input.split(',') if t.strip()]
                
                new_template = PromptTemplate(name, category, content, tags)
                
                manager.add_template(new_template)
                print(f"'{name}' 템플릿이 추가/업데이트되었습니다.")
            except ValueError as e:
                print(f"입력 오류: {e}")
            except Exception as e:
                print(f"템플릿 추가 중 예상치 못한 오류 발생: {e}")

        elif choice == '2':
            display_template_list(manager.templates, "전체 템플릿")

        elif choice == '3':
            keyword = input("검색할 키워드 (이름 또는 프롬프트 내용): ").strip()
            if not keyword:
                print("검색할 키워드를 입력해주세요.")
                continue
            results = manager.search_templates(keyword)
            display_template_list(results, f"'{keyword}' 검색 결과")

        elif choice == '4':
            category_filter = input("필터링할 카테고리: ").strip()
            if not category_filter:
                print("필터링할 카테고리를 입력해주세요.")
                continue
            results = manager.filter_by_category(category_filter)
            display_template_list(results, f"'{category_filter}' 카테고리 템플릿")

        elif choice == '5':
            tag_search = input("검색할 태그: ").strip()
            if not tag_search:
                print("검색할 태그를 입력해주세요.")
                continue
            results = manager.search_by_tag(tag_search)
            display_template_list(results, f"'{tag_search}' 태그 검색 결과")

        elif choice == '6':
            name_to_delete = input("삭제할 템플릿 이름: ").strip()
            if not name_to_delete:
                print("삭제할 템플릿 이름을 입력해주세요.")
                continue
            if manager.delete_template(name_to_delete):
                print(f"'{name_to_delete}' 템플릿이 삭제되었습니다.")
            else:
                print(f"'{name_to_delete}' 템플릿을 찾을 수 없습니다.")

        elif choice == '7':
            name_to_view = input("상세 정보를 볼 템플릿 이름: ").strip()
            if not name_to_view:
                print("상세 정보를 볼 템플릿 이름을 입력해주세요.")
                continue
            template = get_template_by_name(manager, name_to_view)
            if template:
                display_template_detail(template)
            else:
                print(f"'{name_to_view}' 템플릿을 찾을 수 없습니다.")

        elif choice == '0':
            print("관리자를 종료합니다.")
            break
        else:
            print("잘못된 선택입니다. 다시 시도해주세요.")

    input("종료하려면 Enter를 누르세요...")