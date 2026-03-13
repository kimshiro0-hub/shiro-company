import pytest
from novelai_prompt_generator import NovelAIPromptGenerator

def test_character_generation():
    generator = NovelAIPromptGenerator()
    character = generator.generate_character()
    assert isinstance(character, str)
    assert len(character) > 0

def test_background_generation():
    generator = NovelAIPromptGenerator()
    background = generator.generate_background()
    assert isinstance(background, str)
    assert len(background) > 0

def test_style_tags():
    generator = NovelAIPromptGenerator()
    style = generator.get_style_tags()
    assert isinstance(style, str)
    assert "masterpiece" in style.lower()

def test_negative_prompt():
    generator = NovelAIPromptGenerator()
    negative = generator.get_negative_prompt()
    assert isinstance(negative, str)
    assert len(negative) > 0

def test_full_prompt_generation():
    generator = NovelAIPromptGenerator()
    prompt = generator.generate_full_prompt()
    assert isinstance(prompt, dict)
    assert "positive" in prompt
    assert "negative" in prompt

def test_prompt_combination():
    generator = NovelAIPromptGenerator()
    parts = ["1girl", "school uniform", "classroom"]
    combined = generator.combine_prompt_parts(parts)
    assert isinstance(combined, str)
    assert all(part in combined for part in parts)

def test_random_element_selection():
    generator = NovelAIPromptGenerator()
    elements = ["a", "b", "c"]
    selected = generator.select_random_elements(elements, 2)
    assert len(selected) == 2
    assert all(elem in elements for elem in selected)