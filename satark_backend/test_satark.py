"""
Test script for SATARK.AI system
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test if all modules can be imported."""
    try:
        print("🧪 Testing SATARK.AI imports...")
        
        from models.survey_schema import PromptIntent, SurveyGenerationRequest
        print("✅ Survey schema models imported")
        
        from core.prompt_parser import PromptParser
        print("✅ Prompt parser imported")
        
        from core.domain_classifier import DomainClassifier
        print("✅ Domain classifier imported")
        
        from core.retrieval_engine import RetrievalEngine
        print("✅ Retrieval engine imported")
        
        from core.survey_builder import SurveyBuilder
        print("✅ Survey builder imported")
        
        from core.validation_engine import ValidationEngine
        print("✅ Validation engine imported")
        
        from ml.anomaly_detector import AnomalyDetector
        print("✅ Anomaly detector imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_prompt_parsing():
    """Test prompt parsing functionality."""
    try:
        print("\n🧪 Testing prompt parsing...")
        
        from core.prompt_parser import PromptParser
        parser = PromptParser()
        
        test_prompt = "A survey for rural women about healthcare access with 8 questions"
        intent = parser.parse(test_prompt)
        
        print(f"✅ Parsed intent: domain={intent.domain}, audience={intent.audience}")
        return True
        
    except Exception as e:
        print(f"❌ Prompt parsing error: {e}")
        return False

def test_domain_classification():
    """Test domain classification."""
    try:
        print("\n🧪 Testing domain classification...")
        
        from core.domain_classifier import DomainClassifier
        classifier = DomainClassifier()
        
        test_prompt = "Employment survey for urban youth"
        domain = classifier.classify(test_prompt)
        
        print(f"✅ Classified domain: {domain}")
        return True
        
    except Exception as e:
        print(f"❌ Domain classification error: {e}")
        return False

def test_question_retrieval():
    """Test question retrieval."""
    try:
        print("\n🧪 Testing question retrieval...")
        
        from core.retrieval_engine import RetrievalEngine
        from models.survey_schema import PromptIntent
        
        retrieval_engine = RetrievalEngine()
        
        intent = PromptIntent(
            domain="health",
            audience="women",
            keywords=["healthcare", "access"]
        )
        
        questions = retrieval_engine.retrieve_questions(intent, 5)
        
        print(f"✅ Retrieved {len(questions)} questions")
        return True
        
    except Exception as e:
        print(f"❌ Question retrieval error: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 SATARK.AI System Test")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_prompt_parsing,
        test_domain_classification,
        test_question_retrieval
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! SATARK.AI is ready.")
    else:
        print("⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()