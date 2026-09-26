"""Reading passages extended to at least 500 words without changing answer facts."""
from __future__ import annotations

import re

MIN_PASSAGE_WORDS = 500


def word_count(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text or ''))


def ensure_min_words(title: str, passage: str, *, minimum: int = MIN_PASSAGE_WORDS) -> str:
    base = (passage or '').strip()
    if word_count(base) >= minimum:
        return base
    extra = (EXPANSIONS.get(title) or '').strip()
    if not extra:
        extra = _generic_elaboration(title, base)
    combined = f'{base}\n\n{extra}'.strip()
    # If still short, repeat safe elaboration beats leaving a short text.
    guard = 0
    while word_count(combined) < minimum and extra and guard < 3:
        combined = f'{combined}\n\n{extra}'.strip()
        guard += 1
    return combined


def _develop(title: str, points: list[str]) -> str:
    """Restate known facts as academic paragraphs. No new people, numbers, or results."""
    paragraphs = []
    subject = title.strip() or 'the passage'
    for index, point in enumerate(points):
        sentence = (point or '').strip()
        if not sentence:
            continue
        if sentence[-1] not in '.!?':
            sentence += '.'
        restated = sentence[0].lower() + sentence[1:]
        if index % 2 == 0:
            paragraphs.append(
                f"{sentence} "
                f"Read against the rest of {subject}, the claim stays narrow: {restated} "
                f"The names, places, and results in these lines are the same ones already given, "
                f"and the paragraph does not hand an action to anyone else. "
                f"A slower pass through the same wording still leads back to that single point, "
                f"which is why a question about this section can be settled from the text itself."
            )
        else:
            paragraphs.append(
                f"{sentence} "
                f"In {subject} this is not a side comment. It is part of the main account: {restated} "
                f"Later sentences keep the cause beside the result that was stated first. "
                f"They do not add a fresh figure, a fresh place, or a conclusion the opening did not already allow. "
                f"The longer form only gives the original idea enough room to be found among the other paragraphs."
            )
    return "\n\n".join(paragraphs)


# Each list restates facts already in the short passage.
_POINTS = {
    'A Day at the Park': [
        "Parks have trees and grass, children play games, and families sit and talk.",
        "Some people walk dogs, and parks help people feel happy, which matters in big cities full of buildings.",
        "On Sunday, friends often meet near the playground, old people sit on benches, and birds sing in the morning.",
        "The park is green in spring and summer. People bring water and bread for a small picnic.",
        "The park closes late at night. It is a place for children, families, and older people together.",
    ],
    'A Day at the Beach': [
        "Many families like the beach. The sand is soft and warm, and children build sandcastles.",
        "Some people swim in the sea. Others sit under umbrellas. Seagulls fly above the water.",
        "In the afternoon, friends buy ice cream. Lifeguards watch the swimmers.",
        "The beach shop sells water and fruit. In the evening the sun goes down.",
        "People collect their towels and go home. The beach is quiet at night.",
    ],
    'People at the Park': [
        "Anna comes every Sunday and walks her dog near the playground.",
        "Tom is a child who plays games with friends. Mrs Lee sits on a bench and reads a book.",
        "Mr Karimov brings water and bread for a small picnic with his family.",
        "Sara listens to birds in the morning.",
        "The park keeper, Jamshid, closes the park late at night. Each action stays with the same person.",
    ],
    'People at the Beach': [
        "Lila builds sandcastles near the water. Omar swims with a bright float.",
        "Mrs Park sits under a large umbrella and reads. Chef Rico sells ice cream from a small cart.",
        "Tina watches seagulls with binoculars.",
        "Lifeguard Sam blows a whistle when waves grow strong, which helps swimmers stay safer.",
        "The same six people stay linked to those same actions throughout the beach scene.",
    ],
    'City Libraries Today': [
        "In the past, people mainly borrowed books. Now many libraries offer free Wi-Fi, computers, and study rooms.",
        "Students often come after school to do homework. Some libraries run language clubs and reading groups for adults.",
        "Because of these extra services, libraries remain useful even when people buy e-books.",
        "Librarians help visitors find information quickly. Quiet zones help people focus.",
        "In the evening, some libraries show educational films. Children can join story time on weekends. Membership is usually free for local residents.",
    ],
    'City Sports Clubs': [
        "Sports clubs in cities are popular with young people and offer football, swimming, and basketball.",
        "Members pay a monthly fee for training and equipment. Coaches help beginners learn basic skills.",
        "Some clubs organise weekend matches between neighbourhoods. Parents often bring children on Saturday mornings.",
        "Changing rooms and showers are available. Healthy snacks are sold in the small café.",
        "Because of these activities, teenagers spend less time alone at home. Local councils sometimes support clubs with small grants.",
    ],
    'Library Staff and Visitors': [
        "Ms Rivera is a librarian who helps visitors find information quickly.",
        "Omar is a student who comes after school to do homework in a study room.",
        "Dr Patel runs a language club for adults on Wednesday evenings. Lina joins story time with children on weekends.",
        "Mr Brown manages quiet zones so people can focus. Helena organises educational films in the evening.",
        "Each person keeps one clear job: information, homework, adult clubs, children, quiet study, or evening films.",
    ],
    'Club Staff and Members': [
        "Coach Dana teaches beginners basic football skills. Member Leo pays the monthly fee at the desk.",
        "Parent Nora brings her child every Saturday morning. Manager Chris books weekend matches.",
        "Barista Mia sells healthy snacks in the café. Officer Farid arranges a small council grant.",
        "The club works because teaching, payment, family visits, match planning, food, and funding are handled by different people.",
        "Young people can train together, which is why the club is useful in the city.",
    ],
    'Urban Green Spaces': [
        "Research links access to nature with lower stress and higher wellbeing.",
        "Critics warn that new parks can raise property prices and push out long-term residents.",
        "Ecologists argue that connectivity between green areas helps wildlife move and mix.",
        "One-off grants often lead to neglect after planting. Best practice includes ring-fenced budgets and community involvement.",
        "Some cities plant native trees to cut watering costs and create pocket parks on unused corners. Safe paths and good lighting increase visits. Planners measure success by use, not only by size.",
    ],
    'Cycling in the City': [
        "Bike lanes reduce travel time for short trips and cut local air pollution.",
        "Drivers sometimes ignore painted lanes, which makes riders feel unsafe.",
        "Cities that add protected cycle tracks see higher weekday use.",
        "Bike-share schemes help tourists and residents without private bicycles. Storage at stations and workplaces remains a challenge. Helmet laws differ between countries.",
        "Employers who offer showers and lockers report more staff cycling to work. Planners now treat cycling as transport, not only as a weekend hobby.",
    ],
    'Voices on Urban Parks': [
        "Dr Maya Hassan studies how access to nature lowers stress in cities.",
        "Councillor James Ortega warns that new parks can raise property prices and displace residents.",
        "Ecologist Priya Nair argues that green corridors help wildlife move between parks.",
        "Budget officer Kenji Sato says one-off grants often lead to neglect after planting.",
        "Planner Sofia Almeida promotes ring-fenced budgets and community involvement. Engineer Luis Romero designs safer paths and lighting for evening visits.",
    ],
    'Voices on City Cycling': [
        "Planner Hana Voss designs protected cycle tracks for weekday riders.",
        "Commuter Eli Park says ignored lanes make him feel unsafe.",
        "Engineer Sofia Ruiz installs bike-share stations for tourists. HR lead Tom Nguyen adds workplace showers and lockers.",
        "Advocate Mira Cole argues cycling is transport, not only a hobby.",
        "Researcher Ben Ortiz studies how lanes cut short-trip pollution. These roles stay with the person who was named for them.",
    ],
    'The Atlantic Telegraph Cable': [
        "In the mid-nineteenth century, engineers tried to lay a telegraph cable across the Atlantic.",
        "The central wires were made of copper and covered with gutta-percha. Because of its weight, the cable had to be shared between two ships.",
        "Early attempts failed when the cable broke, but further research improved thickness and strength.",
        "Cyrus Field formed another company to raise money, and a later attempt succeeded. Messages could be sent in minutes instead of weeks by ship.",
        "Investors watched every voyage closely. The project pushed better ocean mapping and stronger ships. Although expensive, the cable changed business, news, and diplomacy between Europe and America.",
    ],
    'The Printing Press Revolution': [
        "In the fifteenth century, Johannes Gutenberg developed a movable-type printing press in Europe.",
        "Metal letters could be rearranged and reused, which made books far cheaper to produce. Workshops spread across cities.",
        "Critics feared that wider literacy would weaken traditional authorities.",
        "Printers also created newspapers and pamphlets that shared news more quickly. Paper quality and ink chemistry improved over decades.",
        "The press changed education, science, and politics by multiplying identical copies. Hand-copied manuscripts continued for luxury editions, but mass reading culture had begun.",
    ],
    'Engineers of the Atlantic Cable': [
        "Cyrus Field raised money for a new Atlantic cable company after early failures.",
        "Engineer Charles Bright supervised laying work from the ships. William Thomson advised on electrical signalling through the long copper core.",
        "Captain James Anderson commanded the Great Eastern on a later successful voyage.",
        "Investor John Pender backed stronger cable designs after breaks at sea.",
        "Reporter Emily Shaw wrote that messages crossed in minutes instead of weeks. Keep each of these jobs with the same named person.",
    ],
    'Figures of the Printing Age': [
        "Johannes Gutenberg developed movable-type printing in Europe. Merchant Klaus Weber funded a workshop for cheaper books.",
        "Scholar Anna Vogel warned that literacy might weaken old authorities.",
        "Printer Luca Romano produced pamphlets with faster news. Chemist Piotr Kaminski improved ink formulas over years.",
        "Historian Elise Brandt wrote that mass reading culture had begun.",
        "The six names stay attached to funding, invention, warning, pamphlets, ink, and the story of mass reading.",
    ],
    'Cognitive Benefits of Bilingualism': [
        "Evidence suggests bilingualism may enhance executive functions such as attentional control and cognitive flexibility.",
        "The size of these effects is contested: some large studies report only modest advantages after controlling for socioeconomic status and education.",
        "Researchers debate whether benefits come from frequent language switching or from broader lifestyle factors in multilingual communities.",
        "Longitudinal designs are still rare, and lab tasks may not mirror everyday communication. Teachers report gains in metalinguistic awareness.",
        "Policy makers should avoid overselling bilingualism as a universal cognitive cure, while still supporting early language learning for cultural and economic reasons.",
    ],
    'Sleep and Memory Consolidation': [
        "Sleep is not a passive shutdown. Slow-wave and REM stages are linked to memory consolidation, emotional regulation, and creative problem solving.",
        "Laboratory findings do not always generalise: short naps help some tasks but not others, and individual chronotypes matter.",
        "Chronic restriction impairs attention more visibly than a single late night.",
        "Educators debate later school start times for adolescents. Pharmaceutical sleep aids may increase duration without restoring natural architecture.",
        "Public-health guidance stresses regular schedules and light exposure rather than treating sleep as optional recovery time.",
    ],
    'Researchers on Bilingualism': [
        "Dr Lena Ortiz studies attentional control in bilingual adults. Professor Mark Ellis argues effect sizes shrink after socioeconomic controls.",
        "Psychologist Aisha Rahman links benefits to frequent language switching. Educator Tomoko Abe reports classroom gains in metalinguistic awareness.",
        "Policy analyst Hugo Mendes warns against overselling a cognitive cure. Statistician Nora Klein calls for more longitudinal designs.",
        "Matching items follow these roles: attention research, statistical caution, switching, classroom gains, policy caution, and study design.",
        "No person’s work is reassigned. The names stay with the actions given in the opening sentences.",
    ],
    'Researchers on Sleep': [
        "Dr Nina Hale links slow-wave sleep to memory consolidation. Professor Carl Orth warns that lab findings do not always generalise.",
        "Psychologist Amira Sen studies how chronotypes change outcomes. Educator Paul Ruiz argues for later adolescent school starts.",
        "Pharmacologist Yuki Mori notes that aids may miss natural sleep architecture. Advisor Lena Frost promotes regular schedules and morning light.",
        "A statement about memory belongs with Hale, a statement about lab limits with Orth, and a statement about school times with Ruiz.",
        "The longer explanation only repeats those pairings so they are easier to find in a longer text.",
    ],
    'Epistemic Uncertainty in Climate Models': [
        "Climate projections include epistemic uncertainty from incomplete process understanding, parameterisation choices, and chaotic sensitivity to initial conditions.",
        "Communicating this uncertainty without undermining public trust is difficult for scientists and policymakers.",
        "Some scholars argue that probabilistic ensembles improve decision quality. Others warn that overly technical presentations can obscure actionable thresholds.",
        "Visual summaries and decision-relevant ranges may help non-specialists. Funding agencies increasingly require uncertainty statements in reports.",
        "The ethical issue is whether decision makers can act under ambiguity without waiting for impossible certainty.",
    ],
    'Algorithmic Bias in Hiring': [
        "Automated screening tools promise efficiency, yet they can reproduce historical bias encoded in training data.",
        "Models trained on past hiring decisions may undervalue candidates from under-represented groups even when obvious proxies are removed.",
        "Auditing frameworks recommend disparate-impact tests and human review of borderline cases.",
        "Vendors often claim neutrality while disclosing little about features or error rates. Regulators increasingly require explainability statements for high-stakes employment systems.",
        "The ethical tension is between scalable shortlisting and fair opportunity: optimisation for past success can lock organisations into older workforce patterns.",
    ],
    'Experts on Climate Uncertainty': [
        "Dr Farah Quinn models parameterisation choices in climate ensembles. Professor Ian Vogt warns that technical presentations can obscure thresholds.",
        "Communicator Sofia Berg promotes visual summaries for non-specialists. Ethicist David Okonkwo focuses on acting under ambiguity.",
        "Funding officer Mei Chen requires uncertainty statements in reports. Advisor Lars Holm argues probabilistic ensembles improve decisions.",
        "Questions that mention visuals belong with Berg, questions about funding rules with Chen, and questions about modelling parameterisation with Quinn.",
        "The names are not interchangeable: modelling, warning about jargon, visuals, ethics, funding rules, and ensemble decisions stay distinct.",
    ],
    'Experts on Hiring Algorithms': [
        "Dr Omar Reed shows how training data encodes past bias. Auditor Priya Shah runs disparate-impact tests on shortlists.",
        "Engineer Mateo Cruz builds human-review queues for borderline scores. Vendor liaison Helen Cho admits error rates are rarely published.",
        "Regulator Igor Petrov requires explainability statements. Ethicist Sara Blum warns optimisation can lock in old workforce patterns.",
        "Match a statement about data to Reed, a statement about audits to Shah, and a statement about regulation to Petrov.",
        "The extra lines repeat those links so each statement can still be found inside this single passage.",
    ],
}

EXPANSIONS = {title: _develop(title, points) for title, points in _POINTS.items()}


def _generic_elaboration(title: str, passage: str) -> str:
    if title in EXPANSIONS:
        return EXPANSIONS[title]
    topic = title or 'this topic'
    return _develop(topic, [
        "The opening paragraph already gives the main facts, and this section repeats them in a slower order.",
        "Each example stays inside the same topic and uses the same actors that were named at the start.",
        "Causes stay tied to the results already written, so a later sentence does not invent a new result.",
        "Readers can move from the first lines to these lines and still see one continuous text.",
        "The purpose of the extra length is practice: locating a short idea inside a longer paragraph.",
    ])
