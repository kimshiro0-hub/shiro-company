import pytest
from novelai_prompt_optimizer import NovelAIOptimizer
import os
import tempfile

def test_clean_tags():
    optimizer = NovelAIOptimizer()
    result = optimizer.clean_tags("girl, girl, beautiful, cute, beautiful")
    assert "girl" in result
    assert result.count("girl") == 1
    assert result.count("beautiful") == 1

def test_optimize_weights():
    optimizer = NovelAIOptimizer()
    result = optimizer.optimize_weights("((girl)), [bad quality]")
    assert "{" in result or "(" in result
    assert "[" in result or result.count("(") != result.count(")")

def test_suggest_negative():
    optimizer = NovelAIOptimizer()
    result = optimizer.suggest_negative("1girl, school uniform")
    assert len(result) > 0
    assert isinstance(result, str)

def test_save_and_load_prompt():
    optimizer = NovelAIOptimizer()
    test_name = "test_prompt"
    test_prompt = "1girl, beautiful"
    test_negative = "bad quality"
    
    optimizer.save_prompt(test_name, test_prompt, test_negative)
    loaded = optimizer.load_prompt(test_name)
    
    assert loaded is not None
    assert loaded[0] == test_prompt
    assert loaded[1] == test_negative

def test_get_saved_prompts():
    optimizer = NovelAIOptimizer()
    prompts = optimizer.get_saved_prompts()
    assert isinstance(prompts, list)

def test_empty_prompt_handling():
    optimizer = NovelAIOptimizer()
    result = optimizer.clean_tags("")
    assert result == ""
    
def test_weight_preservation():
    optimizer = NovelAIOptimizer()
    result = optimizer.optimize_weights("{masterpiece:1.5}")
    assert "1.5" in result

def test_invalid_prompt_load():
    optimizer = NovelAIOptimizer()
    result = optimizer.load_prompt("nonexistent")
    assert result is None