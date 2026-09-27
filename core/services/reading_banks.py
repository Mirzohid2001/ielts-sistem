"""Extra reading topics so a new click replaces the passage, not only the order of questions."""
from __future__ import annotations

# Each pack: real paragraphs plus 10 items the questions are built from.
# Only `true` statements are facts in the passage. false / ng must stay unsupported.

def _p(*parts: str) -> str:
    return ' '.join(part.strip() for part in parts if part and part.strip())


PACKS = {
    'A1': [
        {
            'title': 'A Morning at School',
            'names': ['Ms Lina', 'Omar', 'Teacher Dan', 'Noor', 'Mr Aziz', 'Sam'],
            'paragraphs': [
                _p(
                    "School starts at eight. Ms Lina meets the children at the door and says good morning.",
                    "The children put their bags in the classroom. Then they sit at their desks.",
                    "Omar opens his book and takes a pencil. Teacher Dan writes the date on the board.",
                ),
                _p(
                    "The first lesson is reading. The children read a short story about a red bus.",
                    "Noor asks a question, and Ms Lina answers in a kind voice.",
                    "After reading, they draw a picture of the bus. Sam uses a blue pencil for the sky.",
                ),
                _p(
                    "At ten they have a break. The children go outside and drink water.",
                    "Some children play with a ball. Mr Aziz watches them in the yard.",
                    "They do not buy food at school. They bring bread from home.",
                ),
                _p(
                    "After the break they sing a song. Teacher Dan plays a small drum.",
                    "The song is short and easy. All the children stand and clap.",
                    "Then they wash their hands and go back to class.",
                ),
                _p(
                    "The last lesson is numbers. Ms Lina shows three apples and the children count them.",
                    "School ends at twelve. Parents wait at the gate.",
                    "Omar waves to Ms Lina and walks home with his bag.",
                ),
            ],
            'items': [
                {'k': 'true', 's': 'School starts at eight.', 'g': ('School starts at ______.', 'eight'), 'q': 'When does school start?', 'a': 'At eight', 'bad': ['At noon', 'At night', 'On Sunday'], 'h': 'Start time', 'ho': 'School opens at eight', 'hb': ['A night market', 'A long holiday'], 'e0': 'School starts', 'e1': 'at eight.', 'who': 'Ms Lina', 'did': 'meets the children at the door'},
                {'k': 'true', 's': 'The first lesson is reading.', 'g': ('The first lesson is ______.', 'reading'), 'q': 'What is the first lesson?', 'a': 'Reading', 'bad': ['Swimming', 'Cooking', 'Driving'], 'h': 'First lesson', 'ho': 'A reading lesson', 'hb': ['A football match', 'A train trip'], 'e0': 'The first lesson is', 'e1': 'reading.', 'who': 'Teacher Dan', 'did': 'writes the date on the board'},
                {'k': 'true', 's': 'The children read a story about a red bus.', 'g': ('They read about a red ______.', 'bus'), 'q': 'What is the story about?', 'a': 'A red bus', 'bad': ['A green plane', 'A large ship', 'A hospital'], 'h': 'The story', 'ho': 'A story about a red bus', 'hb': ['A story about space', 'A story about banks'], 'e0': 'The story is about', 'e1': 'a red bus.', 'who': 'Omar', 'did': 'opens his book and takes a pencil'},
                {'k': 'false', 's': 'The children buy lunch at school.', 'g': ('They bring ______ from home.', 'bread'), 'q': 'What do the children bring from home?', 'a': 'Bread', 'bad': ['Tickets', 'Cars', 'Gold'], 'h': 'Food', 'ho': 'Bread from home', 'hb': ['A restaurant meal', 'Free pizza every day'], 'e0': 'They bring bread', 'e1': 'from home.', 'who': 'Noor', 'did': 'asks a question in the reading lesson'},
                {'k': 'true', 's': 'At ten the children have a break outside.', 'g': ('At ten they have a ______.', 'break'), 'q': 'Where do they go at break?', 'a': 'Outside', 'bad': ['To the airport', 'To a cinema', 'To a farm'], 'h': 'Break time', 'ho': 'A break at ten', 'hb': ['A night class', 'A winter exam'], 'e0': 'At ten they', 'e1': 'have a break.', 'who': 'Mr Aziz', 'did': 'watches the children in the yard'},
                {'k': 'ng', 's': 'The school has a swimming pool.', 'g': ('Some children play with a ______.', 'ball'), 'q': 'What do some children play with?', 'a': 'A ball', 'bad': ['A computer', 'A horse', 'A boat'], 'h': 'Play', 'ho': 'Play with a ball', 'hb': ['Play a piano exam', 'Drive a car'], 'e0': 'Some children play', 'e1': 'with a ball.', 'who': 'Sam', 'did': 'uses a blue pencil for the sky'},
                {'k': 'true', 's': 'Teacher Dan plays a small drum.', 'g': ('Teacher Dan plays a small ______.', 'drum'), 'q': 'What does Teacher Dan play?', 'a': 'A small drum', 'bad': ['A violin concert', 'A radio station', 'A film'], 'h': 'Music', 'ho': 'A short song and a drum', 'hb': ['A rock festival', 'A silent film'], 'e0': 'Teacher Dan plays', 'e1': 'a small drum.'},
                {'k': 'true', 's': 'The children count three apples.', 'g': ('Ms Lina shows three ______.', 'apples'), 'q': 'What do the children count?', 'a': 'Three apples', 'bad': ['Ten cars', 'One star', 'Five ships'], 'h': 'Numbers', 'ho': 'Counting three apples', 'hb': ['Counting money', 'Counting planes'], 'e0': 'The children count', 'e1': 'three apples.'},
                {'k': 'false', 's': 'School ends at night.', 'g': ('School ends at ______.', 'twelve'), 'q': 'When does school end?', 'a': 'At twelve', 'bad': ['At midnight', 'At dawn', 'At nine in the evening'], 'h': 'Home time', 'ho': 'School ends at twelve', 'hb': ['School ends at night', 'School never ends'], 'e0': 'School ends', 'e1': 'at twelve.'},
                {'k': 'true', 's': 'Parents wait at the gate.', 'g': ('Parents wait at the ______.', 'gate'), 'q': 'Where do parents wait?', 'a': 'At the gate', 'bad': ['On a plane', 'In a bank', 'At a stadium'], 'h': 'Going home', 'ho': 'Parents at the gate', 'hb': ['Parents at the airport', 'Parents on a ship'], 'e0': 'Parents wait', 'e1': 'at the gate.'},
            ],
        },
        {
            'title': 'The Corner Shop',
            'names': ['Mrs Kana', 'Ali', 'Bobo', 'Lela', 'Ravi', 'Aunt Mina'],
            'paragraphs': [
                _p(
                    "The corner shop opens at seven. Mrs Kana puts bread and milk on the table.",
                    "Ali buys milk every morning. He says thank you and walks to school.",
                    "Bobo sits near the door and drinks tea from a small cup.",
                ),
                _p(
                    "The shop sells apples, eggs, and rice. It does not sell shoes.",
                    "Lela likes red apples. She pays with coins and puts the apples in a bag.",
                    "Ravi helps Mrs Kana when the shop is busy. He carries boxes to the shelf.",
                ),
                _p(
                    "At noon many people come in. They buy bread for lunch.",
                    "Aunt Mina buys rice on Friday. She talks to Mrs Kana about the warm weather.",
                    "The radio in the shop plays quiet music. Nobody dances there.",
                ),
                _p(
                    "In the afternoon the shop is quiet. Mrs Kana writes prices on small cards.",
                    "An egg costs less than a bag of rice. A child can buy one apple.",
                    "Ali sometimes comes back after school for bread.",
                ),
                _p(
                    "The shop closes at six. Mrs Kana locks the door and turns off the light.",
                    "Bobo goes home along the same street. The shop is dark at night.",
                    "Tomorrow morning the shop will open again at seven.",
                ),
            ],
            'items': [
                {'k': 'true', 's': 'The corner shop opens at seven.', 'g': ('The shop opens at ______.', 'seven'), 'q': 'When does the shop open?', 'a': 'At seven', 'bad': ['At midnight', 'At noon only', 'On Monday night'], 'h': 'Opening', 'ho': 'The shop opens at seven', 'hb': ['The shop never opens', 'A night cinema'], 'e0': 'The shop opens', 'e1': 'at seven.', 'who': 'Mrs Kana', 'did': 'puts bread and milk on the table'},
                {'k': 'true', 's': 'Ali buys milk every morning.', 'g': ('Ali buys ______ every morning.', 'milk'), 'q': 'What does Ali buy every morning?', 'a': 'Milk', 'bad': ['A ticket', 'A bicycle', 'A computer'], 'h': 'Morning customer', 'ho': 'Ali buys milk', 'hb': ['Ali buys a car', 'Ali flies away'], 'e0': 'Ali buys milk', 'e1': 'every morning.', 'who': 'Ali', 'did': 'buys milk every morning'},
                {'k': 'false', 's': 'The shop sells shoes.', 'g': ('The shop sells apples, eggs, and ______.', 'rice'), 'q': 'Which foods does the shop sell?', 'a': 'Apples, eggs, and rice', 'bad': ['Cars and planes', 'Only gold', 'Ships and trains'], 'h': 'Goods', 'ho': 'Apples, eggs, and rice', 'hb': ['Shoes and coats', 'Tickets to space'], 'e0': 'The shop sells', 'e1': 'apples, eggs, and rice.', 'who': 'Bobo', 'did': 'drinks tea near the door'},
                {'k': 'true', 's': 'Lela pays with coins.', 'g': ('Lela pays with ______.', 'coins'), 'q': 'How does Lela pay?', 'a': 'With coins', 'bad': ['With a credit card only', 'With gold bars', 'She never pays'], 'h': 'Paying', 'ho': 'Payment with coins', 'hb': ['Payment by ship', 'A free market forever'], 'e0': 'Lela pays', 'e1': 'with coins.', 'who': 'Lela', 'did': 'buys red apples'},
                {'k': 'true', 's': 'At noon people buy bread.', 'g': ('At noon people buy ______.', 'bread'), 'q': 'What do people buy at noon?', 'a': 'Bread', 'bad': ['Houses', 'Planes', 'Forests'], 'h': 'Lunch time', 'ho': 'Bread at noon', 'hb': ['A concert at noon', 'A factory tour'], 'e0': 'At noon people buy', 'e1': 'bread.', 'who': 'Ravi', 'did': 'carries boxes to the shelf'},
                {'k': 'ng', 's': 'The shop is one hundred years old.', 'g': ('Aunt Mina buys rice on ______.', 'Friday'), 'q': 'When does Aunt Mina buy rice?', 'a': 'On Friday', 'bad': ['Every night', 'In January only', 'Never'], 'h': 'Friday rice', 'ho': 'Aunt Mina buys rice', 'hb': ['Aunt Mina sells cars', 'A closed shop'], 'e0': 'Aunt Mina buys rice', 'e1': 'on Friday.', 'who': 'Aunt Mina', 'did': 'buys rice on Friday'},
                {'k': 'true', 's': 'An egg costs less than a bag of rice.', 'g': ('An egg costs less than a bag of ______.', 'rice'), 'q': 'What costs more than an egg?', 'a': 'A bag of rice', 'bad': ['A drop of water', 'Nothing at all', 'A free smile'], 'h': 'Prices', 'ho': 'Rice costs more than an egg', 'hb': ['Everything is free', 'Eggs cost more than houses'], 'e0': 'An egg costs less than', 'e1': 'a bag of rice.'},
                {'k': 'false', 's': 'People dance in the shop.', 'g': ('The radio plays quiet ______.', 'music'), 'q': 'What does the radio play?', 'a': 'Quiet music', 'bad': ['News about space only', 'Nothing', 'A film'], 'h': 'Sound', 'ho': 'Quiet music on the radio', 'hb': ['A dance hall', 'A silent shop always'], 'e0': 'The radio plays', 'e1': 'quiet music.'},
                {'k': 'true', 's': 'The shop closes at six.', 'g': ('The shop closes at ______.', 'six'), 'q': 'When does the shop close?', 'a': 'At six', 'bad': ['At dawn', 'It never closes', 'At midnight only'], 'h': 'Closing', 'ho': 'The shop closes at six', 'hb': ['The shop stays open all night', 'The shop closes at noon'], 'e0': 'The shop closes', 'e1': 'at six.'},
                {'k': 'true', 's': 'The shop is dark at night.', 'g': ('Mrs Kana turns off the ______.', 'light'), 'q': 'What does Mrs Kana turn off?', 'a': 'The light', 'bad': ['The river', 'The city', 'The sun'], 'h': 'Night', 'ho': 'A dark shop at night', 'hb': ['A bright stadium', 'An open airport'], 'e0': 'The shop is dark', 'e1': 'at night.'},
            ],
        },
    ],
    'A2': [
        {
            'title': 'A Bus Ride to Work',
            'names': ['Karim', 'Driver Helena', 'Sara', 'Mr Cole', 'Ina', 'Ben'],
            'paragraphs': [
                _p(
                    "Karim takes the number 12 bus to work because his office is far from home.",
                    "The bus stop is next to a bakery. He usually arrives there at half past seven.",
                    "Driver Helena opens the door and checks the cards. A single ticket costs one coin.",
                ),
                _p(
                    "Sara sits near the window and reads messages on her phone.",
                    "Mr Cole stands when the bus is full. He holds the rail so he does not fall.",
                    "The journey takes about twenty-five minutes when the road is clear.",
                ),
                _p(
                    "Ina gets off at the hospital stop. She works there as a nurse.",
                    "Ben gets off near the market and buys a newspaper before his shop opens.",
                    "Karim stays on the bus until the last stop by the river office.",
                ),
                _p(
                    "On rainy days the bus is slower because cars move carefully.",
                    "The company does not give free coffee. Passengers bring their own water.",
                    "If Karim misses this bus, the next one comes fifteen minutes later.",
                ),
                _p(
                    "In the evening he takes the same bus home. The seats are more crowded then.",
                    "Driver Helena finishes her shift at six. Another driver takes the night route.",
                    "Karim likes the bus because it is cheaper than a taxi.",
                ),
            ],
            'items': [
                {'k': 'true', 's': 'Karim takes the number 12 bus to work.', 'g': ('He takes the number ______ bus.', '12|twelve'), 'q': 'Which bus does Karim take?', 'a': 'The number 12', 'bad': ['A night train', 'A plane', 'A boat'], 'h': 'The commute', 'ho': 'Bus number 12', 'hb': ['A private helicopter', 'Walking only'], 'e0': 'Karim takes', 'e1': 'the number 12 bus.', 'who': 'Karim', 'did': 'travels to an office by the river'},
                {'k': 'true', 's': 'The bus stop is next to a bakery.', 'g': ('The stop is next to a ______.', 'bakery'), 'q': 'What is next to the bus stop?', 'a': 'A bakery', 'bad': ['An airport', 'A forest', 'A stadium'], 'h': 'The stop', 'ho': 'A stop beside a bakery', 'hb': ['A stop at the beach', 'A stop underground forever'], 'e0': 'The bus stop is', 'e1': 'next to a bakery.', 'who': 'Driver Helena', 'did': 'checks the cards'},
                {'k': 'true', 's': 'A single ticket costs one coin.', 'g': ('A single ticket costs one ______.', 'coin'), 'q': 'How much is a single ticket?', 'a': 'One coin', 'bad': ['It is free for everyone forever', 'One house', 'Nothing is sold'], 'h': 'Fares', 'ho': 'One coin for a ticket', 'hb': ['Tickets cost a car', 'No tickets exist'], 'e0': 'A single ticket costs', 'e1': 'one coin.', 'who': 'Sara', 'did': 'reads messages by the window'},
                {'k': 'false', 's': 'The journey always takes two hours.', 'g': ('The journey takes about twenty-five ______.', 'minutes'), 'q': 'How long is the journey when the road is clear?', 'a': 'About twenty-five minutes', 'bad': ['Two days', 'One minute', 'A whole week'], 'h': 'Journey time', 'ho': 'About twenty-five minutes', 'hb': ['Two hours every day', 'An overnight trip'], 'e0': 'The journey takes about', 'e1': 'twenty-five minutes.', 'who': 'Mr Cole', 'did': 'stands and holds the rail'},
                {'k': 'true', 's': 'Ina gets off at the hospital.', 'g': ('Ina works as a ______.', 'nurse'), 'q': 'Where does Ina get off?', 'a': 'At the hospital', 'bad': ['At the airport', 'At a farm', 'She never gets off'], 'h': 'Ina’s stop', 'ho': 'The hospital stop', 'hb': ['The port', 'The palace'], 'e0': 'Ina gets off', 'e1': 'at the hospital.', 'who': 'Ina', 'did': 'gets off at the hospital'},
                {'k': 'ng', 's': 'The bus was built in Germany.', 'g': ('Ben buys a ______ before work.', 'newspaper'), 'q': 'What does Ben buy?', 'a': 'A newspaper', 'bad': ['A horse', 'A piano', 'A boat'], 'h': 'Ben’s morning', 'ho': 'A newspaper near the market', 'hb': ['A passport office', 'A free lunch for all'], 'e0': 'Ben buys', 'e1': 'a newspaper.', 'who': 'Ben', 'did': 'buys a newspaper near the market'},
                {'k': 'true', 's': 'Rain makes the bus slower.', 'g': ('On rainy days the bus is ______.', 'slower'), 'q': 'What happens on rainy days?', 'a': 'The bus is slower', 'bad': ['The bus flies', 'The road disappears', 'Tickets become free forever'], 'h': 'Bad weather', 'ho': 'A slower ride in the rain', 'hb': ['A faster race in the rain', 'No rain in the city'], 'e0': 'On rainy days the bus is', 'e1': 'slower.'},
                {'k': 'false', 's': 'The company gives free coffee.', 'g': ('Passengers bring their own ______.', 'water'), 'q': 'What do passengers bring?', 'a': 'Their own water', 'bad': ['Free coffee from the company', 'A meal cooked on the bus', 'Nothing at all'], 'h': 'Drinks', 'ho': 'Passengers bring water', 'hb': ['Free coffee for all', 'A bar on the bus'], 'e0': 'Passengers bring', 'e1': 'their own water.'},
                {'k': 'true', 's': 'The next bus comes fifteen minutes later.', 'g': ('The next bus comes fifteen ______ later.', 'minutes'), 'q': 'If Karim misses the bus, when is the next one?', 'a': 'Fifteen minutes later', 'bad': ['The next day only', 'One hour is never stated', 'Immediately with no wait'], 'h': 'The next bus', 'ho': 'A fifteen-minute wait', 'hb': ['No other bus exists', 'A wait of one day'], 'e0': 'The next bus comes', 'e1': 'fifteen minutes later.'},
                {'k': 'true', 's': 'The bus is cheaper than a taxi.', 'g': ('The bus is cheaper than a ______.', 'taxi'), 'q': 'Why does Karim like the bus?', 'a': 'It is cheaper than a taxi', 'bad': ['It is faster than a plane', 'It is free forever', 'It never stops'], 'h': 'Why the bus', 'ho': 'Cheaper than a taxi', 'hb': ['More expensive than a taxi', 'The only road in the country'], 'e0': 'The bus is cheaper than', 'e1': 'a taxi.'},
            ],
        },
        {
            'title': 'Saturday at the Market',
            'names': ['Farida', 'Chef Luis', 'Nika', 'Old Ken', 'Zara', 'Policeman Idris'],
            'paragraphs': [
                _p(
                    "The town market is open on Saturday from nine until two.",
                    "Farida sells fresh tomatoes, onions, and green herbs.",
                    "Chef Luis comes early because he needs vegetables for his kitchen.",
                ),
                _p(
                    "Nika has a small table with homemade jam. A jar costs two coins.",
                    "Old Ken repairs shoes at the end of the row. He does not sell fruit.",
                    "Zara plays a guitar between the stalls, but she does not sell tickets.",
                ),
                _p(
                    "At eleven the market is very busy. People speak loudly and laugh.",
                    "Policeman Idris walks through the rows so bags are safer.",
                    "There is no car park inside the market. Visitors leave cars in the street.",
                ),
                _p(
                    "Children can buy a small glass of juice. The juice is sweet and cold.",
                    "Farida gives a lower price if a customer buys three kilos of tomatoes.",
                    "The market does not stay open at night. At two the stalls close.",
                ),
                _p(
                    "After two, sellers pack boxes into vans. The square becomes quiet.",
                    "Chef Luis already has his bag and walks back to the restaurant.",
                    "Next Saturday the same sellers plan to return if the weather is dry.",
                ),
            ],
            'items': [
                {'k': 'true', 's': 'The market is open on Saturday from nine until two.', 'g': ('The market is open on ______.', 'Saturday'), 'q': 'Which day is the market open?', 'a': 'Saturday', 'bad': ['Every night', 'Only in winter exams', 'Never'], 'h': 'Market day', 'ho': 'Saturday from nine to two', 'hb': ['A night market', 'A Monday office'], 'e0': 'The market is open', 'e1': 'on Saturday.', 'who': 'Farida', 'did': 'sells tomatoes, onions, and herbs'},
                {'k': 'true', 's': 'Chef Luis needs vegetables for his kitchen.', 'g': ('Chef Luis needs ______.', 'vegetables'), 'q': 'What does Chef Luis need?', 'a': 'Vegetables', 'bad': ['Car engines', 'Plane tickets', 'Gold bars'], 'h': 'The chef', 'ho': 'Vegetables for a kitchen', 'hb': ['Fish from the ocean only', 'A closed restaurant'], 'e0': 'Chef Luis needs vegetables', 'e1': 'for his kitchen.', 'who': 'Chef Luis', 'did': 'buys vegetables early'},
                {'k': 'true', 's': 'A jar of jam costs two coins.', 'g': ('A jar of jam costs two ______.', 'coins'), 'q': 'How much is a jar of jam?', 'a': 'Two coins', 'bad': ['It is always free', 'Two houses', 'Nothing is written'], 'h': 'Jam price', 'ho': 'Two coins for a jar', 'hb': ['A free jar for every visitor', 'A luxury tax only'], 'e0': 'A jar costs', 'e1': 'two coins.', 'who': 'Nika', 'did': 'sells homemade jam'},
                {'k': 'false', 's': 'Old Ken sells fruit.', 'g': ('Old Ken repairs ______.', 'shoes'), 'q': 'What does Old Ken repair?', 'a': 'Shoes', 'bad': ['Ships', 'Hospitals', 'Forests'], 'h': 'The repair stall', 'ho': 'Shoe repairs', 'hb': ['Fruit sales', 'A jewellery shop'], 'e0': 'Old Ken repairs', 'e1': 'shoes.', 'who': 'Old Ken', 'did': 'repairs shoes'},
                {'k': 'ng', 's': 'Zara studied music at a university.', 'g': ('Zara plays a ______.', 'guitar'), 'q': 'What does Zara play?', 'a': 'A guitar', 'bad': ['A drum kit in a stadium', 'Nothing', 'A church organ'], 'h': 'Music', 'ho': 'Guitar between the stalls', 'hb': ['Ticket sales', 'A silent market'], 'e0': 'Zara plays', 'e1': 'a guitar.', 'who': 'Zara', 'did': 'plays a guitar between the stalls'},
                {'k': 'true', 's': 'Policeman Idris walks through the rows.', 'g': ('Policeman Idris keeps bags ______.', 'safer'), 'q': 'Why does the policeman walk through the market?', 'a': 'So bags are safer', 'bad': ['To sell jam', 'To close the hospital', 'To drive the bus'], 'h': 'Safety', 'ho': 'A policeman in the rows', 'hb': ['No one watches the market', 'A soldier at the gate'], 'e0': 'The policeman walks through', 'e1': 'the rows.', 'who': 'Policeman Idris', 'did': 'walks through the rows'},
                {'k': 'true', 's': 'Visitors leave cars in the street.', 'g': ('There is no car park ______ the market.', 'inside'), 'q': 'Where do visitors leave cars?', 'a': 'In the street', 'bad': ['Inside the market', 'At the airport', 'On the roof of every stall'], 'h': 'Cars', 'ho': 'Cars left in the street', 'hb': ['An indoor car park', 'No cars in the town'], 'e0': 'Visitors leave cars', 'e1': 'in the street.'},
                {'k': 'true', 's': 'Three kilos of tomatoes get a lower price.', 'g': ('Three kilos of tomatoes get a lower ______.', 'price'), 'q': 'When is the tomato price lower?', 'a': 'If a customer buys three kilos', 'bad': ['If they buy one tomato', 'The price never changes', 'Only at night'], 'h': 'A better price', 'ho': 'A lower price for three kilos', 'hb': ['Free tomatoes for the town', 'Higher prices for more kilos'], 'e0': 'Three kilos of tomatoes get', 'e1': 'a lower price.'},
                {'k': 'false', 's': 'The market stays open at night.', 'g': ('The stalls close at ______.', 'two'), 'q': 'When do the stalls close?', 'a': 'At two', 'bad': ['At midnight', 'They never close', 'At dawn'], 'h': 'Closing time', 'ho': 'Stalls close at two', 'hb': ['An all-night market', 'Closing at nine in the morning'], 'e0': 'The stalls close', 'e1': 'at two.'},
                {'k': 'true', 's': 'Sellers plan to return if the weather is dry.', 'g': ('Sellers return if the weather is ______.', 'dry'), 'q': 'When do sellers plan to return?', 'a': 'If the weather is dry', 'bad': ['Only if it snows all week', 'They will never return', 'Every night'], 'h': 'Next week', 'ho': 'A return in dry weather', 'hb': ['A promise in every storm', 'The market moves to another country'], 'e0': 'Sellers plan to return', 'e1': 'if the weather is dry.'},
            ],
        },
    ],
}


HIGHER = {
    'B1': [
        {
            'title': 'Community Gardens',
            'names': ['Hana', 'Mr Ortega', 'Priya', 'Ken', 'Sofia', 'Luis'],
            'paragraphs': [
                _p("Community gardens are small plots of land where neighbours grow food together.",
                   "Hana started the garden on an empty corner after the council agreed to a one-year trial.",
                   "Members pay a small yearly fee, and that money buys tools, seeds, and a shared hose."),
                _p("Mr Ortega teaches new members how to prepare soil. He warns that tomatoes need more sun than lettuce.",
                   "Priya keeps a notebook of what each bed produces. The group shares the harvest on Sunday morning.",
                   "People may take vegetables for their own kitchens, but they may not sell them in the street."),
                _p("Water is the main problem in hot weeks. Ken checks the tank every Friday and asks members not to waste it.",
                   "The garden has no night lights, so work stops before dark.",
                   "Sofia organises a monthly meeting. Members vote on which crops to plant next season."),
                _p("Luis builds wooden boxes so older people do not have to bend as much.",
                   "Children may visit with an adult. They can water plants, but they cannot use sharp tools alone.",
                   "Last summer the group gave extra beans to a nearby community kitchen."),
                _p("Some neighbours worried about noise at first. After a few months they said the corner looked cleaner.",
                   "The council has not promised the land forever. The trial can end if the plot is needed for another use.",
                   "Until then the garden remains open to anyone who joins the list and follows the rules."),
            ],
            'items': [
                {'k': 'true', 's': 'Members pay a small yearly fee.', 'g': ('Members pay a small yearly ______.', 'fee'), 'q': 'What do members pay each year?', 'a': 'A small fee', 'bad': ['Nothing at all', 'A house', 'A wage'], 'h': 'The fee', 'ho': 'A yearly fee for tools and seeds', 'hb': ['A fee to enter the city', 'Free land for private sale'], 'e0': 'Members pay', 'e1': 'a small yearly fee.', 'who': 'Hana', 'did': 'started the garden after a council trial'},
                {'k': 'true', 's': 'Tomatoes need more sun than lettuce.', 'g': ('Tomatoes need more sun than ______.', 'lettuce'), 'q': 'Which crop needs more sun?', 'a': 'Tomatoes', 'bad': ['Lettuce', 'Both need no sun', 'Neither is grown'], 'h': 'Sun and crops', 'ho': 'Tomatoes need more sun', 'hb': ['Lettuce needs a dark room', 'No vegetables are grown'], 'e0': 'Tomatoes need more sun than', 'e1': 'lettuce.', 'who': 'Mr Ortega', 'did': 'teaches members how to prepare soil'},
                {'k': 'true', 's': 'The harvest is shared on Sunday morning.', 'g': ('The group shares the harvest on Sunday ______.', 'morning'), 'q': 'When is the harvest shared?', 'a': 'On Sunday morning', 'bad': ['Every night', 'Once a year in secret', 'Never'], 'h': 'Sharing food', 'ho': 'A Sunday morning harvest', 'hb': ['A private sale', 'A winter festival only'], 'e0': 'The harvest is shared', 'e1': 'on Sunday morning.', 'who': 'Priya', 'did': 'keeps a notebook of what each bed produces'},
                {'k': 'false', 's': 'Members may sell vegetables in the street.', 'g': ('Members may not sell food in the ______.', 'street'), 'q': 'What are members not allowed to do with the vegetables?', 'a': 'Sell them in the street', 'bad': ['Take them home', 'Share them', 'Water them'], 'h': 'The rule on sales', 'ho': 'No street sales', 'hb': ['A duty to sell every crop', 'Sales inside a supermarket chain'], 'e0': 'Members may not sell vegetables', 'e1': 'in the street.', 'who': 'Ken', 'did': 'checks the water tank on Fridays'},
                {'k': 'true', 's': 'Work stops before dark because there are no night lights.', 'g': ('The garden has no night ______.', 'lights'), 'q': 'Why does work stop before dark?', 'a': 'There are no night lights', 'bad': ['The law bans daylight', 'The tank is only open at night', 'Members prefer midnight'], 'h': 'After dark', 'ho': 'No lights, so work ends', 'hb': ['A floodlit field', 'Work all night'], 'e0': 'Work stops', 'e1': 'before dark.', 'who': 'Sofia', 'did': 'organises a monthly meeting'},
                {'k': 'ng', 's': 'The garden won a national prize.', 'g': ('Members vote on which ______ to plant.', 'crops'), 'q': 'What do members vote on?', 'a': 'Which crops to plant', 'bad': ['The mayor’s salary', 'Bus fares', 'School exams'], 'h': 'Decisions', 'ho': 'A vote on next season’s crops', 'hb': ['A vote to close the city', 'No meetings at all'], 'e0': 'Members vote on', 'e1': 'which crops to plant.', 'who': 'Luis', 'did': 'builds wooden boxes for older people'},
                {'k': 'true', 's': 'Children cannot use sharp tools alone.', 'g': ('Children cannot use sharp ______ alone.', 'tools'), 'q': 'What must children not use alone?', 'a': 'Sharp tools', 'bad': ['Watering cans', 'Notebooks', 'Seeds'], 'h': 'Children', 'ho': 'No sharp tools without an adult', 'hb': ['Children run the garden alone', 'Children are banned from visits'], 'e0': 'Children cannot use sharp tools', 'e1': 'alone.'},
                {'k': 'true', 's': 'Extra beans went to a community kitchen.', 'g': ('Extra beans went to a community ______.', 'kitchen'), 'q': 'Where did extra beans go?', 'a': 'To a community kitchen', 'bad': ['To a foreign market', 'They were burnt', 'To a supermarket chain'], 'h': 'Extra food', 'ho': 'Beans for a community kitchen', 'hb': ['Beans sold abroad', 'No extra food'], 'e0': 'Extra beans went to', 'e1': 'a community kitchen.'},
                {'k': 'false', 's': 'The council has promised the land forever.', 'g': ('The trial can end if the plot is needed for another ______.', 'use'), 'q': 'What has the council not promised?', 'a': 'The land forever', 'bad': ['A one-year trial', 'Permission to start', 'A place on a corner'], 'h': 'How long the land lasts', 'ho': 'A trial that can end', 'hb': ['A promise of forever', 'Immediate eviction on day one'], 'e0': 'The council has not promised the land', 'e1': 'forever.'},
                {'k': 'true', 's': 'Neighbours later said the corner looked cleaner.', 'g': ('Neighbours said the corner looked ______.', 'cleaner'), 'q': 'What did neighbours say after a few months?', 'a': 'The corner looked cleaner', 'bad': ['The garden made the street unusable', 'They never noticed it', 'They asked for a factory'], 'h': 'Local opinion', 'ho': 'A cleaner corner', 'hb': ['A noisier street forever', 'No change at all'], 'e0': 'Neighbours said the corner looked', 'e1': 'cleaner.'},
            ],
        },
        {
            'title': 'Adult Swimming Lessons',
            'names': ['Coach Mara', 'Jon', 'Anika', 'Receptionist Paul', 'Dr Sen', 'Leila'],
            'paragraphs': [
                _p("The city pool offers beginner lessons for adults who never learned to swim.",
                   "Coach Mara teaches a class of eight on Tuesday and Thursday evenings.",
                   "Each lesson lasts forty minutes and starts in the shallow end, where adults can stand."),
                _p("Jon joined because his children wanted him to enter the water with them.",
                   "Anika was nervous at first and held the side. After three weeks she could float on her back.",
                   "Learners must wear a swim hat. Goggles are allowed but not required."),
                _p("Receptionist Paul checks names at the desk. A missed class can be taken the following week, but not months later.",
                   "The pool provides floats. Learners do not need to buy their own on the first day.",
                   "Dr Sen, who advises the programme, says adults improve faster when they practise twice a week."),
                _p("Leila records attendance. If someone misses four lessons, the place may be offered to the waiting list.",
                   "The class does not include diving. Beginners stay away from the deep end until the coach agrees.",
                   "At the end of the course, confident swimmers may join a general lane session."),
                _p("Fees cover the instructor and entry to the pool on lesson days only.",
                   "There is no promise that every adult will swim a full length by week six.",
                   "Still, most learners in Mara’s last group said they felt safer in the water than before."),
            ],
            'items': [
                {'k': 'true', 's': 'Lessons are for adults who never learned to swim.', 'g': ('Lessons last forty ______.', 'minutes'), 'q': 'How long is each lesson?', 'a': 'Forty minutes', 'bad': ['Four hours', 'Ten minutes', 'All day'], 'h': 'The class', 'ho': 'Beginner lessons for adults', 'hb': ['A children’s racing team', 'A diving school'], 'e0': 'Each lesson lasts', 'e1': 'forty minutes.', 'who': 'Coach Mara', 'did': 'teaches eight adults twice a week'},
                {'k': 'true', 's': 'The class starts in the shallow end.', 'g': ('The class starts in the shallow ______.', 'end'), 'q': 'Where does the class start?', 'a': 'In the shallow end', 'bad': ['In the deep end', 'On the roof', 'In the sea'], 'h': 'Where they begin', 'ho': 'The shallow end', 'hb': ['Open water', 'A diving board'], 'e0': 'The class starts', 'e1': 'in the shallow end.', 'who': 'Jon', 'did': 'joined so he could enter the water with his children'},
                {'k': 'true', 's': 'Anika could float on her back after three weeks.', 'g': ('Anika could float on her ______.', 'back'), 'q': 'What could Anika do after three weeks?', 'a': 'Float on her back', 'bad': ['Dive from ten metres', 'Swim the channel', 'Skip every class'], 'h': 'Progress', 'ho': 'Floating after three weeks', 'hb': ['No improvement is possible', 'A professional race'], 'e0': 'Anika could float', 'e1': 'on her back.', 'who': 'Anika', 'did': 'learned to float on her back'},
                {'k': 'false', 's': 'Goggles are required.', 'g': ('Learners must wear a swim ______.', 'hat'), 'q': 'What must learners wear?', 'a': 'A swim hat', 'bad': ['A coat', 'Nothing', 'Goggles, which are required'], 'h': 'Kit', 'ho': 'A swim hat is required', 'hb': ['Goggles are required', 'No rules on clothing'], 'e0': 'Learners must wear', 'e1': 'a swim hat.', 'who': 'Receptionist Paul', 'did': 'checks names at the desk'},
                {'k': 'true', 's': 'A missed class can be taken the following week.', 'g': ('A missed class can be taken the following ______.', 'week'), 'q': 'When can a missed class be taken?', 'a': 'The following week', 'bad': ['Months later without limit', 'Never', 'Only the same hour'], 'h': 'Missed classes', 'ho': 'A catch-up the next week', 'hb': ['No catch-up exists', 'A catch-up months later by right'], 'e0': 'A missed class can be taken', 'e1': 'the following week.', 'who': 'Dr Sen', 'did': 'says adults improve faster with twice-weekly practice'},
                {'k': 'ng', 's': 'The pool was built in 1980.', 'g': ('The pool provides ______.', 'floats'), 'q': 'What does the pool provide on the first day?', 'a': 'Floats', 'bad': ['Private tutors at home', 'A wetsuit', 'Nothing'], 'h': 'Equipment', 'ho': 'Floats are provided', 'hb': ['Learners must buy a float first', 'No equipment is allowed'], 'e0': 'The pool provides', 'e1': 'floats.', 'who': 'Leila', 'did': 'records attendance'},
                {'k': 'true', 's': 'Four missed lessons can mean losing the place.', 'g': ('After four missed lessons the place may go to the waiting ______.', 'list'), 'q': 'What may happen after four missed lessons?', 'a': 'The place may go to the waiting list', 'bad': ['The learner is paid', 'Nothing changes ever', 'The pool closes'], 'h': 'Attendance', 'ho': 'A place may be lost after four absences', 'hb': ['Unlimited absences', 'A fine of one house'], 'e0': 'The place may be offered to', 'e1': 'the waiting list.'},
                {'k': 'false', 's': 'The class includes diving.', 'g': ('Beginners stay away from the deep end until the ______ agrees.', 'coach'), 'q': 'When may beginners use the deep end?', 'a': 'When the coach agrees', 'bad': ['On day one', 'Never, because diving is the first lesson', 'Whenever they want'], 'h': 'The deep end', 'ho': 'Only when the coach agrees', 'hb': ['Diving from the first lesson', 'The deep end is the starting point'], 'e0': 'Beginners avoid the deep end until', 'e1': 'the coach agrees.'},
                {'k': 'true', 's': 'Fees cover the instructor and entry on lesson days only.', 'g': ('Fees cover entry on lesson ______ only.', 'days'), 'q': 'What do the fees cover besides the instructor?', 'a': 'Entry on lesson days', 'bad': ['Entry every day of the year', 'A hotel stay', 'Nothing'], 'h': 'What the fee includes', 'ho': 'Instructor and entry on lesson days', 'hb': ['Unlimited yearly entry', 'Equipment for home'], 'e0': 'Fees cover entry', 'e1': 'on lesson days only.'},
                {'k': 'ng', 's': 'Every adult swims a full length by week six.', 'g': ('Most learners felt ______ in the water.', 'safer'), 'q': 'How did most learners in the last group feel?', 'a': 'Safer in the water', 'bad': ['Ready for the Olympics', 'Worse than before', 'Unchanged, according to the text'], 'h': 'The result', 'ho': 'Most felt safer', 'hb': ['A guaranteed full length', 'Everyone failed'], 'e0': 'Most learners felt', 'e1': 'safer than before.'},
            ],
        },
    ],
    'B2': [
        {
            'title': 'How Public Museums Began',
            'names': ['Sir Hans', 'Curator Ellen', 'Historian Marc', 'Donor Clara', 'Guide Tomas', 'Critic Adele'],
            'paragraphs': [
                _p("Many great museums began as private cabinets of objects collected by wealthy individuals.",
                   "In the eighteenth century, Sir Hans agreed that his collection should be held for public use after his death.",
                   "Visitors at first had to apply for a ticket, so entry was possible but not casual."),
                _p("Curator Ellen’s notes from a later period show that labels were short and often in Latin.",
                   "Historian Marc argues that this made the rooms impressive but difficult for ordinary readers.",
                   "Lighting was poor. Objects were crowded into cases so that more of the collection could be seen at once."),
                _p("Donor Clara paid for a new gallery on the condition that school groups could enter without a fee on Saturdays.",
                   "That rule still shapes some education programmes, although weekday visits may be charged.",
                   "Guide Tomas now leads short tours in plain language and stops at only six objects, not the whole building."),
                _p("Critic Adele warns that a famous object can dominate a visit and hide quieter pieces that matter to researchers.",
                   "Museums therefore rotate displays. A painting shown this year may be stored next year to protect it from light.",
                   "Storage is not a failure of the museum. It is how fragile works survive."),
                _p("Debates continue about objects taken during imperial expansion. Some communities ask for returns. Others accept long loans.",
                   "The passage does not claim that every disputed object will go back, nor that none will.",
                   "What it does claim is that public museums changed private collecting into a shared, if imperfect, institution."),
            ],
            'items': [
                {'k': 'true', 's': 'Early visitors had to apply for a ticket.', 'g': ('Early visitors had to apply for a ______.', 'ticket'), 'q': 'How did early visitors get in?', 'a': 'They applied for a ticket', 'bad': ['They walked in at any hour without rules', 'Only kings could enter', 'Entry was impossible'], 'h': 'Early entry', 'ho': 'Tickets had to be requested', 'hb': ['Open doors all day from the start', 'A total ban on the public'], 'e0': 'Visitors had to apply', 'e1': 'for a ticket.', 'who': 'Sir Hans', 'did': 'left a collection for public use'},
                {'k': 'true', 's': 'Early labels were often in Latin.', 'g': ('Early labels were often in ______.', 'Latin'), 'q': 'What made early rooms hard for ordinary readers?', 'a': 'Labels often in Latin', 'bad': ['There were no objects', 'The building had no roof', 'Guides spoke only in song'], 'h': 'Labels', 'ho': 'Short labels, often in Latin', 'hb': ['Labels in every modern language', 'No labels were ever used'], 'e0': 'Labels were often', 'e1': 'in Latin.', 'who': 'Curator Ellen', 'did': 'recorded that labels were often in Latin'},
                {'k': 'true', 's': 'Poor lighting and crowded cases were typical.', 'g': ('Lighting was ______.', 'poor'), 'q': 'What was the lighting like in the early rooms?', 'a': 'Poor', 'bad': ['Brighter than daylight all night', 'Unnecessary because of glass walls', 'Never mentioned'], 'h': 'The early rooms', 'ho': 'Poor light and crowded cases', 'hb': ['Empty galleries', 'A digital display from the start'], 'e0': 'Objects were crowded', 'e1': 'into cases.', 'who': 'Historian Marc', 'did': 'argues the rooms were difficult for ordinary readers'},
                {'k': 'true', 's': 'School groups can enter without a fee on Saturdays.', 'g': ('School groups enter without a fee on ______.', 'Saturdays'), 'q': 'When can school groups enter without a fee?', 'a': 'On Saturdays', 'bad': ['Every night', 'Never', 'Only on weekdays, according to the gift'], 'h': 'A donor’s condition', 'ho': 'Free Saturday entry for schools', 'hb': ['Free entry every day for all adults', 'A ban on schools'], 'e0': 'School groups can enter without a fee', 'e1': 'on Saturdays.', 'who': 'Donor Clara', 'did': 'paid for a gallery if schools could enter free on Saturdays'},
                {'k': 'false', 's': 'Weekday school visits are always free.', 'g': ('Weekday visits may be ______.', 'charged'), 'q': 'What may happen to weekday visits?', 'a': 'They may be charged', 'bad': ['They are always free', 'They are illegal', 'They last all night'], 'h': 'Weekdays', 'ho': 'Weekday visits may be charged', 'hb': ['Weekdays are always free', 'The museum closes all week'], 'e0': 'Weekday visits may be', 'e1': 'charged.', 'who': 'Guide Tomas', 'did': 'leads short tours of only six objects'},
                {'k': 'true', 's': 'A famous object can hide quieter pieces.', 'g': ('Works may be stored to protect them from ______.', 'light'), 'q': 'Why may a painting be stored the following year?', 'a': 'To protect it from light', 'bad': ['Because it has no value', 'To sell it the same day', 'Because storage means the museum failed'], 'h': 'Rotation', 'ho': 'Displays change to protect works from light', 'hb': ['Every object stays on show forever', 'Storage means failure'], 'e0': 'A painting may be stored', 'e1': 'to protect it from light.', 'who': 'Critic Adele', 'did': 'warns that a famous object can hide quieter pieces'},
                {'k': 'false', 's': 'Storage means the museum has failed.', 'g': ('Storage helps fragile works ______.', 'survive'), 'q': 'What is storage described as?', 'a': 'A way for fragile works to survive', 'bad': ['Proof of failure', 'A way to hide crime', 'The end of the collection'], 'h': 'Why objects are stored', 'ho': 'Survival of fragile works', 'hb': ['Evidence of failure', 'A temporary shop'], 'e0': 'Storage helps fragile works', 'e1': 'survive.'},
                {'k': 'ng', 's': 'Every disputed object will be returned.', 'g': ('Some communities ask for ______.', 'returns'), 'q': 'What do some communities ask for?', 'a': 'Returns', 'bad': ['The closure of all museums', 'Nothing at all', 'A single global decision already completed'], 'h': 'Disputed objects', 'ho': 'Requests for return, or acceptance of loans', 'hb': ['A claim that every object will go back', 'A claim that none will ever move'], 'e0': 'Some communities ask for', 'e1': 'returns.'},
                {'k': 'true', 's': 'Other communities accept long loans.', 'g': ('Others accept long ______.', 'loans'), 'q': 'What do other communities accept?', 'a': 'Long loans', 'bad': ['Immediate destruction', 'A ban on all display', 'Cash only, according to the text'], 'h': 'Another response', 'ho': 'Long loans', 'hb': ['Only permanent gifts', 'Silence from every community'], 'e0': 'Others accept', 'e1': 'long loans.'},
                {'k': 'true', 's': 'Private collecting became a shared institution.', 'g': ('Museums turned private collecting into a shared ______.', 'institution'), 'q': 'What did public museums turn private collecting into?', 'a': 'A shared institution', 'bad': ['A secret club', 'A shop for one family', 'Nothing lasting'], 'h': 'The larger change', 'ho': 'A shared, if imperfect, institution', 'hb': ['The end of all collections', 'A perfect system with no debate'], 'e0': 'Private collecting became', 'e1': 'a shared institution.'},
            ],
        },
        {
            'title': 'Agreeing the World’s Time Zones',
            'names': ['Fleming', 'Delegate Roux', 'Engineer Patel', 'Minister Cho', 'Clerk Ives', 'Scientist Berg'],
            'paragraphs': [
                _p("Before standard time, towns set clocks by the local sun. Noon in one town was not noon a short distance away.",
                   "Railway timetables became confusing because a train’s departure and arrival could be printed in two local times.",
                   "Fleming proposed dividing the earth into zones of about fifteen degrees, each one hour apart."),
                _p("Delegate Roux supported the idea for shipping as well as rail, since captains needed a shared reference.",
                   "Not every government agreed at once. Some cities kept local time for years after the conferences.",
                   "Engineer Patel notes that the zones are a human agreement, not a fact of nature. Borders bend for political reasons."),
                _p("Minister Cho’s country adopted the new standard because cross-border trade needed matching office hours.",
                   "A few places still use an offset of thirty minutes rather than a full hour.",
                   "Clerk Ives, who published the first national timetable under the new system, reported fewer missed connections."),
                _p("Scientist Berg points out that solar noon still varies inside a zone. A clock can read twelve while the sun is not overhead.",
                   "That difference is accepted because coordination is more useful than perfect astronomy for daily life.",
                   "Daylight-saving shifts, where they exist, are a later political choice and were not part of the original zone map."),
                _p("The system is therefore practical rather than exact. It reduced chaos in transport and business.",
                   "It did not remove all arguments about where a border should fall, and it does not tell a country whether to move the clocks in summer.",
                   "Its achievement was narrower and more solid: one hour, one zone, and a timetable that two cities could share."),
            ],
            'items': [
                {'k': 'true', 's': 'Towns once set clocks by the local sun.', 'g': ('Towns once set clocks by the local ______.', 'sun'), 'q': 'How did towns set clocks before standard time?', 'a': 'By the local sun', 'bad': ['By radio from one capital always', 'By railway law from the start', 'They did not use clocks'], 'h': 'Before standard time', 'ho': 'Local solar time', 'hb': ['One global clock from the ancient world', 'No clocks in towns'], 'e0': 'Towns set clocks', 'e1': 'by the local sun.', 'who': 'Fleming', 'did': 'proposed zones about one hour apart'},
                {'k': 'true', 's': 'Railway timetables mixed two local times.', 'g': ('Railway timetables became ______.', 'confusing'), 'q': 'What problem did railways face?', 'a': 'Timetables in two local times', 'bad': ['A lack of trains', 'Too many engines', 'A ban on printed times'], 'h': 'The railway problem', 'ho': 'Confusing timetables', 'hb': ['Perfect schedules from the start', 'Railways ignored time'], 'e0': 'Timetables became', 'e1': 'confusing.', 'who': 'Delegate Roux', 'did': 'supported the idea for shipping and rail'},
                {'k': 'true', 's': 'Zones were proposed at about one hour apart.', 'g': ('Zones were about one ______ apart.', 'hour'), 'q': 'How far apart were the proposed zones?', 'a': 'About one hour', 'bad': ['One minute', 'One day', 'They were not measured in time'], 'h': 'The proposal', 'ho': 'Zones one hour apart', 'hb': ['A single clock for the whole earth with no zones', 'Zones of one week'], 'e0': 'Zones were about one hour', 'e1': 'apart.', 'who': 'Engineer Patel', 'did': 'notes that borders bend for political reasons'},
                {'k': 'false', 's': 'Every government agreed at once.', 'g': ('Some cities kept local time for ______.', 'years'), 'q': 'What did some cities do after the conferences?', 'a': 'They kept local time for years', 'bad': ['They all changed the next morning', 'They abandoned clocks', 'They moved to the sea'], 'h': 'Slow adoption', 'ho': 'Some cities waited for years', 'hb': ['Immediate universal agreement', 'A ban on conferences'], 'e0': 'Some cities kept local time', 'e1': 'for years.', 'who': 'Minister Cho', 'did': 'adopted standard time for cross-border trade'},
                {'k': 'true', 's': 'Zone borders bend for political reasons.', 'g': ('Borders bend for ______ reasons.', 'political'), 'q': 'Why are zone borders not perfectly straight?', 'a': 'For political reasons', 'bad': ['Because the sun demands it', 'Because railways cannot cross lines', 'The text says they never bend'], 'h': 'Bent borders', 'ho': 'Political reasons, not nature', 'hb': ['A law of astronomy', 'Random error only'], 'e0': 'Borders bend for', 'e1': 'political reasons.', 'who': 'Clerk Ives', 'did': 'published a timetable with fewer missed connections'},
                {'k': 'true', 's': 'Some places use a thirty-minute offset.', 'g': ('Some places use an offset of thirty ______.', 'minutes'), 'q': 'What unusual offset do a few places use?', 'a': 'Thirty minutes', 'bad': ['Thirty days', 'No offset is mentioned', 'Twelve hours only'], 'h': 'Half hours', 'ho': 'A thirty-minute offset', 'hb': ['Only full hours exist everywhere', 'A ten-second offset'], 'e0': 'A few places use an offset of', 'e1': 'thirty minutes.', 'who': 'Scientist Berg', 'did': 'points out that solar noon still varies inside a zone'},
                {'k': 'true', 's': 'Solar noon can differ from twelve o’clock inside a zone.', 'g': ('A clock can read twelve when the sun is not ______.', 'overhead'), 'q': 'What can be true at twelve o’clock inside a zone?', 'a': 'The sun may not be overhead', 'bad': ['The sun is always overhead', 'Clocks stop', 'The zone has no noon'], 'h': 'Clock time and the sun', 'ho': 'Twelve o’clock is not always solar noon', 'hb': ['The sun matches every clock exactly', 'Zones removed the sun'], 'e0': 'The sun may not be', 'e1': 'overhead at twelve.'},
                {'k': 'false', 's': 'Daylight saving was part of the original zone map.', 'g': ('Daylight-saving shifts were not part of the original zone ______.', 'map'), 'q': 'What was not part of the original zone map?', 'a': 'Daylight-saving shifts', 'bad': ['One-hour zones', 'The idea of coordination', 'Railway timetables as a motive'], 'h': 'Summer time', 'ho': 'A later political choice', 'hb': ['Part of the original map', 'Required by Fleming’s first plan'], 'e0': 'Daylight saving was not part of', 'e1': 'the original zone map.'},
                {'k': 'ng', 's': 'The conference was held in Paris.', 'g': ('The system reduced chaos in transport and ______.', 'business'), 'q': 'Which two areas became less chaotic?', 'a': 'Transport and business', 'bad': ['Farming and fishing only', 'Sport and music', 'Nothing improved'], 'h': 'What improved', 'ho': 'Less chaos in transport and business', 'hb': ['The end of all disagreement', 'No practical gain'], 'e0': 'The system reduced chaos in', 'e1': 'transport and business.'},
                {'k': 'true', 's': 'Arguments about borders were not all removed.', 'g': ('The system did not tell countries whether to move clocks in ______.', 'summer'), 'q': 'What does the zone system not decide?', 'a': 'Whether to move clocks in summer', 'bad': ['Whether an hour has sixty minutes', 'Whether two cities can share a timetable', 'Whether zones exist'], 'h': 'What remains open', 'ho': 'Border arguments and summer clock changes', 'hb': ['Every question was settled forever', 'Time zones were abandoned'], 'e0': 'Not every border argument', 'e1': 'was removed.'},
            ],
        },
    ],
    'C1': [
        {
            'title': 'Why Cities Keep Vacant Land',
            'names': ['Planner Voss', 'Economist Rahim', 'Ecologist Mei', 'Lawyer Ortiz', 'Campaigner Jules', 'Auditor Singh'],
            'paragraphs': [
                _p("Vacant plots in growing cities are often described as waste. Planners increasingly treat them as a form of flexibility.",
                   "Planner Voss argues that land held back from immediate building can absorb a later school, clinic, or flood channel that cannot be predicted in detail.",
                   "The cost of that choice is forgone rent. The benefit is avoiding a demolition when the city’s needs change."),
                _p("Economist Rahim notes that private owners may leave land empty while they wait for a higher price. That motive is different from a public reserve.",
                   "A tax on vacant lots can push owners to build, but it can also punish an owner who is assembling several plots for one careful scheme.",
                   "The passage therefore separates speculative delay from deliberate open space."),
                _p("Ecologist Mei adds that a rough, unmown plot can support insects and young trees that a finished park, with its paths and lights, may not.",
                   "These sites are not automatically safe. They can hide dumping, and neighbours may reasonably ask for fencing and basic care.",
                   "Maintenance, not a new building, is sometimes the missing policy."),
                _p("Lawyer Ortiz points to temporary leases: a community garden or a market can use the land for five years without extinguishing the city’s right to build later.",
                   "Campaigner Jules supports this where residents help design the temporary use, rather than receiving a plan already fixed.",
                   "Auditor Singh finds that such leases fail when the paperwork is slow and the community cannot get insurance."),
                _p("No single rule fits every plot. A vacant riverside site may be a flood asset, while a vacant shop is simply a closed business.",
                   "The argument is that emptiness is information. It can be speculation, ecology, or a reserved public option.",
                   "Reading it only as failure makes the later, harder decision — what the city should still be able to do — impossible to see."),
            ],
            'items': [
                {'k': 'true', 's': 'Holding land back can avoid a later demolition.', 'g': ('The benefit is avoiding a later ______.', 'demolition'), 'q': 'What cost is set against forgone rent?', 'a': 'The benefit of avoiding demolition', 'bad': ['A guarantee of higher private profit', 'The end of all planning', 'Free housing for every resident'], 'h': 'Flexibility', 'ho': 'Land kept for a use that cannot yet be specified', 'hb': ['Vacant land is always waste', 'Every plot must be built at once'], 'e0': 'Holding land can avoid', 'e1': 'a later demolition.', 'who': 'Planner Voss', 'did': 'argues vacant land can absorb a later public use'},
                {'k': 'true', 's': 'Private owners may wait for a higher price.', 'g': ('Some owners wait for a higher ______.', 'price'), 'q': 'Why might a private owner leave land empty?', 'a': 'To wait for a higher price', 'bad': ['Because the city forbids all sales', 'Because ecology always requires it', 'The text gives no private motive'], 'h': 'Speculation', 'ho': 'Waiting for a higher price', 'hb': ['The same motive as a public reserve', 'A legal duty to stay empty'], 'e0': 'Owners may wait for', 'e1': 'a higher price.', 'who': 'Economist Rahim', 'did': 'separates speculative delay from a public reserve'},
                {'k': 'true', 's': 'A vacancy tax can also punish a careful assembly of plots.', 'g': ('A tax can punish an owner who is assembling several ______.', 'plots'), 'q': 'Who else might a vacancy tax affect?', 'a': 'An owner assembling several plots', 'bad': ['Only foreign visitors', 'Nobody, because the tax has one clean effect', 'Only renters in finished flats'], 'h': 'The tax trade-off', 'ho': 'Pressure to build, and a possible penalty for assembly', 'hb': ['A tax with no side effect', 'A ban on all taxes'], 'e0': 'A vacancy tax can punish', 'e1': 'the assembly of several plots.', 'who': 'Ecologist Mei', 'did': 'says rough plots can support insects and young trees'},
                {'k': 'true', 's': 'A rough plot can support insects that a finished park may not.', 'g': ('A finished park may not support the same ______.', 'insects'), 'q': 'What may a finished park fail to support as well?', 'a': 'Insects found on a rough plot', 'bad': ['All plant life', 'Paths and lights, which it lacks', 'Nothing living'], 'h': 'Ecology', 'ho': 'Rough ground as habitat', 'hb': ['Finished parks are always richer in wildlife', 'Vacant plots are biologically empty'], 'e0': 'A rough plot can support', 'e1': 'insects a finished park may not.', 'who': 'Lawyer Ortiz', 'did': 'describes temporary leases that do not cancel the right to build'},
                {'k': 'false', 's': 'Vacant plots are automatically safe.', 'g': ('Neighbours may ask for fencing and basic ______.', 'care'), 'q': 'What may neighbours reasonably ask for?', 'a': 'Fencing and basic care', 'bad': ['Immediate high-rise building', 'The closure of the city', 'Nothing, because the sites are automatically safe'], 'h': 'Local concern', 'ho': 'Dumping, fencing, and care', 'hb': ['Automatic safety', 'A duty to leave dumping in place'], 'e0': 'Neighbours may ask for', 'e1': 'fencing and basic care.', 'who': 'Campaigner Jules', 'did': 'wants residents to help design temporary use'},
                {'k': 'true', 's': 'Temporary leases need not extinguish the right to build later.', 'g': ('A lease can last five ______ without ending the city’s right to build.', 'years'), 'q': 'What can a temporary lease avoid extinguishing?', 'a': 'The city’s later right to build', 'bad': ['All private ownership', 'The need for any agreement', 'Public access forever'], 'h': 'Temporary use', 'ho': 'Use now without losing the option to build', 'hb': ['A lease that ends public ownership', 'A permanent transfer'], 'e0': 'A temporary lease need not extinguish', 'e1': 'the right to build later.', 'who': 'Auditor Singh', 'did': 'finds leases fail when paperwork and insurance are slow'},
                {'k': 'true', 's': 'Leases fail when insurance is hard to obtain.', 'g': ('Leases fail when communities cannot get ______.', 'insurance'), 'q': 'What practical barrier does the auditor mention besides slow paperwork?', 'a': 'Insurance', 'bad': ['A lack of sunlight', 'Too many residents', 'The price of seeds'], 'h': 'Why leases stall', 'ho': 'Slow paperwork and insurance', 'hb': ['A lack of legal interest', 'Unlimited easy insurance'], 'e0': 'Leases fail when communities cannot get', 'e1': 'insurance.'},
                {'k': 'false', 's': 'A vacant shop and a vacant riverside site are the same kind of problem.', 'g': ('A riverside site may be a ______ asset.', 'flood'), 'q': 'What may a vacant riverside site be?', 'a': 'A flood asset', 'bad': ['Identical to a closed shop', 'Useless in every case', 'A finished museum'], 'h': 'Not one category', 'ho': 'A flood asset is not the same as a closed shop', 'hb': ['All vacancy is one problem', 'Rivers do not matter'], 'e0': 'A riverside plot may be', 'e1': 'a flood asset.'},
                {'k': 'ng', 's': 'Most vacant land in the city is publicly owned.', 'g': ('Emptiness can be speculation, ecology, or a reserved public ______.', 'option'), 'q': 'Which three readings of emptiness does the passage allow?', 'a': 'Speculation, ecology, or a reserved public option', 'bad': ['Only failure', 'Only profit', 'Only sport'], 'h': 'How to read emptiness', 'ho': 'Speculation, ecology, or a reserved option', 'hb': ['Failure only', 'A single national statistic'], 'e0': 'Emptiness can be a reserved public', 'e1': 'option.'},
                {'k': 'true', 's': 'Reading vacancy only as failure hides a later choice.', 'g': ('Seeing only failure makes the later decision ______ to see.', 'impossible'), 'q': 'What does a failure-only reading make hard to see?', 'a': 'What the city should still be able to do', 'bad': ['The colour of the soil', 'Yesterday’s rent only', 'Nothing important'], 'h': 'The cost of one story', 'ho': 'A narrow story hides the later choice', 'hb': ['Failure is the only accurate description', 'Planning should ignore vacancy'], 'e0': 'A failure-only reading hides', 'e1': 'the later decision.'},
            ],
        },
        {
            'title': 'Open-Plan Offices and Attention',
            'names': ['Dr Okonkwo', 'Manager Ellis', 'Researcher Nair', 'Designer Berg', 'Union rep Salim', 'Analyst Cho'],
            'paragraphs': [
                _p("Open-plan offices were promoted as a way to increase conversation and reduce the cost of walls.",
                   "Dr Okonkwo’s review of several workplace studies finds a less tidy result: easy visibility does not reliably produce useful talk.",
                   "Short questions do increase. Longer thinking, especially work that requires holding a problem in mind, often decreases."),
                _p("Manager Ellis introduced the layout to help new staff learn by overhearing. Some did learn routines faster.",
                   "Others began to use headphones for most of the day, which restored quiet but reduced the very overhearing the office was meant to provide.",
                   "The design therefore changed behaviour in two directions at once."),
                _p("Researcher Nair separates interruption from ambient noise. A distant murmur may be tolerable. A question addressed to the person beside you is not, because it demands a reply.",
                   "That distinction matters for what a designer can control. Acoustic panels can soften murmur. They cannot decide whether someone should tap a colleague’s shoulder.",
                   "Norms, not furniture, govern the second problem."),
                _p("Designer Berg now recommends a mix: open desks for tasks that benefit from quick coordination, and small rooms booked for work that collapses when it is broken.",
                   "The rooms are not a return to private offices for everyone. There are fewer of them than there are staff, so they must be reserved.",
                   "Union rep Salim argues that if booking is informal, senior staff will occupy the rooms and juniors will remain in the noise."),
                _p("Analyst Cho finds that satisfaction scores rise when people can predict their afternoon, not merely when the office is fashionable.",
                   "The passage does not claim that open plan should be abolished, nor that it suits every task.",
                   "It claims that attention is a resource the layout spends, and that spending it on constant availability has a price."),
            ],
            'items': [
                {'k': 'true', 's': 'Open plan was promoted to increase conversation and cut the cost of walls.', 'g': ('Open plan was meant to reduce the cost of ______.', 'walls'), 'q': 'Which two aims promoted open-plan offices?', 'a': 'More conversation and lower wall costs', 'bad': ['Total silence and private offices', 'Fewer staff', 'Outdoor work'], 'h': 'The original promise', 'ho': 'More talk and fewer walls', 'hb': ['A promise of silence', 'A promise of private rooms for all'], 'e0': 'Open plan aimed to increase conversation and cut', 'e1': 'the cost of walls.', 'who': 'Dr Okonkwo', 'did': 'finds visibility does not reliably produce useful talk'},
                {'k': 'true', 's': 'Longer thinking often decreases in these offices.', 'g': ('Work that requires holding a problem in mind often ______.', 'decreases'), 'q': 'What often decreases, according to the review?', 'a': 'Longer thinking', 'bad': ['All speech', 'The number of desks', 'Nothing measurable'], 'h': 'A cost to concentration', 'ho': 'Longer thinking often declines', 'hb': ['Deep work reliably improves', 'No cognitive effect'], 'e0': 'Longer thinking often', 'e1': 'decreases.', 'who': 'Manager Ellis', 'did': 'hoped new staff would learn by overhearing'},
                {'k': 'true', 's': 'Headphones restored quiet but reduced overhearing.', 'g': ('Headphones reduced the ______ the office was meant to provide.', 'overhearing'), 'q': 'What did headphones reduce?', 'a': 'The overhearing the layout was meant to provide', 'bad': ['The need for desks', 'All cooperation forever', 'The manager’s post'], 'h': 'An unintended pair of effects', 'ho': 'Quiet returns, overhearing falls', 'hb': ['Headphones increase overhearing', 'No one uses headphones'], 'e0': 'Headphones reduced', 'e1': 'overhearing.', 'who': 'Researcher Nair', 'did': 'separates interruption from ambient noise'},
                {'k': 'true', 's': 'A direct question demands a reply in a way a murmur does not.', 'g': ('A distant ______ may be tolerable.', 'murmur'), 'q': 'What may be tolerable that a direct question is not?', 'a': 'A distant murmur', 'bad': ['Any interruption', 'Silence', 'A formal meeting'], 'h': 'Two kinds of sound', 'ho': 'Murmur versus a question that needs a reply', 'hb': ['All noise is the same', 'Speech is never a problem'], 'e0': 'A question demands', 'e1': 'a reply.', 'who': 'Designer Berg', 'did': 'recommends open desks plus bookable small rooms'},
                {'k': 'false', 's': 'Acoustic panels can stop colleagues from interrupting.', 'g': ('Norms, not furniture, govern ______.', 'interruption'), 'q': 'What governs shoulder-tapping, according to the passage?', 'a': 'Norms rather than furniture', 'bad': ['Acoustic panels alone', 'The height of the ceiling only', 'Nothing can be said'], 'h': 'What design cannot do', 'ho': 'Panels soften murmur but do not set norms', 'hb': ['Panels prevent every interruption', 'Furniture decides all behaviour'], 'e0': 'Norms, not furniture, govern', 'e1': 'whether someone interrupts.', 'who': 'Union rep Salim', 'did': 'warns senior staff may monopolise the quiet rooms'},
                {'k': 'true', 's': 'There are fewer small rooms than staff.', 'g': ('The small rooms must be ______.', 'reserved'), 'q': 'Why must the small rooms be reserved?', 'a': 'There are fewer of them than there are staff', 'bad': ['They are larger than the whole office', 'They are private offices for everyone', 'They are never used'], 'h': 'A scarce room', 'ho': 'Fewer quiet rooms than people', 'hb': ['A room for every employee', 'The end of open desks'], 'e0': 'The rooms must be', 'e1': 'reserved.', 'who': 'Analyst Cho', 'did': 'links satisfaction to a predictable afternoon'},
                {'k': 'true', 's': 'Informal booking may favour senior staff.', 'g': ('Juniors may remain in the ______ if booking is informal.', 'noise'), 'q': 'Who may remain in the noise if booking is informal?', 'a': 'Junior staff', 'bad': ['Only visitors', 'Nobody', 'The designer'], 'h': 'Who gets the quiet', 'ho': 'A risk that seniors take the rooms', 'hb': ['A guarantee of equal access', 'Juniors control the rooms by right'], 'e0': 'Juniors may remain in', 'e1': 'the noise.'},
                {'k': 'false', 's': 'The passage says open plan should be abolished.', 'g': ('Satisfaction rises when people can ______ their afternoon.', 'predict'), 'q': 'When do satisfaction scores rise?', 'a': 'When people can predict their afternoon', 'bad': ['Whenever the office is fashionable', 'Only if walls return for everyone', 'The scores are not discussed'], 'h': 'What staff value', 'ho': 'A predictable afternoon', 'hb': ['Fashionable design by itself', 'The abolition of open plan'], 'e0': 'Satisfaction rises when the afternoon is', 'e1': 'predictable.'},
                {'k': 'ng', 's': 'Open-plan offices reduce rent by forty percent.', 'g': ('Attention is a ______ the layout spends.', 'resource'), 'q': 'What does the layout spend, in the passage’s metaphor?', 'a': 'Attention', 'bad': ['Only money on plants', 'Nothing of value', 'Staff salaries, which are fully explained'], 'h': 'The metaphor', 'ho': 'Attention as a resource that is spent', 'hb': ['A claim that attention is unlimited', 'A precise rent reduction'], 'e0': 'The layout spends', 'e1': 'attention.'},
                {'k': 'true', 's': 'Constant availability has a price.', 'g': ('Spending attention on constant availability has a ______.', 'price'), 'q': 'What has a price, in the final claim?', 'a': 'Spending attention on constant availability', 'bad': ['Any conversation', 'Booking a room', 'Having desks'], 'h': 'The final claim', 'ho': 'Availability is not free', 'hb': ['Open plan suits every task', 'Open plan should vanish'], 'e0': 'Constant availability has', 'e1': 'a price.'},
            ],
        },
    ],
    'C2': [
        {
            'title': 'Replication and the Credibility of Findings',
            'names': ['Professor Adler', 'Editor Kwon', 'Statistician Rahman', 'Philosopher Estes', 'Funder Iqbal', 'Methodologist Serra'],
            'paragraphs': [
                _p("A finding that cannot be repeated is not automatically false, but it is a weak basis for a strong claim.",
                   "Professor Adler distinguishes a failed replication caused by a real difference in context from one caused by a result that was fragile in the first place.",
                   "The distinction is easy to state and hard to prove, because the original conditions are rarely described in full."),
                _p("Editor Kwon’s journal now asks authors to state, before they see the data analysis, which result would count as support.",
                   "This does not stop a surprising pattern from being reported. It stops that pattern from being treated as the hypothesis that was tested.",
                   "Critics reply that scientific discovery is often recognisable only after the fact, so a rigid pre-statement can undervalue insight."),
                _p("Statistician Rahman argues that the argument is not mainly about honesty. Small samples and flexible analysis can produce a striking number even when every step is reported.",
                   "In that case the remedy is not accusation but a design that was never likely to fit noise: more observations, or a simpler claim.",
                   "A single dramatic study remains news. It does not, by itself, become a settled generalisation."),
                _p("Philosopher Estes resists the idea that replication is the only virtue. A study can be repeatable and still measure the wrong thing.",
                   "Funder Iqbal, who pays for multi-site repeats, accepts the cost because a cheap study that cannot travel is often an expensive mistake later.",
                   "Methodologist Serra notes that some phenomena, especially those tied to a particular institution, should not be expected to copy perfectly elsewhere."),
                _p("The mature position is therefore narrower than a slogan. Replication raises confidence when the claim was specified and the context was comparable.",
                   "It does not prove a universal law, and a failure does not by itself prove misconduct.",
                   "What it can do is slow the passage from an interesting result to a recommendation that other people must live with."),
            ],
            'items': [
                {'k': 'true', 's': 'A finding that cannot be repeated is a weak basis for a strong claim.', 'g': ('An unrepeated finding is a weak basis for a strong ______.', 'claim'), 'q': 'What is an unrepeated finding a weak basis for?', 'a': 'A strong claim', 'bad': ['Any description of method', 'The existence of data', 'A weak claim, which the text forbids'], 'h': 'The status of one result', 'ho': 'Too little for a strong claim', 'hb': ['Automatic proof of falsehood', 'Proof that the study never happened'], 'e0': 'An unrepeated finding is a weak basis for', 'e1': 'a strong claim.', 'who': 'Professor Adler', 'did': 'distinguishes context from a fragile result'},
                {'k': 'true', 's': 'Original conditions are rarely described in full.', 'g': ('Original conditions are rarely described in ______.', 'full'), 'q': 'Why is the distinction hard to prove?', 'a': 'Original conditions are rarely fully described', 'bad': ['Replication is illegal', 'Journals ban methods sections', 'Contexts never differ'], 'h': 'Why the distinction is hard', 'ho': 'Incomplete descriptions of the original conditions', 'hb': ['A complete public record in every case', 'No interest in conditions'], 'e0': 'Original conditions are rarely described', 'e1': 'in full.', 'who': 'Editor Kwon', 'did': 'asks authors to state what would count as support beforehand'},
                {'k': 'true', 's': 'A surprising pattern should not automatically be treated as the hypothesis that was tested.', 'g': ('A surprising pattern is not automatically the hypothesis that was ______.', 'tested'), 'q': 'What should a surprising pattern not automatically be treated as?', 'a': 'The hypothesis that was tested', 'bad': ['Worth reporting', 'A number', 'Part of the paper'], 'h': 'Surprise and the hypothesis', 'ho': 'Reporting a surprise is not the same as having tested it', 'hb': ['Surprises must be hidden', 'Every pattern was the prior hypothesis'], 'e0': 'A surprise is not automatically the hypothesis', 'e1': 'that was tested.', 'who': 'Statistician Rahman', 'did': 'says flexible analysis can produce a striking number without dishonesty'},
                {'k': 'false', 's': 'The only problem is dishonesty.', 'g': ('The remedy may be more observations or a simpler ______.', 'claim'), 'q': 'What remedy does Rahman prefer to accusation when samples are small?', 'a': 'More observations or a simpler claim', 'bad': ['A legal penalty in every case', 'Abandoning statistics', 'Ignoring the number'], 'h': 'Beyond accusation', 'ho': 'Design, not only honesty', 'hb': ['Dishonesty is the only explanation', 'No remedy exists'], 'e0': 'The remedy may be a simpler', 'e1': 'claim.', 'who': 'Philosopher Estes', 'did': 'says a repeatable study can still measure the wrong thing'},
                {'k': 'true', 's': 'A study can be repeatable and still measure the wrong thing.', 'g': ('A repeatable study may still measure the wrong ______.', 'thing'), 'q': 'What can still be true of a study that repeats?', 'a': 'It may measure the wrong thing', 'bad': ['It is therefore a universal law', 'It must be misconduct', 'It has no result'], 'h': 'Repeatability is not enough', 'ho': 'The measure itself may be wrong', 'hb': ['Replication is the only virtue', 'A repeated result cannot mislead'], 'e0': 'A repeatable study may measure', 'e1': 'the wrong thing.', 'who': 'Funder Iqbal', 'did': 'funds repeats because a study that cannot travel becomes an expensive mistake'},
                {'k': 'true', 's': 'A cheap study that cannot travel can become an expensive mistake.', 'g': ('A study that cannot travel can become an expensive ______.', 'mistake'), 'q': 'Why does Iqbal accept the cost of multi-site repeats?', 'a': 'A study that cannot travel may be an expensive mistake later', 'bad': ['Repeats are always cheaper than the first study', 'He opposes replication', 'The text gives no reason'], 'h': 'Why pay for repeats', 'ho': 'A cheap unreproducible study can cost more later', 'hb': ['Repeats are a waste by definition', 'Only one site is ever needed'], 'e0': 'A study that cannot travel may become', 'e1': 'an expensive mistake.', 'who': 'Methodologist Serra', 'did': 'says some institution-specific phenomena should not copy perfectly'},
                {'k': 'true', 's': 'Some phenomena tied to one institution should not be expected to copy perfectly.', 'g': ('Some phenomena should not be expected to copy ______.', 'perfectly'), 'q': 'What should not be expected of every phenomenon?', 'a': 'A perfect copy elsewhere', 'bad': ['Any description', 'A method section', 'Disagreement'], 'h': 'Limits on copying', 'ho': 'Some findings are tied to an institution', 'hb': ['Every result must copy perfectly', 'Context never matters'], 'e0': 'Some phenomena should not copy', 'e1': 'perfectly elsewhere.'},
                {'k': 'false', 's': 'A failed replication proves misconduct.', 'g': ('A failure does not by itself prove ______.', 'misconduct'), 'q': 'What does a failed replication not prove by itself?', 'a': 'Misconduct', 'bad': ['That the contexts differed in a way already explained', 'That the claim needs caution', 'That records can be incomplete'], 'h': 'What failure does not mean', 'ho': 'Not proof of misconduct', 'hb': ['Automatic proof of fraud', 'Proof the topic is unreal'], 'e0': 'A failure does not by itself prove', 'e1': 'misconduct.'},
                {'k': 'ng', 's': 'Most journals now refuse all unreplicated papers.', 'g': ('Replication can slow the passage from a result to a ______.', 'recommendation'), 'q': 'What can replication slow?', 'a': 'The move from a result to a recommendation others must live with', 'bad': ['The writing of any method', 'All scientific disagreement', 'The funding of every laboratory, by a stated percentage'], 'h': 'A narrower achievement', 'ho': 'Slower movement from result to recommendation', 'hb': ['The end of recommendations', 'A ban on interesting results'], 'e0': 'Replication can slow the move toward a', 'e1': 'recommendation.'},
                {'k': 'true', 's': 'Replication raises confidence when the claim was specified and the context was comparable.', 'g': ('Confidence rises when the claim was specified and the context was ______.', 'comparable'), 'q': 'When does replication raise confidence?', 'a': 'When the claim was specified and the context was comparable', 'bad': ['In every case regardless of context', 'Only if the result is surprising', 'Never'], 'h': 'When a repeat counts', 'ho': 'A specified claim and a comparable context', 'hb': ['Any repeat, however unlike the original', 'Only a repeat that fails'], 'e0': 'Confidence rises when the context was', 'e1': 'comparable.'},
            ],
        },
        {
            'title': 'What National Income Leaves Out',
            'names': ['Economist Sen', 'Statistician Holm', 'Minister Adeyemi', 'Campaigner Rocha', 'Accountant Venn', 'Critic Paul'],
            'paragraphs': [
                _p("Gross domestic product adds up market production. It is useful for that narrow purpose and misleading when it is treated as a full account of how people live.",
                   "Economist Sen’s long-standing objection is that a rising total can coexist with lives that remain short, uneducated, or unable to appear in public without fear.",
                   "The measure records a transaction. It does not record the capability the transaction was supposed to serve."),
                _p("Statistician Holm replies that a single number is still a discipline. Without it, governments announce improvement with no common scale.",
                   "He does not claim the number is sufficient. He claims that replacing it with a paragraph of examples makes comparison across years too easy to manipulate.",
                   "The practical answer, in his view, is to publish the number beside other indicators, not instead of a narrative and not as the narrative."),
                _p("Minister Adeyemi’s ministry now releases a small set of accompanying figures: school completion, a basic health count, and a measure of hours spent fetching water.",
                   "These are not a complete moral theory. They are chosen because they can be collected again next year with roughly the same method.",
                   "Campaigner Rocha objects that unpaid care, most of it done by women, is still treated as outside the economy even when the household would collapse without it."),
                _p("Accountant Venn notes the technical difficulty. If care is given a money value, the valuation itself contains a judgement about whose time matters.",
                   "Leaving it at zero also contains a judgement. Neither choice is neutral, and the office should say which judgement it has made.",
                   "Critic Paul adds that environmental damage can raise the product when repair is sold, so a spill and its cleanup may both look like prosperity."),
                _p("The passage does not offer a replacement formula, and it does not deny that market output matters for employment and tax.",
                   "It denies that a higher product, by itself, answers whether people can do and be what they have reason to value.",
                   "A serious statistical office will keep the product, label its limits, and refuse to let one number close a political argument it cannot even see."),
            ],
            'items': [
                {'k': 'true', 's': 'GDP is misleading when treated as a full account of how people live.', 'g': ('GDP is misleading as a full account of how people ______.', 'live'), 'q': 'When is GDP described as misleading?', 'a': 'When it is treated as a full account of how people live', 'bad': ['When it is used only for market production', 'When it is never published', 'In every technical definition of a sale'], 'h': 'The limit of the total', 'ho': 'Useful for market production, misleading as a whole life', 'hb': ['A complete account of wellbeing', 'A useless number in every sense'], 'e0': 'GDP is misleading as a full account of how people', 'e1': 'live.', 'who': 'Economist Sen', 'did': 'objects that a rising total can coexist with constrained lives'},
                {'k': 'true', 's': 'The measure records a transaction, not the capability it was meant to serve.', 'g': ('The measure records a transaction, not the ______.', 'capability'), 'q': 'What does the measure fail to record?', 'a': 'The capability the transaction was supposed to serve', 'bad': ['Any price', 'The existence of a market', 'Employment in every firm'], 'h': 'Transaction and capability', 'ho': 'A sale is not the capability it was for', 'hb': ['The measure records capabilities directly', 'Transactions are irrelevant'], 'e0': 'The measure does not record the', 'e1': 'capability.', 'who': 'Statistician Holm', 'did': 'defends a single number as a discipline against vague claims of improvement'},
                {'k': 'true', 's': 'Holm wants the number published beside other indicators.', 'g': ('Holm wants the number published beside other ______.', 'indicators'), 'q': 'What does Holm recommend besides abandoning the number?', 'a': 'Publishing it beside other indicators', 'bad': ['Replacing it with examples only', 'Keeping it as the whole story', 'Stopping all statistics'], 'h': 'Beside, not instead', 'ho': 'The number next to other indicators', 'hb': ['Examples instead of any number', 'The number alone as a narrative'], 'e0': 'The number should be published beside', 'e1': 'other indicators.', 'who': 'Minister Adeyemi', 'did': 'releases figures on schooling, health, and water-fetching'},
                {'k': 'true', 's': 'Accompanying figures include hours spent fetching water.', 'g': ('One accompanying figure is hours spent fetching ______.', 'water'), 'q': 'Which accompanying figure concerns time rather than income?', 'a': 'Hours spent fetching water', 'bad': ['Company profits', 'Share prices', 'The minister’s salary'], 'h': 'What is published with the total', 'ho': 'School completion, health, and time spent fetching water', 'hb': ['A complete moral theory', 'Only market prices'], 'e0': 'The ministry counts hours spent fetching', 'e1': 'water.', 'who': 'Campaigner Rocha', 'did': 'objects that unpaid care is still treated as outside the economy'},
                {'k': 'true', 's': 'Unpaid care can hold a household together without being counted.', 'g': ('Unpaid care is still treated as ______ the economy.', 'outside'), 'q': 'How is unpaid care still treated?', 'a': 'As outside the economy', 'bad': ['As the largest item in every GDP table', 'As illegal', 'As fully measured already'], 'h': 'Care and the boundary', 'ho': 'Unpaid care left outside the economy', 'hb': ['Care fully included with no dispute', 'Care irrelevant to households'], 'e0': 'Unpaid care is treated as', 'e1': 'outside the economy.', 'who': 'Accountant Venn', 'did': 'says giving care a money value is itself a judgement'},
                {'k': 'false', 's': 'Putting care at zero is a neutral choice.', 'g': ('Leaving care at zero also contains a ______.', 'judgement'), 'q': 'What does leaving care at zero contain?', 'a': 'A judgement', 'bad': ['Neutrality', 'A physical measurement with no choice', 'An international law that the text quotes'], 'h': 'No neutral zero', 'ho': 'Zero is also a judgement', 'hb': ['Zero is neutral', 'Valuation avoids all judgement'], 'e0': 'Leaving care at zero contains', 'e1': 'a judgement.', 'who': 'Critic Paul', 'did': 'notes that a spill and its cleanup can both look like prosperity'},
                {'k': 'true', 's': 'Repair after damage can raise the product.', 'g': ('A spill and its cleanup may both look like ______.', 'prosperity'), 'q': 'How can environmental damage look like prosperity?', 'a': 'Because the repair is sold', 'bad': ['Because the environment is included as a loss automatically', 'Because GDP falls whenever there is a spill', 'The text denies any such effect'], 'h': 'Damage and repair', 'ho': 'Cleanup can be counted as gain', 'hb': ['Damage always lowers the product', 'Repair is excluded'], 'e0': 'A spill and its cleanup may both look like', 'e1': 'prosperity.'},
                {'k': 'ng', 's': 'The ministry will replace GDP within five years.', 'g': ('Market output still matters for employment and ______.', 'tax'), 'q': 'For what two reasons does market output still matter?', 'a': 'Employment and tax', 'bad': ['It is a full account of a good life', 'It is about to be abolished', 'Sport and tourism only'], 'h': 'What is not denied', 'ho': 'Output still matters for jobs and tax', 'hb': ['Output should be ignored', 'A dated plan to abolish the measure'], 'e0': 'Market output still matters for employment and', 'e1': 'tax.'},
                {'k': 'false', 's': 'A higher product by itself answers whether people can live as they have reason to value.', 'g': ('A higher product does not by itself answer what people have reason to ______.', 'value'), 'q': 'What does a higher product not answer by itself?', 'a': 'Whether people can do and be what they have reason to value', 'bad': ['Whether a transaction occurred', 'Whether tax exists', 'Whether employment can be discussed'], 'h': 'What the number cannot close', 'ho': 'A valued life is not settled by the product', 'hb': ['The product answers that question', 'Value has no place in the argument'], 'e0': 'A higher product does not answer what people have reason to', 'e1': 'value.'},
                {'k': 'true', 's': 'A serious office will keep the product and label its limits.', 'g': ('A serious office will refuse to let one number close a political ______.', 'argument'), 'q': 'What should a serious statistical office refuse to do?', 'a': 'Let one number close a political argument it cannot see', 'bad': ['Publish any figure', 'Mention employment', 'Label the limits of the product'], 'h': 'The office’s duty', 'ho': 'Keep the number, label its limits, and leave the argument open', 'hb': ['Drop the product entirely', 'Treat the product as the last word'], 'e0': 'One number should not close a political', 'e1': 'argument.'},
            ],
        },
    ],
}


def get_pack(level: str, slot: int) -> dict:
    slot = 0 if int(slot) % 2 == 0 else 1
    if level in PACKS:
        return PACKS[level][slot]
    return HIGHER[level][slot]


def titles_for(level: str) -> list[str]:
    rows = PACKS.get(level) or HIGHER.get(level) or []
    return [row['title'] for row in rows]


def passage_for(level: str, pack: dict) -> str:
    """Join the paragraphs and extend them in a voice that matches the level."""
    paragraphs = []
    for index, para in enumerate(pack['paragraphs']):
        paragraphs.append(para.strip() + ' ' + _follow(level, para, index))
    return '\n\n'.join(paragraphs)


def _follow(level: str, para: str, index: int) -> str:
    anchor = para.split('. ')[0].rstrip('.')
    band = 'A' if level in ('A1', 'A2') else ('B' if level in ('B1', 'B2') else 'C')
    frames = {
        'A': (
            f"The same idea is here again: {anchor}. The people and the place do not change. A simple question can use these words.",
            f"Read this part slowly. {anchor}. The time in the story stays the same, and no new place is added.",
            f"These lines are still about one small event. {anchor}. You do not need a different text to check the idea.",
        ),
        'B': (
            f"The paragraph stays with that point: {anchor}. It gives the same result in a slightly fuller way, without a new topic.",
            f"A reader can check the idea against this section alone. {anchor}. The example does not move to another situation.",
            f"What matters for the questions is already in these sentences. {anchor}. Later lines do not replace it.",
        ),
        'C': (
            f"The section neither widens the claim nor withdraws it: {anchor}. Any inference has to remain inside that wording.",
            f"The qualification already made is the one that counts. {anchor}. A stronger conclusion is not supplied here.",
            f"Comparison with the rest of the passage should confirm, not enlarge, the point. {anchor}. The limits stated above still hold.",
        ),
    }
    return frames[band][index % 3]


def _tfng_options():
    return [
        {'letter': 'a', 'text': 'TRUE'},
        {'letter': 'b', 'text': 'FALSE'},
        {'letter': 'c', 'text': 'NOT GIVEN'},
    ]


def build_questions(rtype: str, pack: dict, tip: str) -> list[dict]:
    items = pack['items']
    names = list(pack.get('names') or [])
    if rtype == 'tfng':
        letter = {'true': 'a', 'false': 'b', 'ng': 'c'}
        return [
            {'prompt': item['s'], 'options': _tfng_options(), 'correct': letter[item['k']], 'explanation': tip}
            for item in items
        ]
    if rtype == 'gap_fill':
        return [
            {'prompt': item['g'][0], 'options': [], 'correct': item['g'][1], 'explanation': tip}
            for item in items
        ]
    if rtype == 'mcq':
        rows = []
        for item in items:
            rows.append({
                'prompt': item['q'],
                'options': [
                    {'letter': 'a', 'text': item['a']},
                    {'letter': 'b', 'text': item['bad'][0]},
                    {'letter': 'c', 'text': item['bad'][1]},
                    {'letter': 'd', 'text': item['bad'][2]},
                ],
                'correct': 'a',
                'explanation': tip,
            })
        return rows
    if rtype == 'matching_headings':
        rows = []
        for item in items:
            rows.append({
                'prompt': item['h'],
                'options': [
                    {'letter': 'i', 'text': item['ho']},
                    {'letter': 'ii', 'text': item['hb'][0]},
                    {'letter': 'iii', 'text': item['hb'][1]},
                ],
                'correct': 'i',
                'explanation': tip,
            })
        return rows
    endings = []
    for item in items[:6]:
        endings.append(item['e1'])
    if rtype == 'matching_endings':
        rows = []
        for index, item in enumerate(items):
            if index < 6:
                opts = endings
                correct = 'abcdef'[index]
            else:
                opts = [item['e1'], item['bad'][0], item['bad'][1]]
                correct = 'a'
            rows.append({
                'prompt': item['e0'],
                'options': [
                    {'letter': 'abcdef'[i] if index < 6 else 'abcd'[i], 'text': text}
                    for i, text in enumerate(opts)
                ],
                'correct': correct,
                'explanation': tip,
            })
        return rows
    # matching names
    while len(names) < 6:
        names.append(f'Person {len(names) + 1}')
    rows = []
    named = [item for item in items if item.get('who') and item.get('did')]
    for item in named:
        rows.append({
            'prompt': item['did'][:1].upper() + item['did'][1:],
            'who': item['who'],
        })
    # two further links that reuse people already named, still using their action words
    for item in named[:4]:
        rows.append({
            'prompt': item['did'][:1].upper() + item['did'][1:],
            'who': item['who'],
        })
    rows = rows[:10]
    out = []
    for row in rows:
        who_index = names.index(row['who']) if row['who'] in names else 0
        out.append({
            'prompt': row['prompt'],
            'options': [
                {'letter': 'abcdef'[i], 'text': name}
                for i, name in enumerate(names[:6])
            ],
            'correct': 'abcdef'[who_index],
            'explanation': tip,
        })
    return out
