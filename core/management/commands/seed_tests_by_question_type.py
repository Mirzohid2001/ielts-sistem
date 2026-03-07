"""
Bazadagi barcha testlarni o'chirib, har bir savol turi bo'yicha bittadan namuna test yaratadi.
Keyinchalik admin xohlagan savol turiga qarab shu namunalarga o'xshab test yarata oladi.

Ishlatish:
  python manage.py seed_tests_by_question_type
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Category, Test, Question, ReadingPassage


# Har bir savol: order, question_type, question_text, option_*, correct_answer, options_json, correct_answer_json
def _q(order, question_type, part=1, **kwargs):
    d = {"order": order, "question_type": question_type, "options_json": {"part": part}}
    d.update(kwargs)
    return d

# ——— MCQ: 8 ta xilma-xil savol ———
MCQ_QUESTIONS = [
    _q(1, "mcq", question_text="What is the main topic of the passage?", option_a="Stress in cities", option_b="The development of urban green spaces", option_c="Property prices", option_d="European wildlife", correct_answer="b"),
    _q(2, "mcq", question_text="According to paragraph A, what is one concern about new parks?", option_a="Lower wellbeing", option_b="Rising property prices and displacement", option_c="Lack of funding", option_d="Loss of biodiversity", correct_answer="b"),
    _q(3, "mcq", question_text="The Journal of Urban Ecology research linked wellbeing to what?", option_a="Property values", option_b="Access to nature within 500 metres", option_c="Number of parks in a city", option_d="Rooftop gardens only", correct_answer="b"),
    _q(4, "mcq", question_text="In paragraph B, what is said to be key for wildlife in cities?", option_a="Large single parks", option_b="Connectivity between green areas", option_c="Non-native species", option_d="School involvement", correct_answer="b"),
    _q(5, "mcq", question_text="Which cities are mentioned as examples of best practice in paragraph C?", option_a="London and Singapore", option_b="Copenhagen and Melbourne", option_c="European cities only", option_d="None", correct_answer="b"),
    _q(6, "mcq", question_text="What problem does the passage associate with one-off grants?", option_a="Too much biodiversity", option_b="Initial planting followed by neglect", option_c="Gentrification", option_d="Lack of research", correct_answer="b"),
    _q(7, "mcq", question_text="What is suggested as important for long-term success of green spaces?", option_a="Developer contributions only", option_b="Ring-fenced budgets and community involvement", option_c="Fewer species", option_d="Isolated patches", correct_answer="b"),
    _q(8, "mcq", question_text="The passage as a whole is primarily concerned with what?", option_a="History of urban planning", option_b="Urban green spaces: benefits, challenges and good practice", option_c="Wildlife in Europe", option_d="Property markets", correct_answer="b"),
]

# ——— True / False: 8 ta ———
TF_QUESTIONS = [
    _q(1, "true_false", question_text="The passage states that access to nature near home is linked to lower stress.", option_a="TRUE", option_b="FALSE", correct_answer="a"),
    _q(2, "true_false", question_text="All cities mentioned have reduced property prices after adding parks.", option_a="TRUE", option_b="FALSE", correct_answer="b"),
    _q(3, "true_false", question_text="Ecologists emphasise the importance of connecting green areas.", option_a="TRUE", option_b="FALSE", correct_answer="a"),
    _q(4, "true_false", question_text="Peregrine falcons are mentioned as an example of urban wildlife.", option_a="TRUE", option_b="FALSE", correct_answer="a"),
    _q(5, "true_false", question_text="Funding for green spaces is described as unproblematic.", option_a="TRUE", option_b="FALSE", correct_answer="b"),
    _q(6, "true_false", question_text="Community involvement in design and upkeep is mentioned as good practice.", option_a="TRUE", option_b="FALSE", correct_answer="a"),
    _q(7, "true_false", question_text="The passage says that only European cities have invested in green spaces.", option_a="TRUE", option_b="FALSE", correct_answer="b"),
    _q(8, "true_false", question_text="Schools and local groups can adopt sections of parkland.", option_a="TRUE", option_b="FALSE", correct_answer="a"),
]

# ——— True / False / Not Given: 8 ta ———
TFNG_QUESTIONS = [
    _q(1, "true_false_not_given", question_text="The research in the Journal of Urban Ecology was conducted in 2020.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="c"),
    _q(2, "true_false_not_given", question_text="Property prices often rise when new parks are created in a neighbourhood.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="a"),
    _q(3, "true_false_not_given", question_text="Native species are recommended for urban planting schemes.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="a"),
    _q(4, "true_false_not_given", question_text="Melbourne has the largest urban park in the world.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="c"),
    _q(5, "true_false_not_given", question_text="One-off grants can lead to neglect after initial planting.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="a"),
    _q(6, "true_false_not_given", question_text="Green corridors allow wildlife populations to move and mix.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="a"),
    _q(7, "true_false_not_given", question_text="Copenhagen has ring-fenced budgets for green space maintenance.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="a"),
    _q(8, "true_false_not_given", question_text="The passage states that gentrification is always negative.", option_a="TRUE", option_b="FALSE", option_c="NOT GIVEN", correct_answer="c"),
]

# ——— Yes / No / Not Given: 8 ta ———
YNNG_QUESTIONS = [
    _q(1, "yes_no_not_given", question_text="Do the findings cited in paragraph A support a link between nature and wellbeing?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
    _q(2, "yes_no_not_given", question_text="Does the author agree that new parks cause gentrification?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
    _q(3, "yes_no_not_given", question_text="Have European cities documented the return of peregrine falcons?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
    _q(4, "yes_no_not_given", question_text="Is connectivity between habitats the only factor for biodiversity?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="c"),
    _q(5, "yes_no_not_given", question_text="Do the best-practice cities use community involvement?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
    _q(6, "yes_no_not_given", question_text="Does the passage recommend relying only on developer contributions?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="b"),
    _q(7, "yes_no_not_given", question_text="Are rooftop gardens mentioned as part of urban greening?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
    _q(8, "yes_no_not_given", question_text="Does the author suggest that social ties are strengthened by park adoption?", option_a="YES", option_b="NO", option_c="NOT GIVEN", correct_answer="a"),
]

# ——— Fill in the blank / Summary / Sentence completion: 8 ta (passage ga mos) ———
FILL_BLANK_QUESTIONS = [
    _q(1, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nGreen spaces within [1] metres of one's home are linked to lower stress.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["500"]),
    _q(2, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nCritics warn that new parks can lead to [1], pushing out residents.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["gentrification"]),
    _q(3, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nEcologists say [1] between green areas is key for wildlife.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["connectivity"]),
    _q(4, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nFunding from one-off [1] can lead to neglect later.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["grants"]),
    _q(5, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nCities like Copenhagen use [1]-fenced budgets for maintenance.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["ring"]),
    _q(6, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nCommunity [1] in design and upkeep is part of best practice.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["involvement"]),
    _q(7, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nSchools can [1] sections of parkland.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["adopt"]),
    _q(8, "fill_blank", question_text="Complete the sentence. Use ONE WORD ONLY.\n\nThe result includes stronger [1] ties.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["social"]),
]

SUMMARY_QUESTIONS = [
    _q(1, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\nUrban green spaces have become important in [1] planning. Research links nature nearby to lower [2] and higher wellbeing. A concern is [3] when property prices rise.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["urban", "stress", "gentrification"]),
    _q(2, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\nBiodiversity in cities needs [1] so that species can move. Studies show species such as the peregrine [2] returning. The aim is to avoid [3] patches.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["connectivity", "falcon", "isolated"]),
    _q(3, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\n[1] and maintenance are challenges. Best practice includes ring-fenced [2] and [3] involvement.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Funding", "budgets", "community"]),
    _q(4, "summary_completion", question_text="Complete the summary. Use NO MORE THAN TWO WORDS.\n\nMany cities rely on one-off [1] or [2] contributions, which can lead to [3] after initial planting.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["grants", "developer", "neglect"]),
    _q(5, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\n[1] and local groups can adopt parkland. This strengthens [2] ties and gives a model for [3] development.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Schools", "social", "sustainable"]),
    _q(6, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\nParagraph A discusses wellbeing and [1]. Paragraph B focuses on [2]. Paragraph C deals with [3] and maintenance.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["gentrification", "biodiversity", "Funding"]),
    _q(7, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\nNative [1] and varied habitats support wildlife. [2] between parks helps populations [3].", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["species", "Connectivity", "move"]),
    _q(8, "summary_completion", question_text="Complete the summary. Use ONE WORD ONLY.\n\nThe passage gives [1] from London to Singapore and from Copenhagen to [2], and recommends long-term [3] of green spaces.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["examples", "Melbourne", "maintenance"]),
]

NOTES_QUESTIONS = [
    _q(1, "notes_completion", question_text="Complete the notes. Write NO MORE THAN TWO WORDS AND/OR A NUMBER.\n\nUrban green spaces — benefits: lower [1], higher [2]. Distance: within [3] metres.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS AND/OR A NUMBER"}, correct_answer_json=["stress", "wellbeing", "500"]),
    _q(2, "notes_completion", question_text="Complete the notes. Write ONE WORD AND/OR A NUMBER.\n\nConcern: [1] — prices rise, residents [2]. Wildlife needs [3].", options_json={"part": 1, "instruction": "ONE WORD AND/OR A NUMBER"}, correct_answer_json=["gentrification", "displaced", "connectivity"]),
    _q(3, "notes_completion", question_text="Complete the notes. Write NO MORE THAN TWO WORDS.\n\nFunding: avoid [1] grants only. Use [2] budgets and [3] involvement.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["one-off", "ring-fenced", "community"]),
    _q(4, "notes_completion", question_text="Complete the notes. Write ONE WORD ONLY.\n\nExample species: peregrine [1]. Key idea: [2] of green areas. Result: stronger [3] ties.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["falcon", "connectivity", "social"]),
    _q(5, "notes_completion", question_text="Complete the notes. Write NO MORE THAN TWO WORDS.\n\nBest practice cities: [1] and [2]. Schools can [3] parkland.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["Copenhagen", "Melbourne", "adopt"]),
    _q(6, "notes_completion", question_text="Complete the notes. Write ONE WORD AND/OR A NUMBER.\n\nParagraph A: [1] and gentrification. Paragraph B: [2]. Paragraph C: [3] and maintenance.", options_json={"part": 1, "instruction": "ONE WORD AND/OR A NUMBER"}, correct_answer_json=["wellbeing", "biodiversity", "Funding"]),
    _q(7, "notes_completion", question_text="Complete the notes. Write NO MORE THAN TWO WORDS.\n\nRisk: initial [1] then [2]. Solution: [3] and community role.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["planting", "neglect", "budgets"]),
    _q(8, "notes_completion", question_text="Complete the notes. Write ONE WORD ONLY.\n\nJournal of [1] Ecology. Native [2]. Green [3].", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Urban", "species", "corridors"]),
]

SENTENCE_QUESTIONS = [
    _q(1, "sentence_completion", question_text="Complete the sentences. Use NO MORE THAN TWO WORDS.\n\n1. The transformation of cities through green spaces has been a theme for [1].\n2. Research links access to nature to lower [2].", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["decades", "stress"]),
    _q(2, "sentence_completion", question_text="Complete the sentences. Use ONE WORD ONLY.\n\n1. Critics point to the risk of [1].\n2. Property prices often [2] when parks are added.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["gentrification", "rise"]),
    _q(3, "sentence_completion", question_text="Complete the sentences. Use NO MORE THAN TWO WORDS.\n\n1. Urban green spaces can support a range of [1].\n2. The key is [2] between habitats.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["wildlife", "connectivity"]),
    _q(4, "sentence_completion", question_text="Complete the sentences. Use ONE WORD ONLY.\n\n1. Many cities rely on one-off [1].\n2. This can lead to [2] after initial planting.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["grants", "neglect"]),
    _q(5, "sentence_completion", question_text="Complete the sentences. Use NO MORE THAN TWO WORDS.\n\n1. Best practice includes [1] budgets.\n2. [2] can adopt sections of parkland.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["ring-fenced", "Schools"]),
    _q(6, "sentence_completion", question_text="Complete the sentences. Use ONE WORD ONLY.\n\n1. European cities have documented the return of the peregrine [1].\n2. Populations need to move and [2].", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["falcon", "mix"]),
    _q(7, "sentence_completion", question_text="Complete the sentences. Use NO MORE THAN TWO WORDS.\n\n1. Community involvement gives a sense of [1].\n2. The result is [2] social ties.", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["ownership", "stronger"]),
    _q(8, "sentence_completion", question_text="Complete the sentences. Use ONE WORD ONLY.\n\n1. Design should use [1] species where possible.\n2. The passage recommends a model for [2] development.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["native", "sustainable"]),
]

TABLE_QUESTIONS = [
    _q(1, "table_completion", question_text="Complete the table. Use NO MORE THAN TWO WORDS.\n\n| Paragraph | Main idea |\n| A | Wellbeing and [1] |\n| B | [2] and connectivity |\n| C | [3] and maintenance |", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["gentrification", "Biodiversity", "Funding"]),
    _q(2, "table_completion", question_text="Complete the table. Use ONE WORD ONLY.\n\n| Factor | Detail |\n| Distance | Within [1] metres |\n| Risk | [2] |\n| Key for wildlife | [3] |", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["500", "gentrification", "connectivity"]),
    _q(3, "table_completion", question_text="Complete the table. Use NO MORE THAN TWO WORDS.\n\n| Topic | Finding |\n| Research | Journal of [1] Ecology |\n| Species | e.g. peregrine [2] |\n| Practice | [3] and Melbourne |", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["Urban", "falcon", "Copenhagen"]),
    _q(4, "table_completion", question_text="Complete the table. Use ONE WORD ONLY.\n\n| Funding type | Problem |\n| One-off [1] | Neglect later |\n| Solution | [2]-fenced budgets |\n| Role | [3] involvement |", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["grants", "ring", "community"]),
    _q(5, "table_completion", question_text="Complete the table. Use NO MORE THAN TWO WORDS.\n\n| Actor | Role |\n| Municipal [1] | Invest in parks |\n| Schools / groups | [2] parkland |\n| Result | Stronger [3] ties |", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["authorities", "adopt", "social"]),
    _q(6, "table_completion", question_text="Complete the table. Use ONE WORD ONLY.\n\n| Paragraph A | Paragraph B | Paragraph C |\n| [1] | Wildlife | [2] |\n| displacement | connectivity | [3] |", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Gentrification", "Biodiversity", "Funding"]),
    _q(7, "table_completion", question_text="Complete the table. Use NO MORE THAN TWO WORDS.\n\n| Element | Description |\n| Green [1] | Link parks and gardens |\n| Design | [2] species |\n| Outcome | [3] development |", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["corridors", "native", "sustainable"]),
    _q(8, "table_completion", question_text="Complete the table. Use ONE WORD ONLY.\n\n| Cities | Focus |\n| London, Singapore | [1] in green space |\n| European | [2] return |\n| Copenhagen, Melbourne | [3] practice |", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Investment", "species", "best"]),
]

SHORT_ANSWER_QUESTIONS = [
    _q(1, "short_answer", question_text="Answer in NO MORE THAN THREE WORDS.\n\nWhat is linked to lower stress and higher wellbeing? [1]", options_json={"part": 1, "instruction": "NO MORE THAN THREE WORDS"}, correct_answer_json=["Access to nature"]),
    _q(2, "short_answer", question_text="Answer in NO MORE THAN TWO WORDS.\n\nWhat risk do critics associate with new parks? [1]", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["Gentrification"]),
    _q(3, "short_answer", question_text="Answer in ONE WORD ONLY.\n\nWhat do ecologists say is key for wildlife in cities? [1]", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["connectivity"]),
    _q(4, "short_answer", question_text="Answer in NO MORE THAN THREE WORDS.\n\nWhich bird is mentioned as returning to European cities? [1]", options_json={"part": 1, "instruction": "NO MORE THAN THREE WORDS"}, correct_answer_json=["peregrine falcon"]),
    _q(5, "short_answer", question_text="Answer in NO MORE THAN TWO WORDS.\n\nWhat can follow impressive initial planting when funding is one-off? [1]", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["neglect"]),
    _q(6, "short_answer", question_text="Answer in NO MORE THAN TWO WORDS.\n\nWhich two cities are given as best-practice examples? [1] and [2]", options_json={"part": 1, "instruction": "NO MORE THAN TWO WORDS"}, correct_answer_json=["Copenhagen", "Melbourne"]),
    _q(7, "short_answer", question_text="Answer in ONE WORD ONLY.\n\nWho can adopt sections of parkland? [1] and local groups.", options_json={"part": 1, "instruction": "ONE WORD ONLY"}, correct_answer_json=["Schools"]),
    _q(8, "short_answer", question_text="Answer in NO MORE THAN THREE WORDS.\n\nIn which journal is the research on wellbeing and nature published? [1]", options_json={"part": 1, "instruction": "NO MORE THAN THREE WORDS"}, correct_answer_json=["Journal of Urban Ecology"]),
]

# ——— Essay: 2 ta (Task 1, Task 2) ———
ESSAY_QUESTIONS = [
    _q(1, "essay", question_text="Task 1 (Academic): The graph below shows the percentage of households in owned and rented accommodation in England and Wales between 1918 and 2011. Summarise the information by selecting and reporting the main features, and make comparisons where relevant. Write at least 150 words.", options_json={"part": 1}, correct_answer_json=[]),
    _q(2, "essay", question_text="Task 2: Some people believe that urban green spaces are essential for the wellbeing of city residents and should be prioritised in planning. Others think that housing and transport are more important. Discuss both views and give your own opinion. Write at least 250 words.", options_json={"part": 2}, correct_answer_json=[]),
]

# ——— Matching: 8 ta (har biri 3–5 item) ———
def _matching_headings_q(order):
    items = [{"num": i, "label": f"Paragraph {chr(64+i)}"} for i in range(1, 6)]
    headings = [{"letter": chr(105+i), "text": h} for i, h in enumerate(["Introduction", "Benefits and concerns", "Biodiversity", "Funding and practice", "Conclusion"])]
    return _q(order, "matching_headings", options_json={"part": 1, "items": items, "headings": headings}, question_text="Choose the correct heading (i–v) for each paragraph (A–E).\n\ni Introduction\nii Benefits and concerns\niii Biodiversity\niv Funding and practice\nv Conclusion\n\nA–E: Paragraphs A to E.", correct_answer_json={"1": "i", "2": "ii", "3": "iii", "4": "iv", "5": "v"})
MATCHING_HEADINGS_QUESTIONS = [_matching_headings_q(i) for i in range(1, 9)]

def _matching_sentences_q(order):
    items = [{"num": 1, "label": "The passage states that..."}, {"num": 2, "label": "According to ecologists..."}, {"num": 3, "label": "Best practice involves..."}]
    options = [{"letter": "A", "text": "access to nature is linked to wellbeing."}, {"letter": "B", "text": "connectivity between green areas is key."}, {"letter": "C", "text": "ring-fenced budgets and community involvement."}]
    return _q(order, "matching_sentences", options_json={"part": 1, "items": items, "options": options}, question_text="Match the sentence endings (A–C) to the beginnings (1–3).\n\n1. The passage states that...\n2. According to ecologists...\n3. Best practice involves...\n\nA. ...access to nature is linked to wellbeing.\nB. ...connectivity between green areas is key.\nC. ...ring-fenced budgets and community involvement.", correct_answer_json={"1": "A", "2": "B", "3": "C"})
MATCHING_SENTENCES_QUESTIONS = [_matching_sentences_q(i) for i in range(1, 9)]

def _matching_features_q(order):
    items = [{"num": 15, "label": "Link between nature and wellbeing"}, {"num": 16, "label": "Importance of connectivity"}, {"num": 17, "label": "Best practice cities"}]
    options = [{"letter": "A", "text": "Paragraph A"}, {"letter": "B", "text": "Paragraph B"}, {"letter": "C", "text": "Paragraph C"}]
    return _q(order, "matching_features", options_json={"part": 1, "items": items, "options": options}, question_text="Which paragraph (A–C) does each idea (15–17) refer to? Write the correct letter.\n\n15. Link between nature and wellbeing\n16. Importance of connectivity\n17. Best practice cities", correct_answer_json={"15": "A", "16": "B", "17": "C"})
MATCHING_FEATURES_QUESTIONS = [_matching_features_q(i) for i in range(1, 9)]

def _matching_info_q(order):
    items = [{"num": 18, "label": "A concern about new parks"}, {"num": 19, "label": "Wildlife and connectivity"}, {"num": 20, "label": "Funding and community"}]
    options = [{"letter": "A", "text": "Paragraph A"}, {"letter": "B", "text": "Paragraph B"}, {"letter": "C", "text": "Paragraph C"}]
    return _q(order, "matching_info", options_json={"part": 1, "items": items, "options": options}, question_text="Which paragraph (A–C) contains the following? Write the correct letter.\n\n18. A concern about new parks\n19. Wildlife and connectivity\n20. Funding and community", correct_answer_json={"18": "A", "19": "B", "20": "C"})
MATCHING_INFO_QUESTIONS = [_matching_info_q(i) for i in range(1, 9)]

def _classification_q(order):
    items = [{"num": 21, "label": "Wellbeing linked to nature"}, {"num": 22, "label": "Gentrification"}, {"num": 23, "label": "Community involvement"}]
    options = [{"letter": "A", "text": "positive"}, {"letter": "B", "text": "negative"}, {"letter": "C", "text": "neutral / mixed"}]
    return _q(order, "classification", options_json={"part": 1, "items": items, "options": options}, question_text="Classify the following (21–23) as A (positive), B (negative), or C (neutral/mixed).\n\n21. Wellbeing linked to nature\n22. Gentrification\n23. Community involvement", correct_answer_json={"21": "A", "22": "B", "23": "A"})
CLASSIFICATION_QUESTIONS = [_classification_q(i) for i in range(1, 9)]

def _list_selection_q(order):
    return _q(order, "list_selection", options_json={"part": 1, "instruction": "Choose TWO", "options": [{"letter": "A", "text": "Wellbeing"}, {"letter": "B", "text": "Biodiversity"}, {"letter": "C", "text": "Funding"}, {"letter": "D", "text": "Community"}, {"letter": "E", "text": "Gentrification"}]}, question_text="Choose TWO letters, A–E. Which TWO are mentioned as benefits or positive outcomes of urban green spaces?\n\nA Wellbeing  B Biodiversity  C Funding  D Community  E Gentrification", correct_answer_json=["A", "D"])
LIST_SELECTION_QUESTIONS = [_list_selection_q(i) for i in range(1, 9)]

# ——— Konfiguratsiya: har bir tur uchun 8 ta savol (essay 2 ta) ———
QUESTION_TYPE_CONFIG = [
    ("mcq", "Multiple Choice (A/B/C/D)", "reading", MCQ_QUESTIONS),
    ("true_false", "True / False", "reading", TF_QUESTIONS),
    ("true_false_not_given", "True / False / Not Given (Reading)", "reading", TFNG_QUESTIONS),
    ("yes_no_not_given", "Yes / No / Not Given", "reading", YNNG_QUESTIONS),
    ("fill_blank", "Bo'sh joyni to'ldirish", "reading", FILL_BLANK_QUESTIONS),
    ("summary_completion", "Summary Completion (Reading)", "reading", SUMMARY_QUESTIONS),
    ("notes_completion", "Notes Completion (Listening)", "listening", NOTES_QUESTIONS),
    ("sentence_completion", "Sentence Completion", "reading", SENTENCE_QUESTIONS),
    ("table_completion", "Table Completion", "reading", TABLE_QUESTIONS),
    ("short_answer", "Qisqa javob", "reading", SHORT_ANSWER_QUESTIONS),
    ("essay", "Essay (Writing Task)", "writing", ESSAY_QUESTIONS),
    ("matching_headings", "Matching Headings", "reading", MATCHING_HEADINGS_QUESTIONS),
    ("matching_sentences", "Matching Sentence Endings", "reading", MATCHING_SENTENCES_QUESTIONS),
    ("matching_features", "Matching Features", "reading", MATCHING_FEATURES_QUESTIONS),
    ("matching_info", "Matching Information", "reading", MATCHING_INFO_QUESTIONS),
    ("classification", "Classification", "reading", CLASSIFICATION_QUESTIONS),
    ("list_selection", "List Selection (Choose TWO)", "listening", LIST_SELECTION_QUESTIONS),
]

# IELTS-style professional passage (~400 so'z) — Reading testlar uchun
SAMPLE_PASSAGE = """The Rise of Urban Green Spaces

A. The transformation of cities through the deliberate introduction of green spaces has become a central theme in urban planning over the past two decades. Municipal authorities from London to Singapore have invested heavily in parks, rooftop gardens, and linear corridors of vegetation along rivers and former industrial sites. Research published in the Journal of Urban Ecology suggests that access to nature within 500 metres of one's home is associated with lower stress levels and higher self-reported wellbeing. Critics, however, point to the risk of gentrification: when neighbourhoods gain new parks, property prices often rise, displacing long-term residents.

B. A second strand of evidence concerns biodiversity. Urban green spaces, when designed with native species and varied habitats, can support a surprising range of wildlife. Studies conducted in European cities have documented the return of species such as the peregrine falcon and various pollinators in areas where planting schemes and nesting sites were introduced. The key, according to ecologists, is connectivity—linking parks and gardens through green corridors so that populations can move and mix rather than remaining isolated in small patches.

C. Funding and long-term maintenance remain challenging. Many cities rely on one-off grants or developer contributions, which can lead to impressive initial planting followed by neglect. Best practice, as seen in cities like Copenhagen and Melbourne, involves ring-fenced budgets and community involvement in both design and upkeep. Schools and local groups often adopt sections of parkland, providing labour and a sense of ownership. The result is not only greener cities but also stronger social ties and a clearer model for sustainable urban development in the future."""


class Command(BaseCommand):
    help = "Bazadagi barcha testlarni o'chiradi va har bir savol turi bo'yicha bittadan namuna test yaratadi."

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-delete",
            action="store_true",
            help="Mavjud testlarni o'chirmasdan faqat yangi namuna testlarni qo'shadi (agar test yo'q bo'lsa).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        no_delete = options.get("no_delete", False)

        # 1) Kategoriya (faqat admin da ko'rinadi, interfeysda emas)
        category, created = Category.objects.get_or_create(
            slug="namuna",
            defaults={
                "name": "Namuna (savol turlari)",
                "description": "Har bir savol turi bo'yicha bittadan namuna test. Keyinchalik bularga qarab yangi test yarating.",
                "icon": "fas fa-layer-group",
                "color": "#6366f1",
                "order": 0,
                "is_active": True,
                "show_on_site": False,
            },
        )
        if not created and getattr(category, "show_on_site", True):
            category.show_on_site = False
            category.save(update_fields=["show_on_site"])
        self.stdout.write(f"Kategoriya: {category.name} (faqat admin)")

        # 2) Barcha testlarni o'chirish
        if not no_delete:
            deleted_count = Test.objects.count()
            Test.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"O'chirildi: {deleted_count} ta test (savollar va passage'lar ham ketdi)."))
        else:
            self.stdout.write("Mavjud testlar saqlanadi (--no-delete).")

        created = 0
        skipped = 0

        for qt_key, qt_label, test_type, questions_data in QUESTION_TYPE_CONFIG:
            title = f"Namuna: {qt_label}"
            if no_delete and Test.objects.filter(category=category, title=title).exists():
                skipped += 1
                continue
            test = Test.objects.create(
                category=category,
                title=title,
                test_type=test_type,
                difficulty="medium",
                description=f"Bu test «{qt_label}» savol turi uchun namuna. Admin da shu testga o'xshab yangi test yarating.",
                duration_minutes=60 if test_type != "writing" else 60,
                passing_score=60,
                allow_retake=True,
                is_active=True,
            )

            if test_type == "reading":
                ReadingPassage.objects.create(test=test, order=1, title="Part 1", text=SAMPLE_PASSAGE)

            for q_data in questions_data:
                order = q_data.pop("order")
                Question.objects.create(
                    test=test,
                    order=order,
                    question_type=q_data.get("question_type", qt_key),
                    question_text=q_data.get("question_text", ""),
                    option_a=q_data.get("option_a", ""),
                    option_b=q_data.get("option_b", ""),
                    option_c=q_data.get("option_c", ""),
                    option_d=q_data.get("option_d", ""),
                    correct_answer=q_data.get("correct_answer", ""),
                    options_json=q_data.get("options_json", {}),
                    correct_answer_json=q_data.get("correct_answer_json", []),
                    points=1,
                )

            created += 1
            self.stdout.write(f"  + {title} ({test_type})")

        self.stdout.write(self.style.SUCCESS(f"Yakunlandi: {created} ta yangi test."))
        if skipped:
            self.stdout.write(self.style.NOTICE(f"Qoldirildi (mavjud): {skipped} ta."))
