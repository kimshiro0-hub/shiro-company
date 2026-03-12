import pytest
import json
import os
from novelai_prompt_manager import PromptTemplate, PromptManager

def test_prompt_template_creation():
    template = PromptTemplate("test", "character", "cute girl", ["anime", "kawaii"])
    assert template.name == "test"
    assert template.category == "character"
    assert "anime" in template.tags

def test_add_template():
    manager = PromptManager()
    template = PromptTemplate("test", "character", "cute girl", ["anime"])
    manager.add_template(template)
    assert len(manager.templates) == 1
    assert manager.templates[0].name == "test"

def test_search_by_name():
    manager = PromptManager()
    template = PromptTemplate("cute_girl", "character", "kawaii girl", ["anime"])
    manager.add_template(template)
    results = manager.search_templates("cute")
    assert len(results) == 1
    assert results[0].name == "cute_girl"

def test_filter_by_category():
    manager = PromptManager()
    manager.add_template(PromptTemplate("char1", "character", "girl", []))
    manager.add_template(PromptTemplate("bg1", "background", "forest", []))
    results = manager.filter_by_category("character")
    assert len(results) == 1
    assert results[0].category == "character"

def test_search_by_tag():
    manager = PromptManager()
    template = PromptTemplate("test", "character", "girl", ["anime", "cute"])
    manager.add_template(template)
    results = manager.search_by_tag("anime")
    assert len(results) == 1
    assert "anime" in results[0].tags

def test_delete_template():
    manager = PromptManager()
    manager.add_template(PromptTemplate("test", "character", "girl", []))
    manager.delete_template("test")
    assert len(manager.templates) == 0

def test_save_and_load():
    manager = PromptManager()
    template = PromptTemplate("test", "character", "cute girl", ["anime"])
    manager.add_template(template)
    manager.save_templates("test_templates.json")
    
    new_manager = PromptManager()
    new_manager.load_templates("test_templates.json")
    assert len(new_manager.templates) == 1
    assert new_manager.templates[0].name == "test"
    
    os.remove("test_templates.json")

def test_duplicate_name_handling():
    manager = PromptManager()
    manager.add_template(PromptTemplate("test", "character", "girl1", []))
    manager.add_template(PromptTemplate("test", "character", "girl2", []))
    assert len(manager.templates) == 1
    assert manager.templates[0].prompt == "girl2"

def test_empty_search():
    manager = PromptManager()
    results = manager.search_templates("nonexistent")
    assert len(results) == 0