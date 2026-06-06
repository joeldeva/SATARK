import sys
sys.path.insert(0, 'backend')

from utils.knowledge_loader import KnowledgeBaseLoader
from services.prompt_parser import PromptParser
from services.rule_engine import RuleEngine
from services.survey_generator import SurveyGenerator

# Lightweight test - skip RAG/vector model
class SimpleRAG:
    def __init__(self, kb):
        self.kb = kb
    def build_index(self):
        return self
    def search(self, query, domain=None, tags=None, top_k=20):
        results = []
        for d in ([domain] if domain else self.kb.surveys.keys()):
            results.extend(self.kb.surveys.get(d, {}).get("questions", []))
        return results[:top_k]

kb = KnowledgeBaseLoader(base_path='knowledge_base').load_all()
parser = PromptParser()
rag = SimpleRAG(kb)
rules = RuleEngine(kb)
gen = SurveyGenerator(parser, rag, rules)

survey = gen.generate('A survey for rural women about healthcare access with 8 questions', 'test_user')

print("Survey ID:", survey["survey_id"])
print("Title:", survey["title"])
print("Domain:", survey["domain"])
print("Questions:", len(survey["questions"]))
print("Audience:", survey["target_audience"])
print()
for q in survey["questions"]:
    print("  Q" + str(q["question_number"]) + ": " + q["text"][:70])

print()
print("SUCCESS - SATARK core pipeline working")
