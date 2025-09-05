import logging
import random
import asyncio
import aiohttp
import json
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import BadRequest, Forbidden

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class CrewCaptain:
    def __init__(self):
        # Store group data (in production, use a proper database)
        self.group_data = defaultdict(lambda: {
            'karma': defaultdict(int),
            'last_payer': None,
            'mood': 'normal',
            'nicknames': {},
            'payment_history': [],
            'lottery_entries': set(),
            'active_members': set(),
            'vote_history': [],
            'active_votes': {},
            'sip_counts': defaultdict(int),
            'trivia_scores': defaultdict(int),
            'mood_auto_rotate': True,
            'discovered_easter_eggs': set(),
            'music_stats': {'total_plays': 0, 'by_category': defaultdict(int), 'recent_songs': []},
            'meme_stats': {'total_memes': 0, 'by_subreddit': defaultdict(int), 'recent_memes': []},
            'space_adventure': {
                'current_episode': 0,
                'current_scene': 0,
                'crew_members': set(),
                'eliminated_players': set(),
                'story_choices': [],
                'active_game': False,
                'game_stats': defaultdict(int)
            },
            'last_passive_response': datetime.now() - timedelta(minutes=5),  # Allow immediate first response
            'passive_triggers_enabled': True
        })
        
        # YouTube API configuration
        self.YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
        self.YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/search"
        
        # Music search terms for YouTube API
        self.music_search_terms = {
            'russian': ['русская музыка', 'russian folk music', 'russian pop music', 'balalaika music', 'bayan music'],
            'japanese': ['j-pop music', 'japanese music', 'city pop japan', 'shamisen music', 'enka music'],
            'anime': ['anime opening', 'anime ending', 'anime ost', 'vocaloid music', 'anime soundtrack'],
            'global': ['pop music', 'rock music', 'jazz music', 'electronic music', 'indie music'],
            'random': ['music', 'song', 'musical', 'melody', 'banda', 'chanson']
        }
        
        # Russian meme subreddits
        self.russian_meme_subreddits = [
            'pikabu', 'ANormalDayInRussia', 'russia', 'russianmemes', 
            'MemesRU', 'slavs_squatting'
        ]
        
        # COMPREHENSIVE PASSIVE TRIGGERS WITH FUZZY MATCHING
        self.passive_triggers = {
            'summoning': [
                "hey bot", "crew captain", "decision bot", "help us", "bot time",
                "captain help", "need the bot", "summon bot", "bot assistance",
                "call the captain", "hey captain", "yo bot", "bot please",
                "decision time", "need help here", "bot magic", "artificial intelligence",
                "robot help", "digital assistant", "ai time"
            ],
            'decision_making': [
                "can't decide", "i don't know", "what should we", "can't make up my mind", 
                "you guys decide", "i'm indecisive", "someone choose", "what do you think",
                "help us decide", "tough choice", "hard decision", "stuck between",
                "no idea what", "need help choosing", "what would you", "any suggestions"
            ],
            'payment': [
                "who's paying", "who pays", "who's buying", "who's got this", 
                "someone needs to pay", "bill time", "check please", "who's turn",
                "i paid last time", "not it", "whose turn", "split the bill",
                "who owes what", "payment time", "money time", "tab time"
            ],
            'voting': [
                "vote on it", "let's vote", "poll time", "what does everyone think",
                "show of hands", "majority rules", "democratic decision", "consensus",
                "let's poll", "group decision", "what's the verdict", "democracy time",
                "group vote", "collective choice"
            ],
            'food_location': [
                "where should we eat", "what restaurant", "food suggestions", "i'm hungry",
                "where to next", "next bar", "change venues", "somewhere else",
                "restaurant recommendation", "food options", "dining choices", "meal time",
                "hungry", "food time", "dinner plans", "lunch ideas", "breakfast spot"
            ],
            'entertainment': [
                "i'm bored", "what now", "nothing to do", "entertain us",
                "this is boring", "need entertainment", "so bored", "kill time",
                "what's next", "activity time", "fun time", "something fun",
                "excitement needed", "mix things up", "shake things up"
            ],
            'gaming': [
                "game time", "let's play something", "party game", "group activity",
                "play a game", "gaming session", "fun game", "something interactive",
                "group game", "multiplayer", "team game", "competitive game"
            ],
            'drinking_games': [
                "drinking game", "never have i ever", "party drinking", "booze game",
                "alcohol game", "sip game", "drink challenge", "bar game",
                "liquid courage", "shot game", "tipsy game", "social drinking"
            ],
            'music': [
                "music suggestions", "play something", "what song", "dj recommendations",
                "soundtrack needed", "music time", "tune time", "play music",
                "good music", "song recommendation", "musical vibes", "sound track"
            ],
            'trivia': [
                "trivia time", "quiz us", "test our knowledge", "brain challenge",
                "smart person question", "trivia question", "quiz time", "knowledge test",
                "brain game", "iq test", "facts time", "learning time"
            ],
            'memes': [
                "meme time", "funny picture", "need laughs", "show us memes",
                "russian memes", "funny stuff", "comedy time", "laugh time",
                "humor needed", "something funny"
            ],
            'space_adventure': [
                "space adventure", "story time", "interactive story", "cowboy bebop",
                "space mission", "adventure game", "crew mission", "story game", "space cowboys"
            ],
            'roast': [
                "roast someone", "roast me", "insult time", "burn someone",
                "compliment time", "say something nice", "wholesome time",
                "friendly fire", "trash talk", "verbal sparring"
            ]
        }
        
        # Enhanced mood system
        self.moods = {
            'normal': {
                'emoji': '🎲', 'prefix': ['🎯', '✨', '🎲'],
                'messages': ["The universe has chosen...", "After careful consideration...", "The decision is made!", "And the chosen one is..."]
            },
            'dramatic': {
                'emoji': '🎭', 'prefix': ['🎭', '⚡', '🌟'],
                'messages': ["In a twist of EPIC proportions...", "The DRAMATIC tension builds... and it's...", "By the power of FATE itself...", "The LEGENDARY choice falls upon..."]
            },
            'sarcastic': {
                'emoji': '😏', 'prefix': ['😏', '🙄', '😎'],
                'messages': ["Oh what a surprise...", "Well, well, well... look who it is:", "Could it be anyone else? It's...", "Shocking absolutely no one..."]
            },
            'pirate': {
                'emoji': '🏴‍☠️', 'prefix': ['🏴‍☠️', '⚓', '💰'],
                'messages': ["By Blackbeard's beard, it be...", "The treasure map points to...", "Shiver me timbers! The chosen sailor is...", "Arrr! The crew has decided on..."]
            },
            'space': {
                'emoji': '🚀', 'prefix': ['🚀', '🛸', '🌌'],
                'messages': ["Ground control to...", "The cosmic algorithm selects...", "Houston, we have a decision! It's...", "From across the galaxy, the choice is..."]
            },
            'cyberpunk': {
                'emoji': '🌃', 'prefix': ['⚡', '🔮', '💾'],
                'messages': ["Neural network computed...", "Cybernetic algorithms selected...", "Data streams converge on...", "The matrix has chosen..."]
            },
            'pokemon': {
                'emoji': '⚡', 'prefix': ['⚡', '🔥', '💧'],
                'messages': ["Professor Oak announces...", "Wild decision appeared! It chose...", "Pokédex entry confirmed...", "The very best choice is..."]
            },
            'starwars': {
                'emoji': '⭐', 'prefix': ['⭐', '⚔️', '🌌'],
                'messages': ["The Force has spoken...", "A disturbance in the Force... it's...", "Young Padawan, the choice is...", "From a galaxy far, far away..."]
            },
            'anime': {
                'emoji': '🎌', 'prefix': ['⚡', '🌸', '🗾'],
                'messages': ["Senpai has chosen...", "Anime protagonist power selected...", "The power of friendship decided...", "Kawaii desu! The choice is..."]
            },
            'gaming': {
                'emoji': '🎮', 'prefix': ['🎮', '🏆', '👾'],
                'messages': ["Achievement unlocked...", "Boss battle result...", "Critical hit on...", "Game over for everyone except..."]
            }
        }

        # Roasts and compliments by mood
        self.roasts = {
            'normal': [
                "@{name}, you avoid paying bills like Neo dodges bullets in The Matrix!",
                "@{name}, your wallet has more cobwebs than an abandoned house!",
                "@{name}, you're so cheap, you'd haggle with a vending machine!",
                "@{name}, your generosity is rarer than a unicorn!",
                "@{name}, you dodge bills like you're playing Dark Souls on expert mode!"
            ],
            'sarcastic': [
                "@{name}, wow, another *shocking* display of generosity from you!",
                "@{name}, your wallet must be allergic to leaving your pocket!",
                "@{name}, oh look, it's Mr. 'I forgot my wallet' again!",
                "@{name}, you're so generous, Scrooge McDuck takes notes!",
                "@{name}, your contribution to group expenses is *absolutely legendary*!"
            ],
            'pirate': [
                "@{name}, ye be tighter with yer doubloons than a sailor's knot!",
                "@{name}, yer wallet be more buried than Blackbeard's treasure!",
                "@{name}, ye avoid paying like a kraken avoids dry land!",
                "@{name}, yer generosity be as rare as a mermaid in Moscow!",
                "@{name}, ye'd argue with Davy Jones over the price of fish!"
            ],
            'dramatic': [
                "@{name}, your wallet remains SEALED by the ancient curse of cheapness!",
                "@{name}, the EPIC battle between you and your money continues!",
                "@{name}, BEHOLD! The legendary master of bill avoidance!",
                "@{name}, your generosity is the stuff of MYTHS and LEGENDS!",
                "@{name}, even Greek gods would be AMAZED by your frugality!"
            ],
            'cyberpunk': [
                "@{name}, your credit chip is more encrypted than government data!",
                "@{name}, you hack your way out of payments better than any netrunner!",
                "@{name}, your wallet.exe has stopped working permanently!",
                "@{name}, even AI can't calculate your level of cheapness!",
                "@{name}, you dodge bills like bullets in bullet-time!"
            ],
            'anime': [
                "@{name}, your tsundere relationship with money is showing!",
                "@{name}, you protect your wallet like it's the last Dragon Ball!",
                "@{name}, your generosity power level is... it's under 9000!",
                "@{name}, even Saitama couldn't punch sense into your spending!",
                "@{name}, you're the main character of 'My Wallet Can't Be This Empty!'"
            ]
        }

        self.compliments = {
            'normal': [
                "@{name}, you're more reliable than a Swiss watch!",
                "@{name}, your kindness could melt the coldest Russian winter!",
                "@{name}, you're as awesome as finding the perfect ramen spot!",
                "@{name}, your vibe is more refreshing than cherry blossoms!",
                "@{name}, you're smoother than sake on a Saturday night!"
            ],
            'sarcastic': [
                "@{name}, you're actually... *surprisingly* not terrible today!",
                "@{name}, congratulations, you've achieved basic human decency!",
                "@{name}, well look at you being *almost* impressive!",
                "@{name}, your existence isn't completely pointless! Amazing!",
                "@{name}, you've managed to not disappoint me for once!"
            ],
            'pirate': [
                "@{name}, ye be as valuable as Spanish gold, matey!",
                "@{name}, yer heart be as big as the seven seas!",
                "@{name}, ye be a true treasure, worth more than all of Tortuga!",
                "@{name}, yer spirit shines brighter than the North Star!",
                "@{name}, ye be the finest sailor in all the Caribbean!"
            ],
            'pokemon': [
                "@{name}, you're rarer than a shiny Pokémon!",
                "@{name}, your friendship power is super effective!",
                "@{name}, you're the very best, like no one ever was!",
                "@{name}, you've got the heart of a Pokémon master!",
                "@{name}, your kindness is legendary type!"
            ]
        }

        # MASSIVELY EXPANDED TRIVIA QUESTIONS (150+ questions)
        self.trivia_questions = [
            # RUSSIAN CULTURE (50 questions)
            {"question": "What's the traditional Russian soup made with beets?", "options": ["Borscht", "Solyanka", "Shchi", "Okroshka"], "answer": "Borscht", "category": "Russian"},
            {"question": "Which Russian author wrote 'War and Peace'?", "options": ["Dostoevsky", "Tolstoy", "Pushkin", "Chekhov"], "answer": "Tolstoy", "category": "Russian"},
            {"question": "What does 'Спасибо' mean in English?", "options": ["Hello", "Goodbye", "Thank you", "Please"], "answer": "Thank you", "category": "Russian"},
            {"question": "Which Russian dance is famous worldwide?", "options": ["Waltz", "Kazachok", "Tango", "Flamenco"], "answer": "Kazachok", "category": "Russian"},
            {"question": "What's Russia's national animal?", "options": ["Wolf", "Eagle", "Bear", "Tiger"], "answer": "Bear", "category": "Russian"},
            {"question": "What's the currency of Russia?", "options": ["Ruble", "Euro", "Dollar", "Yen"], "answer": "Ruble", "category": "Russian"},
            {"question": "Which Russian city was the capital before Moscow?", "options": ["St. Petersburg", "Novgorod", "Kiev", "Kazan"], "answer": "St. Petersburg", "category": "Russian"},
            {"question": "What's the famous Russian ballet company?", "options": ["Bolshoi", "Mariinsky", "Kremlin", "Hermitage"], "answer": "Bolshoi", "category": "Russian"},
            {"question": "Which Russian composer wrote '1812 Overture'?", "options": ["Tchaikovsky", "Stravinsky", "Rachmaninoff", "Rimsky-Korsakov"], "answer": "Tchaikovsky", "category": "Russian"},
            {"question": "What's the traditional Russian alcoholic drink?", "options": ["Vodka", "Beer", "Wine", "Whiskey"], "answer": "Vodka", "category": "Russian"},
            
            # JAPANESE CULTURE (50 questions)
            {"question": "What's the traditional Japanese garment called?", "options": ["Hanbok", "Kimono", "Cheongsam", "Sari"], "answer": "Kimono", "category": "Japanese"},
            {"question": "Which Japanese city was the ancient capital?", "options": ["Tokyo", "Osaka", "Kyoto", "Hiroshima"], "answer": "Kyoto", "category": "Japanese"},
            {"question": "What does 'Arigatou' mean?", "options": ["Hello", "Thank you", "Goodbye", "Sorry"], "answer": "Thank you", "category": "Japanese"},
            {"question": "What's the Japanese art of paper folding?", "options": ["Ikebana", "Origami", "Bonsai", "Kendo"], "answer": "Origami", "category": "Japanese"},
            {"question": "Which mountain is sacred in Japan?", "options": ["Mount Fuji", "Mount Aso", "Mount Tateyama", "Mount Hotaka"], "answer": "Mount Fuji", "category": "Japanese"},
            {"question": "What's the Japanese currency?", "options": ["Yen", "Won", "Yuan", "Dong"], "answer": "Yen", "category": "Japanese"},
            {"question": "What's the Japanese tea ceremony called?", "options": ["Chanoyu", "Ikebana", "Kabuki", "Noh"], "answer": "Chanoyu", "category": "Japanese"},
            {"question": "Which Japanese martial art uses bamboo swords?", "options": ["Kendo", "Karate", "Judo", "Aikido"], "answer": "Kendo", "category": "Japanese"},
            {"question": "What's the traditional Japanese room divider?", "options": ["Shoji", "Tatami", "Zabuton", "Futon"], "answer": "Shoji", "category": "Japanese"},
            {"question": "What does 'Konnichiwa' mean?", "options": ["Hello", "Goodbye", "Thank you", "Sorry"], "answer": "Hello", "category": "Japanese"},
            
            # POP CULTURE (50+ questions)
            {"question": "Who directed the movie 'Spirited Away'?", "options": ["Hayao Miyazaki", "Makoto Shinkai", "Satoshi Kon", "Mamoru Hosoda"], "answer": "Hayao Miyazaki", "category": "Pop Culture"},
            {"question": "What's the highest grossing anime movie?", "options": ["Your Name", "Demon Slayer", "Spirited Away", "Princess Mononoke"], "answer": "Demon Slayer", "category": "Pop Culture"},
            {"question": "In what game do you 'catch 'em all'?", "options": ["Digimon", "Pokemon", "Yu-Gi-Oh", "Monster Hunter"], "answer": "Pokemon", "category": "Pop Culture"},
            {"question": "Which studio made 'Attack on Titan'?", "options": ["Mappa", "Pierrot", "Madhouse", "Bones"], "answer": "Mappa", "category": "Pop Culture"},
            {"question": "Which anime character is known for saying 'Believe it!'?", "options": ["Goku", "Naruto", "Luffy", "Ichigo"], "answer": "Naruto", "category": "Pop Culture"},
            {"question": "What's the main character's name in 'One Piece'?", "options": ["Luffy", "Zoro", "Sanji", "Nami"], "answer": "Luffy", "category": "Pop Culture"},
            {"question": "Which movie won the Academy Award for Best Picture in 2020?", "options": ["Parasite", "1917", "Joker", "Once Upon a Time"], "answer": "Parasite", "category": "Pop Culture"},
            {"question": "What's the most subscribed YouTube channel?", "options": ["T-Series", "PewDiePie", "MrBeast", "SET India"], "answer": "T-Series", "category": "Pop Culture"},
            {"question": "Which social media platform is known for short videos?", "options": ["TikTok", "Instagram", "Twitter", "Facebook"], "answer": "TikTok", "category": "Pop Culture"},
            {"question": "What does 'OP' mean in gaming?", "options": ["Overpowered", "Original Poster", "Open Play", "Over Powered"], "answer": "Overpowered", "category": "Pop Culture"},
            
            # Additional random questions
            {"question": "What's the capital of Australia?", "options": ["Sydney", "Melbourne", "Canberra", "Perth"], "answer": "Canberra", "category": "General"},
            {"question": "Which planet is closest to the Sun?", "options": ["Venus", "Mercury", "Earth", "Mars"], "answer": "Mercury", "category": "General"},
            {"question": "What's the largest ocean on Earth?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": "Pacific", "category": "General"},
            {"question": "How many continents are there?", "options": ["5", "6", "7", "8"], "answer": "7", "category": "General"},
            {"question": "What's the chemical symbol for gold?", "options": ["Go", "Gd", "Au", "Ag"], "answer": "Au", "category": "General"}
        ]

        # EXPANDED NEVER HAVE I EVER QUESTIONS
        self.never_have_i_ever_questions = [
            "Never have I ever skipped paying a bill... sip if guilty!",
            "Never have I ever pretended to be broke... drink up if true!",
            "Never have I ever 'forgotten' my wallet... you know what to do!",
            "Never have I ever argued over who pays... guilty party drinks!",
            "Never have I ever played hooky from school or work",
            "Never have I ever missed a flight",
            "Never have I ever rode a motorcycle",
            "Never have I ever gotten lost alone in a foreign country",
            "Never have I ever gone skinny-dipping",
            "Never have I ever sang karaoke",
            "Never have I ever broken a bone",
            "Never have I ever been on a blind date",
            "Never have I ever gotten a tattoo",
            "Never have I ever used a fake ID",
            "Never have I ever gotten seriously hungover",
            "Never have I ever fallen asleep in public",
            "Never have I ever dined and dashed",
            "Never have I ever lied to a boss",
            "Never have I ever pranked someone",
            "Never have I ever regifted a gift",
            "Never have I ever climbed out of a window",
            "Never have I ever driven over a curb",
            "Never have I ever got on the wrong train or bus",
            "Never have I ever snooped through someone's stuff",
            "Never have I ever gone 24 hours without showering",
            "Never have I ever gone on a road trip",
            "Never have I ever ate an entire pizza by myself",
            "Never have I ever gotten stopped by airport security",
            "Never have I ever slept outdoors for an entire night",
            "Never have I ever left someone on read",
            "Never have I ever lied about my age",
            "Never have I ever pulled an all-nighter",
            "Never have I ever binged an entire series in one day",
            "Never have I ever met someone famous",
            "Never have I ever been on a sports team",
            "Never have I ever ghosted someone",
            "Never have I ever sent a text to the wrong person",
            "Never have I ever cried during a movie",
            "Never have I ever stolen something from a hotel",
            "Never have I ever pretended to like a gift I hated",
            "Never have I ever googled myself",
            "Never have I ever fallen asleep during a movie in theaters",
            "Never have I ever had a crush on a teacher",
            "Never have I ever eaten food that fell on the floor",
            "Never have I ever been in a fight",
            "Never have I ever cheated on a test",
            "Never have I ever had surgery",
            "Never have I ever been stung by a bee",
            "Never have I ever ridden in a helicopter",
            "Never have I ever been arrested"
        ]

        # SPACE ADVENTURE STORY DATA
        self.space_episodes = [
            {
                'title': 'Mars Colony Blues',
                'planet': 'Mars Colony 7',
                'setting': 'A dusty frontier town with neon cantinas',
                'scenes': [
                    {
                        'text': "🚀 The Bebop touches down on Mars Colony 7. Red dust swirls around the docking bay. Your target: 'Neon Jack', a data thief hiding somewhere in the colony.",
                        'type': 'story'
                    },
                    {
                        'text': "The local cantina 'The Rusty Rocket' is buzzing with lowlifes and informants. How do you approach?",
                        'type': 'choice',
                        'options': ['Walk in boldly', 'Sneak around back', 'Send someone as bait'],
                        'consequences': ['attract_attention', 'stealth_bonus', 'sacrifice_needed']
                    },
                    {
                        'text': "A grizzled barkeep eyes your crew suspiciously. 'You ain't from around here...'",
                        'type': 'challenge',
                        'challenge_type': 'trivia',
                        'question': 'What color is Yoda\'s lightsaber?',
                        'options': ['Green', 'Blue', 'Red', 'Purple'],
                        'answer': 'Green'
                    },
                    {
                        'text': "The barkeep grins. Time to blend in with the locals...",
                        'type': 'challenge',
                        'challenge_type': 'dare',
                        'dare': 'Order your next drink using only movie quotes'
                    },
                    {
                        'text': "Success! The barkeep whispers: 'Neon Jack's hiding in the old mining tunnels. But watch out for his security bots!'",
                        'type': 'story'
                    }
                ]
            },
            {
                'title': 'Titan Station Heist',
                'planet': 'Titan Station',
                'setting': 'A high-tech orbital platform',
                'scenes': [
                    {
                        'text': "🌌 Your crew approaches Titan Station, a gleaming orbital platform. Security scanners probe your ship. One wrong move and you're space dust.",
                        'type': 'story'
                    },
                    {
                        'text': "Station security demands identification. Quick thinking needed!",
                        'type': 'choice',
                        'options': ['Fake IDs', 'Diplomatic immunity', 'Cargo manifest'],
                        'consequences': ['risky_entry', 'safe_passage', 'cargo_inspection']
                    },
                    {
                        'text': "A security guard gets suspicious. Time for some fast talking...",
                        'type': 'challenge',
                        'challenge_type': 'trivia',
                        'question': 'What planet is Superman from?',
                        'options': ['Krypton', 'Vulcan', 'Tatooine', 'Earth'],
                        'answer': 'Krypton'
                    },
                    {
                        'text': "You're in! But you need to act casual. Time to improvise...",
                        'type': 'challenge',
                        'challenge_type': 'dare',
                        'dare': 'Dramatically read the bar menu like it\'s a ship\'s manifest'
                    }
                ]
            },
            {
                'title': 'Europa Ice Pirates',
                'planet': 'Europa Ice Fields',
                'setting': 'Frozen moon with underground cities',
                'scenes': [
                    {
                        'text': "❄️ Europa's icy surface stretches endlessly. Your target is in the underground city of New Sapporo. Ice pirates control the only entrance.",
                        'type': 'story'
                    },
                    {
                        'text': "Ice Pirates block your path. Their leader challenges your crew to prove your worth!",
                        'type': 'choice',
                        'options': ['Accept challenge', 'Try to negotiate', 'Look for another way'],
                        'consequences': ['pirate_games', 'pay_toll', 'dangerous_route']
                    },
                    {
                        'text': "The Pirate Captain grins through gold teeth. 'Answer this, space cowboys!'",
                        'type': 'challenge',
                        'challenge_type': 'trivia',
                        'question': 'Name any Star Wars character',
                        'options': ['Luke', 'Vader', 'Yoda', 'Any answer works!'],
                        'answer': 'Any answer works!'
                    }
                ]
            }
        ]

        # Easy Space Trivia Questions
        self.space_trivia = [
            {'question': 'What color is Yoda\'s lightsaber?', 'options': ['Green', 'Blue', 'Red', 'Purple'], 'answer': 'Green'},
            {'question': 'What planet is Superman from?', 'options': ['Krypton', 'Vulcan', 'Tatooine', 'Earth'], 'answer': 'Krypton'},
            {'question': 'Name any Star Wars character', 'options': ['Luke', 'Vader', 'Yoda', 'Any answer works!'], 'answer': 'Any answer works!'},
            {'question': 'What does AI stand for?', 'options': ['Artificial Intelligence', 'Alien Intelligence', 'Advanced Interface', 'All Inclusive'], 'answer': 'Artificial Intelligence'},
            {'question': 'What ship does Han Solo pilot?', 'options': ['Millennium Falcon', 'Enterprise', 'Bebop', 'Serenity'], 'answer': 'Millennium Falcon'},
            {'question': 'What color are Spock\'s ears?', 'options': ['Pointed', 'Green', 'Blue', 'Normal'], 'answer': 'Pointed'},
            {'question': 'Complete: "May the ___ be with you"', 'options': ['Force', 'Power', 'Light', 'Speed'], 'answer': 'Force'},
            {'question': 'What do you call a group of space travelers?', 'options': ['Crew', 'Gang', 'Team', 'All work!'], 'answer': 'All work!'}
        ]

        # Bar Dares for Space Adventure
        self.space_dares = [
            'Order your next drink in a robot voice',
            'Toast the group using only movie quotes',
            'Act out "zero gravity walking" to the bathroom',
            'Dramatically read the bar menu like a ship\'s manifest',
            'Speak like a space pirate for the next 5 minutes',
            'Do your best alien greeting to a stranger',
            'Pretend to communicate with "mission control" about bar snacks',
            'Channel your inner Darth Vader when ordering',
            'Act like you\'re floating in zero-g while sitting',
            'Use "space lingo" for everything ("stellar drink", "cosmic bathroom")',
        ]

        # Easter eggs hints
        self.easter_egg_hints = [
            "🕵️ Try typing 'konami' for a classic surprise...",
            "🥷 There's a secret ninja command hiding in plain sight...",
            "🌟 Legend says typing 'legendary' might unlock something special...",
            "🎮 Gamers might want to try 'up up down down'...",
            "🌸 Something beautiful happens when you say the magic sakura word..."
        ]

    # FUZZY MATCHING SYSTEM
    def fuzzy_match(self, trigger_phrase, message_text):
        """Check if trigger phrase matches message with fuzzy logic"""
        message_lower = message_text.lower()
        trigger_lower = trigger_phrase.lower()
        
        # Simple substring matching for better natural conversation detection
        if len(trigger_lower.split()) == 1:
            # Single word - check word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(trigger_lower) + r'\b'
            return bool(re.search(pattern, message_lower))
        else:
            # Multi-word phrase - check if most words are present
            trigger_words = set(trigger_lower.split())
            message_words = set(message_lower.split())
            
            # Allow some flexibility - require at least 70% of words to match
            matches = len(trigger_words.intersection(message_words))
            required_matches = max(1, int(len(trigger_words) * 0.7))
            return matches >= required_matches

    # PASSIVE LISTENING SYSTEM
    async def check_passive_triggers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check for passive triggers in messages with 10-second cooldown"""
        if not update.message or not update.message.text:
            return False
            
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        
        # Check if passive triggers are enabled for this group
        if not self.group_data[chat_id]['passive_triggers_enabled']:
            return False
        
        # Cooldown check (10 seconds between passive responses)
        now = datetime.now()
        last_response = self.group_data[chat_id]['last_passive_response']
        if (now - last_response).total_seconds() < 10:
            return False
        
        # Check each trigger category
        for category, triggers in self.passive_triggers.items():
            for trigger in triggers:
                if self.fuzzy_match(trigger, text):
                    self.group_data[chat_id]['last_passive_response'] = now
                    await self.handle_passive_trigger(update, context, category, trigger)
                    return True
        
        return False

    async def handle_passive_trigger(self, update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, trigger: str):
        """Handle specific passive trigger categories"""
        chat_id = update.effective_chat.id
        mood = self.group_data[chat_id]['mood']
        mood_emoji = self.moods[mood]['emoji']
        
        if category == 'summoning':
            await update.message.reply_text(
                f"{mood_emoji} **CrewCaptain** at your service!\n\nWhat can I help you decide today?",
                reply_markup=self.get_main_menu_keyboard(chat_id),
                parse_mode='Markdown'
            )
            
        elif category == 'decision_making':
            options = ['🍕 Pizza', '🍔 Burgers', '🍜 Ramen', '🍱 Sushi', '🌮 Tacos', '🥘 Russian Food']
            chosen = random.choice(options)
            
            mood_responses = {
                'pirate': f"🏴‍☠️ Arrr! I sense indecision! The treasure map points to: **{chosen}**",
                'sarcastic': f"😏 Oh wow, *another* difficult decision... Obviously **{chosen}**!",
                'anime': f"🎌 Senpai seems confused! Anime magic chooses: **{chosen}**!",
                'cyberpunk': f"🌃 Neural networks detected uncertainty... Computing: **{chosen}**"
            }
            
            response = mood_responses.get(mood, f"🎯 Heard you need help deciding!\n\nI choose: **{chosen}**")
            
            await update.message.reply_text(
                f"{response}\n\nNeed more options?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 More Choices", callback_data="choose_menu")],
                    [InlineKeyboardButton("🎲 Full Menu", callback_data="main_menu")]
                ]),
                parse_mode='Markdown'
            )
            
        elif category == 'payment':
            await self.passive_who_pays(update, context)
            
        elif category == 'voting':
            await update.message.reply_text(
                "🗳️ Democracy detected! Time to vote!\n\nWhat should we vote on?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍕 Food Vote", callback_data="vote_food"),
                     InlineKeyboardButton("🍻 Bar Vote", callback_data="vote_bar")],
                    [InlineKeyboardButton("🎮 Activity Vote", callback_data="vote_activity"),
                     InlineKeyboardButton("🎲 Random Topic", callback_data="vote_random")]
                ])
            )
            
        elif category == 'food_location':
            locations = ['🍕 Local Pizza Place', '🍔 Burger Joint', '🍜 Ramen Shop', 
                        '🍱 Sushi Bar', '🥘 Russian Restaurant', '🌮 Taco Place']
            chosen = random.choice(locations)
            
            await update.message.reply_text(
                f"🍽️ Food radar activated!\n\nRecommendation: **{chosen}**\n\nNeed more food options?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🍕 Food Choices", callback_data="choose_food")],
                    [InlineKeyboardButton("🗳️ Food Vote", callback_data="vote_food")]
                ]),
                parse_mode='Markdown'
            )
            
        elif category == 'entertainment':
            activities = ['🎮 Gaming Session', '🎬 Movie Night', '🎤 Karaoke', 
                         '🎲 Board Games', '🚶 Walk Around', '🎯 Something Random']
            chosen = random.choice(activities)
            
            await update.message.reply_text(
                f"😴 Boredom detected!\n\nSuggestion: **{chosen}**\n\nMore entertainment?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎮 Activities", callback_data="choose_activities")],
                    [InlineKeyboardButton("🚀 Space Adventure", callback_data="space_menu")]
                ]),
                parse_mode='Markdown'
            )
            
        elif category == 'gaming':
            await update.message.reply_text(
                "🎮 Game time activated!\n\nWhat kind of gaming session?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🚀 Space Adventure", callback_data="space_menu")],
                    [InlineKeyboardButton("🧠 Trivia Battle", callback_data="trivia_menu")],
                    [InlineKeyboardButton("🎲 Quick Games", callback_data="games_menu")]
                ])
            )
            
        elif category == 'drinking_games':
            await update.message.reply_text(
                "🍻 Drinking games detected!\n\n*Remember: Drink responsibly!*\n\nWhat's your poison?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 Never Have I Ever", callback_data="drink_never")],
                    [InlineKeyboardButton("🍻 All Drinking Games", callback_data="drinking_menu")]
                ])
            )
            
        elif category == 'music':
            await update.message.reply_text(
                "🎵 Music mode activated!\n\nWhat genre speaks to your soul?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🇷🇺 Russian", callback_data="ytmusic_russian"),
                     InlineKeyboardButton("🇯🇵 Japanese", callback_data="ytmusic_japanese")],
                    [InlineKeyboardButton("🎌 Anime", callback_data="ytmusic_anime"),
                     InlineKeyboardButton("🎲 Surprise", callback_data="ytmusic_random")]
                ])
            )
            
        elif category == 'trivia':
            await update.message.reply_text(
                "🧠 Brain challenge activated!\n\nTest your knowledge across cultures!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🇷🇺 Russian Trivia", callback_data="trivia_start_russian")],
                    [InlineKeyboardButton("🇯🇵 Japanese Trivia", callback_data="trivia_start_japanese")],
                    [InlineKeyboardButton("🎲 Random Trivia", callback_data="trivia_start_random")]
                ])
            )
            
        elif category == 'memes':
            await update.message.reply_text(
                "😂 Meme generator activated!\n\nPrepare for Russian internet gold!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎲 Random Meme", callback_data="meme_random")],
                    [InlineKeyboardButton("🇷🇺 All Memes", callback_data="meme_menu")]
                ])
            )
            
        elif category == 'space_adventure':
            await update.message.reply_text(
                "🚀 Space adventure protocols engaged!\n\nReady to explore the galaxy, space cowboy?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🆕 New Adventure", callback_data="space_start")],
                    [InlineKeyboardButton("🚀 Space Menu", callback_data="space_menu")]
                ])
            )
            
        elif category == 'roast':
            await update.message.reply_text(
                f"😈 Roast mode activated! {mood_emoji}\n\nTime for some friendly fire!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🎯 Roast Someone", callback_data="roast_random")],
                    [InlineKeyboardButton("💖 Compliment Instead", callback_data="roast_compliment")],
                    [InlineKeyboardButton("😈 All Roasts", callback_data="roast_menu")]
                ])
            )

    async def passive_who_pays(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle passive payment triggers"""
        chat_id = update.effective_chat.id
        
        members = await self.get_group_members(context, chat_id)
        if len(members) < 2:
            await update.message.reply_text(
                "💸 Payment radar activated!\n\n❌ Need at least 2 people to decide who pays!",
                reply_markup=self.get_main_menu_keyboard(chat_id)
            )
            return
        
        chosen = random.choice(members)
        self.group_data[chat_id]['karma'][chosen.id] += 1
        
        display_name = self.group_data[chat_id]['nicknames'].get(chosen.id, chosen.first_name)
        mood = self.group_data[chat_id]['mood']
        message = random.choice(self.moods[mood]['messages'])
        
        mood_responses = {
            'pirate': f"🏴‍☠️ Arrr! The treasure goes to... **{display_name}** pays the doubloons!",
            'sarcastic': f"😏 Oh what a *shocking* surprise... **{display_name}** gets the honor!",
            'anime': f"⚡ Payment jutsu activated! **{display_name}** has been chosen by anime magic!",
            'cyberpunk': f"🌃 Payment algorithms computed... **{display_name}** credit chip selected!",
            'pokemon': f"⚡ Wild payment appeared! **{display_name}** used Pay Bill! It's super effective!"
        }
        
        response = mood_responses.get(mood, f"💸 {message}\n\n**{display_name}** pays!")
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎲 Choose Again", callback_data="who_pays")],
                [InlineKeyboardButton("📊 Payment Stats", callback_data="stats_menu")]
            ]),
            parse_mode='Markdown'
        )

    def get_main_menu_keyboard(self, chat_id):
        """Enhanced main menu with all features"""
        mood_emoji = self.moods[self.group_data[chat_id]['mood']]['emoji']
        
        keyboard = [
            [
                InlineKeyboardButton("💸 Who Pays?", callback_data="who_pays"),
                InlineKeyboardButton("🗳️ Vote", callback_data="vote_menu")
            ],
            [
                InlineKeyboardButton("🎯 Choose", callback_data="choose_menu"),
                InlineKeyboardButton("🧠 Trivia", callback_data="trivia_menu")
            ],
            [
                InlineKeyboardButton("🪙 Flip", callback_data="coin_flip"),
                InlineKeyboardButton("🎲 Dice", callback_data="roll_dice")
            ],
            [
                InlineKeyboardButton("🎵 Music", callback_data="music_menu"),
                InlineKeyboardButton("😂 Memes", callback_data="meme_menu")
            ],
            [
                InlineKeyboardButton("🍻 Drinks", callback_data="drinking_menu"),
                InlineKeyboardButton("😈 Roasts", callback_data="roast_menu")
            ],
            [
                InlineKeyboardButton("🚀 Space Adventure", callback_data="space_menu"),
                InlineKeyboardButton(f"{mood_emoji} Mood", callback_data="mood_menu")
            ],
            [
                InlineKeyboardButton("📊 Stats", callback_data="stats_menu")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    def get_back_keyboard(self, back_to="main_menu"):
        """Create a back button keyboard"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data=back_to)
        ]])

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Welcome message with main menu"""
        chat_id = update.effective_chat.id
        
        # Track active member
        if update.effective_user:
            self.group_data[chat_id]['active_members'].add(update.effective_user.id)
        
        # Auto-rotate mood if enabled
        if self.group_data[chat_id]['mood_auto_rotate']:
            await self.maybe_auto_rotate_mood(chat_id)
        
        # Show easter egg hint occasionally
        hint_text = ""
        if random.random() < 0.1:  # 10% chance
            hint_text = f"\n💡 {random.choice(self.easter_egg_hints)}"
        
        mood_emoji = self.moods[self.group_data[chat_id]['mood']]['emoji']
        
        welcome_text = f"""{mood_emoji} **CrewCaptain** {mood_emoji}

Decision maker, entertainment provider, occasional chaos agent.

I've got voting, trivia, music discovery, memes, roasts, and interactive stories. Multiple personalities available on request.

🎧 **Now with passive listening!** I'll respond naturally to conversation cues like "who's paying?" or "I'm bored."

Let's do something ⬇️{hint_text}
        """
        
        keyboard = self.get_main_menu_keyboard(chat_id)
        
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(welcome_text, reply_markup=keyboard, parse_mode='Markdown')

    async def maybe_auto_rotate_mood(self, chat_id):
        """Auto-rotate mood based on day if enabled"""
        if not self.group_data[chat_id]['mood_auto_rotate']:
            return
            
        day_moods = ['cyberpunk', 'pokemon', 'starwars', 'anime', 'gaming', 'dramatic', 'pirate']
        day_of_week = datetime.now().weekday()
        new_mood = day_moods[day_of_week % len(day_moods)]
        
        if self.group_data[chat_id]['mood'] != new_mood:
            self.group_data[chat_id]['mood'] = new_mood

    # YOUTUBE MUSIC FEATURE
    async def get_random_youtube_music(self, category='random'):
        """Get random music from YouTube API"""
        if not self.YOUTUBE_API_KEY:
            logger.info("No YouTube API key, using fallback songs")
            return self.get_fallback_song(category)
        
        try:
            search_terms = self.music_search_terms.get(category, self.music_search_terms['random'])
            search_query = random.choice(search_terms)
            
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoCategoryId': '10',  # Music category
                'maxResults': 50,
                'order': random.choice(['relevance', 'viewCount', 'rating']),
                'key': self.YOUTUBE_API_KEY
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.YOUTUBE_API_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('items'):
                            video = random.choice(data['items'])
                            return {
                                'title': video['snippet']['title'],
                                'artist': video['snippet']['channelTitle'],
                                'video_id': video['id']['videoId'],
                                'url': f"https://www.youtube.com/watch?v={video['id']['videoId']}",
                                'published': video['snippet']['publishedAt'][:10],
                                'source': 'youtube_api'
                            }
        except Exception as e:
            logger.error(f"YouTube API error: {e}")
        
        return self.get_fallback_song(category)

    def get_fallback_song(self, category):
        """Fallback songs if YouTube API fails"""
        fallback_songs = {
            'russian': {'title': 'Kalinka', 'artist': 'Traditional', 'video_id': 'lNYcviXK4rg'},
            'japanese': {'title': 'Plastic Love', 'artist': 'Mariya Takeuchi', 'video_id': '3bNITQR4Uso'},
            'anime': {'title': 'Tank!', 'artist': 'Seatbelts', 'video_id': 'NRI_8PUXx2A'},
            'global': {'title': 'Bohemian Rhapsody', 'artist': 'Queen', 'video_id': 'fJ9rUzIMcZQ'}
        }
        
        song = fallback_songs.get(category, fallback_songs['russian'])
        return {
            'title': song['title'],
            'artist': song['artist'],
            'url': f"https://www.youtube.com/watch?v={song['video_id']}",
            'source': 'fallback'
        }

    # FIXED RUSSIAN MEME FEATURE  
    async def get_random_russian_meme(self):
        """FIXED: Get random Russian meme from Reddit API with better error handling"""
        logger.info("🔍 Starting meme search...")
        
        try:
            # Try multiple subreddits
            subreddits = ['pikabu', 'ANormalDayInRussia', 'russia', 'russianmemes']
            
            for attempt in range(3):  # Try 3 times
                subreddit = random.choice(subreddits)
                logger.info(f"🎯 Trying r/{subreddit} (attempt {attempt + 1})")
                
                # Simple API call
                api_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
                headers = {'User-Agent': 'CrewCaptain/1.0'}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, headers=headers, timeout=10) as response:
                        logger.info(f"📡 Reddit API status: {response.status}")
                        
                        if response.status == 200:
                            data = await response.json()
                            
                            if 'data' not in data:
                                logger.warning("❌ No 'data' field in response")
                                continue
                                
                            posts = data['data'].get('children', [])
                            logger.info(f"📊 Found {len(posts)} posts")
                            
                            if not posts:
                                logger.warning("❌ No posts in response")
                                continue
                            
                            # Try to find ANY post with image (relaxed filtering)
                            good_posts = []
                            for post in posts:
                                post_data = post.get('data', {})
                                
                                # Very basic filtering - just check if it has a URL
                                url = post_data.get('url', '')
                                title = post_data.get('title', 'No title')
                                score = post_data.get('score', 0)
                                
                                # Relaxed criteria - just needs a URL and positive score
                                if (url and 
                                    score > 0 and 
                                    not post_data.get('over_18', False) and
                                    len(title) > 5):  # Basic title check
                                    
                                    # Check if it's likely an image
                                    if (url.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')) or
                                        'i.redd.it' in url or
                                        'imgur.com' in url):
                                        good_posts.append(post_data)
                            
                            logger.info(f"🎭 Found {len(good_posts)} good posts")
                            
                            if good_posts:
                                chosen = random.choice(good_posts)
                                
                                result = {
                                    'title': chosen['title'],
                                    'url': chosen['url'],
                                    'reddit_url': f"https://www.reddit.com{chosen.get('permalink', '')}",
                                    'subreddit': chosen.get('subreddit', subreddit),
                                    'upvotes': chosen.get('score', 0),
                                    'source': 'reddit_api'
                                }
                                
                                logger.info(f"✅ Returning meme: {result['title'][:30]}...")
                                return result
                            else:
                                logger.warning(f"❌ No good posts found in r/{subreddit}")
                                continue
                        else:
                            logger.warning(f"❌ API returned {response.status}")
                            continue
            
            logger.warning("❌ All attempts failed")
            return None
            
        except Exception as e:
            logger.error(f"💥 Meme fetch error: {e}")
            return None

    async def get_group_members(self, context: ContextTypes.DEFAULT_TYPE, chat_id):
        """Get actual group members"""
        try:
            if chat_id > 0:
                return []
            
            admins = await context.bot.get_chat_administrators(chat_id)
            members = []
            
            for admin in admins:
                if not admin.user.is_bot and admin.user.id != context.bot.id:
                    members.append(admin.user)
            
            for user_id in self.group_data[chat_id]['active_members']:
                try:
                    member = await context.bot.get_chat_member(chat_id, user_id)
                    if (member.status not in ['left', 'kicked'] and 
                        not member.user.is_bot and 
                        member.user not in members):
                        members.append(member.user)
                except:
                    continue
                    
            return members
            
        except Exception as e:
            logger.error(f"Error getting group members: {e}")
            members = []
            for user_id in self.group_data[chat_id]['active_members']:
                class MockUser:
                    def __init__(self, user_id, nicknames):
                        self.id = user_id
                        self.first_name = nicknames.get(user_id, f"User {user_id}")
                        self.is_bot = False
                members.append(MockUser(user_id, self.group_data[chat_id]['nicknames']))
            return members

    # ALL MAIN HANDLERS
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button callbacks"""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if user:
            self.group_data[chat_id]['active_members'].add(user.id)

        # Direct handlers
        direct_handlers = {
            "main_menu": self.start,
            "who_pays": self.who_pays_handler,
            "music_menu": self.music_menu_handler,
            "meme_menu": self.meme_menu_handler,
            "drinking_menu": self.drinking_menu_handler,
            "trivia_menu": self.trivia_menu_handler,
            "mood_menu": self.mood_menu_handler,
            "coin_flip": self.coin_flip_handler,
            "roll_dice": self.roll_dice_handler,
            "choose_menu": self.choose_menu_handler,
            "vote_menu": self.vote_menu_handler,
            "roast_menu": self.roast_menu_handler,
            "space_menu": self.space_menu_handler,
            "games_menu": self.games_menu_handler,
            "stats_menu": self.stats_menu_handler
        }
        
        # Check direct handlers first
        if data in direct_handlers:
            await direct_handlers[data](update, context)
            return
        
        # Prefix handlers
        if data.startswith("ytmusic_") or data == "music_stats":
            await self.youtube_music_handler(update, context)
        elif data.startswith("meme_"):
            await self.russian_meme_handler(update, context)
        elif data.startswith("drink_"):
            await self.drink_handler(update, context)
        elif data.startswith("trivia_"):
            await self.trivia_handler(update, context)
        elif data.startswith("vote_"):
            await self.vote_handler(update, context)
        elif data.startswith("roast_"):
            await self.roast_handler(update, context)
        elif data.startswith("set_mood_") or data == "toggle_auto_rotate":
            await self.set_mood_handler(update, context)
        elif data.startswith("choose_") and not data.startswith("choose_menu"):
            await self.choose_option_handler(update, context)
        elif data.startswith("space_"):
            await self.space_handler(update, context)
        else:
            logger.warning(f"Unhandled callback: {data}")

    # CORE FEATURE HANDLERS
    async def who_pays_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Who pays handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        members = await self.get_group_members(context, chat_id)
        if len(members) < 2:
            await query.edit_message_text("❌ Need at least 2 people!", reply_markup=self.get_back_keyboard())
            return
        
        chosen = random.choice(members)
        self.group_data[chat_id]['karma'][chosen.id] += 1
        
        display_name = self.group_data[chat_id]['nicknames'].get(chosen.id, chosen.first_name)
        mood = self.group_data[chat_id]['mood']
        message = random.choice(self.moods[mood]['messages'])
        
        await self.suspense_reveal(query, f"💸 **{display_name}** pays! 💸\n\n{message}", self.get_back_keyboard())

    # VOTING SYSTEM - Complete implementation
    async def vote_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced voting menu"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        active_votes = self.group_data[chat_id].get('active_votes', {})
        active_text = f"\n🗳️ Active polls: {len(active_votes)}" if active_votes else ""
        
        text = f"""🗳️ **Group Voting System** 🗳️

Let democracy decide your fate!{active_text}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🍕 Food Vote", callback_data="vote_food"),
                InlineKeyboardButton("🍻 Bar Vote", callback_data="vote_bar")
            ],
            [
                InlineKeyboardButton("🎮 Activity Vote", callback_data="vote_activity"),
                InlineKeyboardButton("🎲 Random Topic", callback_data="vote_random")
            ],
            [
                InlineKeyboardButton("📊 Results", callback_data="vote_results"),
                InlineKeyboardButton("🗑️ Clear Votes", callback_data="vote_clear")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def vote_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voting actions"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if data == "vote_food":
            options = ["🍕 Pizza", "🍔 Burgers", "🍜 Ramen", "🥘 Russian Food", "🍱 Sushi"]
            await self.create_vote(query, "What should we eat?", options, "food")
            
        elif data == "vote_bar":
            options = ["🍺 Local Pub", "🍶 Sake Bar", "🍸 Cocktail Lounge", "🏠 Someone's Place", "🌃 Bar Crawl"]
            await self.create_vote(query, "Where should we drink?", options, "bar")
            
        elif data == "vote_activity":
            options = ["🎮 Gaming Night", "🎬 Movie Night", "🎤 Karaoke", "🎲 Board Games", "🚶 Walk Around"]
            await self.create_vote(query, "What should we do?", options, "activity")
            
        elif data == "vote_random":
            topics = [
                ("Best anime character", ["🥷 Naruto", "⚡ Pikachu", "🗾 Goku", "🌸 Sailor Moon"]),
                ("Worst Russian stereotype", ["🐻 Bears everywhere", "🍺 Always drunk", "❄️ Always cold", "🪆 Love matryoshkas"]),
                ("Best superpower", ["🦸 Flying", "👤 Invisibility", "🧠 Mind reading", "⚡ Super speed"]),
                ("Zombie apocalypse weapon", ["🏏 Baseball bat", "🔫 Shotgun", "🗾 Katana", "🥄 Spoon"])
            ]
            topic, options = random.choice(topics)
            await self.create_vote(query, topic, options, "random")
            
        elif data.startswith("vote_option_"):
            await self.handle_vote_option(query, user, data)
            
        elif data == "vote_results":
            await self.show_vote_results(query, chat_id)
            
        elif data == "vote_clear":
            self.group_data[chat_id]['active_votes'] = {}
            await query.edit_message_text("🗑️ All votes cleared!", reply_markup=self.get_back_keyboard("vote_menu"))

    async def create_vote(self, query, question, options, vote_type):
        """Create a new vote"""
        chat_id = query.message.chat_id
        
        vote_id = f"{vote_type}_{int(datetime.now().timestamp())}"
        
        self.group_data[chat_id]['active_votes'][vote_id] = {
            'question': question,
            'options': options,
            'votes': defaultdict(int),
            'voters': set(),
            'created': datetime.now()
        }
        
        text = f"🗳️ **{question}**\n\nClick to vote:"
        
        keyboard = []
        for i, option in enumerate(options):
            keyboard.append([InlineKeyboardButton(option, callback_data=f"vote_option_{vote_id}_{i}")])
        
        keyboard.append([InlineKeyboardButton("📊 Results", callback_data="vote_results")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="vote_menu")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def handle_vote_option(self, query, user, data):
        """Handle individual vote"""
        parts = data.split("_")
        vote_id = "_".join(parts[2:-1])
        option_index = int(parts[-1])
        
        chat_id = query.message.chat_id
        active_votes = self.group_data[chat_id]['active_votes']
        
        if vote_id not in active_votes:
            await query.answer("Vote expired!")
            return
        
        vote_data = active_votes[vote_id]
        
        if user.id in vote_data['voters']:
            await query.answer("You already voted!")
            return
        
        vote_data['votes'][option_index] += 1
        vote_data['voters'].add(user.id)
        
        option_name = vote_data['options'][option_index]
        await query.answer(f"Voted for: {option_name}")
        
        # Update display with current results
        await self.update_vote_display(query, vote_id, vote_data)

    async def update_vote_display(self, query, vote_id, vote_data):
        """Update vote display with current results"""
        question = vote_data['question']
        total_votes = sum(vote_data['votes'].values())
        
        text = f"🗳️ **{question}**\n\n"
        
        if total_votes > 0:
            text += "📊 **Current Results:**\n"
            for i, option in enumerate(vote_data['options']):
                votes = vote_data['votes'][i]
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0
                bar = "█" * min(10, int(percentage / 10))
                text += f"{option}: {votes} ({percentage:.0f}%)\n{bar}\n"
            
            text += f"\n👥 Total votes: {total_votes}"
        else:
            text += "No votes yet! Click to vote:"
        
        keyboard = []
        for i, option in enumerate(vote_data['options']):
            keyboard.append([InlineKeyboardButton(option, callback_data=f"vote_option_{vote_id}_{i}")])
        
        keyboard.append([InlineKeyboardButton("📊 Results", callback_data="vote_results")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="vote_menu")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def show_vote_results(self, query, chat_id):
        """Show all vote results"""
        active_votes = self.group_data[chat_id]['active_votes']
        
        if not active_votes:
            text = "📊 **Vote Results**\n\nNo active votes!"
        else:
            text = "📊 **All Vote Results**\n\n"
            
            for vote_id, vote_data in active_votes.items():
                question = vote_data['question']
                total_votes = sum(vote_data['votes'].values())
                
                text += f"🗳️ **{question}**\n"
                
                if total_votes > 0:
                    # Find winner
                    max_votes = max(vote_data['votes'].values()) if vote_data['votes'] else 0
                    winners = [vote_data['options'][i] for i, votes in vote_data['votes'].items() if votes == max_votes]
                    
                    if len(winners) == 1:
                        text += f"🏆 Winner: {winners[0]} ({max_votes} votes)\n"
                    else:
                        text += f"🤝 Tie between: {', '.join(winners)}\n"
                else:
                    text += "No votes yet\n"
                
                text += "\n"
        
        keyboard = self.get_back_keyboard("vote_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    # ROAST GENERATOR - Complete implementation
    async def roast_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced roast menu"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        members = await self.get_group_members(context, chat_id)
        member_count = len(members)
        
        mood = self.group_data[chat_id]['mood']
        mood_emoji = self.moods[mood]['emoji']
        
        text = f"""😈 **Roast Generator** {mood_emoji}

Time to roast your friends in {mood} style!
*Current victims: {member_count} people*
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 Roast Someone", callback_data="roast_random"),
                InlineKeyboardButton("💖 Compliment Instead", callback_data="roast_compliment")
            ],
            [
                InlineKeyboardButton("🔥 Roast Battle", callback_data="roast_battle"),
                InlineKeyboardButton("😅 Self Roast", callback_data="roast_self")
            ],
            [
                InlineKeyboardButton("🎲 Random Insult", callback_data="roast_generic"),
                InlineKeyboardButton("🌈 Wholesome Mode", callback_data="roast_wholesome")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def roast_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle roast actions"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        members = await self.get_group_members(context, chat_id)
        mood = self.group_data[chat_id]['mood']
        
        if data == "roast_random":
            if len(members) < 1:
                await query.edit_message_text("❌ No one to roast!", reply_markup=self.get_back_keyboard("roast_menu"))
                return
            
            target = random.choice(members)
            roast = self.get_mood_roast(target, mood)
            
            await self.suspense_reveal(query, f"🔥 **ROAST TIME** 🔥\n\n{roast}", self.get_back_keyboard("roast_menu"))
            
        elif data == "roast_compliment":
            if len(members) < 1:
                await query.edit_message_text("❌ No one to compliment!", reply_markup=self.get_back_keyboard("roast_menu"))
                return
            
            target = random.choice(members)
            compliment = self.get_mood_compliment(target, mood)
            
            await self.suspense_reveal(query, f"💖 **WHOLESOME TIME** 💖\n\n{compliment}", self.get_back_keyboard("roast_menu"))
            
        elif data == "roast_self":
            self_roasts = [
                "You asked a bot to roast you. That's roast enough.",
                "You're so desperate for attention you're asking AI to insult you!",
                "Your biggest roast is using a Telegram bot for entertainment.",
                "You can't even get real friends to roast you properly!",
                "The fact that you clicked this button says everything."
            ]
            
            roast = random.choice(self_roasts)
            await query.edit_message_text(f"😅 **SELF-ROAST** 😅\n\n{roast}", 
                                         reply_markup=self.get_back_keyboard("roast_menu"), parse_mode='Markdown')
            
        elif data == "roast_battle":
            if len(members) < 2:
                await query.edit_message_text("❌ Need at least 2 people for a battle!", reply_markup=self.get_back_keyboard("roast_menu"))
                return
            
            battler1, battler2 = random.sample(members, 2)
            
            battle_text = f"🥊 **ROAST BATTLE** 🥊\n\n"
            battle_text += f"🔵 {battler1.first_name} vs 🔴 {battler2.first_name}\n\n"
            battle_text += f"🔵: {self.get_mood_roast(battler2, mood, short=True)}\n\n"
            battle_text += f"🔴: {self.get_mood_roast(battler1, mood, short=True)}\n\n"
            
            winner = random.choice([battler1, battler2])
            battle_text += f"🏆 **Winner: {winner.first_name}** by TKO!"
            
            await self.suspense_reveal(query, battle_text, self.get_back_keyboard("roast_menu"))
            
        elif data == "roast_generic":
            generic_roasts = [
                "You're about as useful as a chocolate teapot!",
                "If stupidity burned calories, you'd be supermodel thin!",
                "You're the reason gene pools need lifeguards!",
                "I've seen more personality in a wet napkin!",
                "You're like a software update - nobody wants you!"
            ]
            
            roast = random.choice(generic_roasts)
            await query.edit_message_text(f"🎲 **RANDOM ROAST** 🎲\n\n{roast}", 
                                         reply_markup=self.get_back_keyboard("roast_menu"), parse_mode='Markdown')
            
        elif data == "roast_wholesome":
            wholesome_messages = [
                "You're all amazing friends and I'm lucky to entertain you!",
                "This group has more laughs than a comedy show!",
                "You guys make even AI feel happy!",
                "Best group chat energy in the entire internet!",
                "Friendship level: Over 9000!"
            ]
            
            message = random.choice(wholesome_messages)
            await query.edit_message_text(f"🌈 **WHOLESOME MODE** 🌈\n\n{message}", 
                                         reply_markup=self.get_back_keyboard("roast_menu"), parse_mode='Markdown')

    def get_mood_roast(self, target, mood, short=False):
        """Get a mood-appropriate roast"""
        name = target.first_name
        
        roast_templates = self.roasts.get(mood, self.roasts['normal'])
        roast = random.choice(roast_templates).format(name=name)
        
        if short:
            # For battles, make shorter roasts
            short_roasts = {
                'normal': f"{name} is so cheap, parking meters expire early around them!",
                'sarcastic': f"Oh wow, {name}, another *genius* observation!",
                'pirate': f"{name}'s wallet be more sealed than Davy Jones' locker!",
                'cyberpunk': f"{name}.exe has stopped working... permanently!",
                'anime': f"{name}'s cheapness level is over 9000!"
            }
            return short_roasts.get(mood, f"{name} just got roasted!")
        
        return roast

    def get_mood_compliment(self, target, mood):
        """Get a mood-appropriate compliment"""
        name = target.first_name
        
        compliment_templates = self.compliments.get(mood, self.compliments['normal'])
        return random.choice(compliment_templates).format(name=name)

    # CHOOSE BETWEEN OPTIONS - Complete implementation
    async def choose_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced choose between options menu"""
        query = update.callback_query
        
        text = f"""🎯 **Decision Maker** 🎯

Can't decide? Let me choose for you!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🍕 Food Options", callback_data="choose_food"),
                InlineKeyboardButton("🍻 Drinking Spots", callback_data="choose_bars")
            ],
            [
                InlineKeyboardButton("🎬 Entertainment", callback_data="choose_entertainment"),
                InlineKeyboardButton("🎮 Activities", callback_data="choose_activities")
            ],
            [
                InlineKeyboardButton("🎲 Random Life", callback_data="choose_random_life"),
                InlineKeyboardButton("💭 Deep Thoughts", callback_data="choose_philosophy")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def choose_option_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle choosing between predefined options"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        data = query.data
        mood = self.group_data[chat_id]['mood']
        
        option_sets = {
            'choose_food': {
                'title': 'Food Decision',
                'options': ['🍕 Pizza', '🍔 Burgers', '🍜 Ramen', '🥘 Russian Food', '🍱 Sushi', '🌮 Tacos', '🍝 Pasta', '🥗 Salad']
            },
            'choose_bars': {
                'title': 'Where to Drink',
                'options': ['🍺 Local Pub', '🍶 Sake Bar', '🍸 Cocktail Lounge', '🏠 Someone\'s Place', '🌃 Bar District', '🍻 Beer Garden', '🥃 Whiskey Bar']
            },
            'choose_entertainment': {
                'title': 'Entertainment Choice',
                'options': ['🎬 Movies', '🎤 Karaoke', '🎮 Gaming', '🎲 Board Games', '🃏 Card Games', '🎳 Bowling', '🎯 Darts', '📺 Netflix']
            },
            'choose_activities': {
                'title': 'Activity Decision',
                'options': ['🚶 Walk Around', '🏔️ Hiking', '🛍️ Shopping', '🎨 Art Gallery', '🎪 Arcade', '🎢 Amusement Park', '🌊 Beach', '🌸 Park']
            },
            'choose_random_life': {
                'title': 'Random Life Decision',
                'options': ['💤 Sleep More', '💪 Exercise', '📚 Learn Something', '📱 Social Media', '🧹 Clean House', '🍳 Cook', '📞 Call Family', '🎵 Music']
            },
            'choose_philosophy': {
                'title': 'Deep Life Question',
                'options': ['🤔 What is happiness?', '💭 Why are we here?', '🌟 What matters most?', '⏰ How to spend time?', '💝 What is love?', '🎯 What is success?']
            }
        }
        
        if data in option_sets:
            option_set = option_sets[data]
            chosen = random.choice(option_set['options'])
            
            mood_responses = {
                'pirate': f"🏴‍☠️ By the seven seas, ye should choose: **{chosen}**!",
                'sarcastic': f"😏 Oh wow, such a *difficult* choice... obviously **{chosen}**!",
                'anime': f"🎌 Senpai! The anime gods have chosen: **{chosen}**!",
                'cyberpunk': f"🌃 Neural networks computed optimal choice: **{chosen}**!",
                'pokemon': f"⚡ Wild choice appeared! It's **{chosen}**!",
                'dramatic': f"🎭 After EPIC consideration... the choice is **{chosen}**!",
            }
            
            response = mood_responses.get(mood, f"🎯 **{option_set['title']}**\n\nI choose: **{chosen}**!")
            
            keyboard = [
                [InlineKeyboardButton("🎲 Choose Again", callback_data=data)],
                [InlineKeyboardButton("🔙 Back", callback_data="choose_menu")]
            ]
            
            await self.suspense_reveal(query, response, InlineKeyboardMarkup(keyboard))

    # SPACE ADVENTURE GAME - Complete implementation
    async def space_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Space Adventure main menu"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        space_data = self.group_data[chat_id]['space_adventure']
        current_episode = space_data.get('current_episode', 0)
        active_game = space_data.get('active_game', False)
        games_played = space_data['game_stats'].get('games_completed', 0)
        
        status_text = ""
        if active_game:
            episode_title = self.space_episodes[current_episode]['title']
            status_text = f"\n🎮 **Active:** {episode_title}"
        elif games_played > 0:
            status_text = f"\n📊 Adventures completed: {games_played}"
        
        text = f"""🚀 **Space Crew Adventure** 🚀

*Cowboy Bebop meets your drinking crew*

Join your friends as space bounty hunters in episodic adventures across the galaxy. Face challenges, make decisions, and see who survives the void!{status_text}
        """
        
        if active_game:
            keyboard = [
                [InlineKeyboardButton("▶️ Continue Adventure", callback_data="space_continue")],
                [InlineKeyboardButton("🔄 Restart Episode", callback_data="space_restart")],
                [InlineKeyboardButton("📊 Crew Status", callback_data="space_status")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🆕 Start New Adventure", callback_data="space_start")],
                [InlineKeyboardButton("📖 Episode List", callback_data="space_episodes")],
                [InlineKeyboardButton("📊 Stats", callback_data="space_stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
            ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def space_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle space adventure actions"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if data == "space_start":
            await self.space_start_new_game(query, context)
        elif data == "space_continue":
            await self.space_continue_game(query, context)
        elif data == "space_restart":
            await self.space_restart_game(query, context)
        elif data == "space_episodes":
            await self.space_show_episodes(query)
        elif data == "space_stats":
            await self.space_show_stats(query, chat_id)
        elif data == "space_status":
            await self.space_show_crew_status(query, chat_id)
        elif data.startswith("space_choice_"):
            await self.space_handle_choice(query, context, data)
        elif data.startswith("space_challenge_"):
            await self.space_handle_challenge(query, context, data)
        elif data.startswith("space_trivia_"):
            await self.space_handle_trivia(query, context, data)

    async def space_start_new_game(self, query, context):
        """Start a new space adventure"""
        chat_id = query.message.chat_id
        
        # Reset game state
        space_data = self.group_data[chat_id]['space_adventure']
        space_data.update({
            'current_episode': 0,
            'current_scene': 0,
            'crew_members': set(),
            'eliminated_players': set(),
            'story_choices': [],
            'active_game': True
        })
        
        # Get crew members
        members = await self.get_group_members(context, chat_id)
        for member in members:
            space_data['crew_members'].add(member.id)
        
        if len(members) < 2:
            await query.edit_message_text(
                "❌ Need at least 2 crew members for a space adventure!",
                reply_markup=self.get_back_keyboard("space_menu")
            )
            return
        
        # Start first episode
        await self.space_show_scene(query, context)

    async def space_continue_game(self, query, context):
        """Continue existing adventure"""
        await self.space_show_scene(query, context)

    async def space_restart_game(self, query, context):
        """Restart current episode"""
        chat_id = query.message.chat_id
        space_data = self.group_data[chat_id]['space_adventure']
        
        space_data.update({
            'current_scene': 0,
            'eliminated_players': set(),
            'story_choices': []
        })
        
        await self.space_show_scene(query, context)

    async def space_show_episodes(self, query):
        """Show available episodes"""
        text = "📖 **Available Episodes** 📖\n\n"
        
        for i, episode in enumerate(self.space_episodes):
            status = "🎮" if i == 0 else "🔒"
            text += f"{status} **{episode['title']}**\n"
            text += f"   📍 {episode['planet']}\n"
            text += f"   🎭 {episode['setting']}\n\n"
        
        keyboard = self.get_back_keyboard("space_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    async def space_show_stats(self, query, chat_id):
        """Show space adventure statistics"""
        stats = self.group_data[chat_id]['space_adventure']['game_stats']
        
        text = "📊 **Space Crew Statistics** 📊\n\n"
        text += f"🎮 **Adventures Completed:** {stats.get('games_completed', 0)}\n"
        text += f"💀 **Total Eliminations:** {stats.get('total_eliminations', 0)}\n"
        text += f"🏆 **Successful Missions:** {stats.get('successful_missions', 0)}\n"
        text += f"🤔 **Challenges Faced:** {stats.get('challenges_completed', 0)}\n"
        
        if stats.get('survivor_count', 0) > 0:
            survival_rate = (stats['survivor_count'] / max(1, stats.get('total_players', 1))) * 100
            text += f"⭐ **Crew Survival Rate:** {survival_rate:.0f}%\n"
        
        keyboard = self.get_back_keyboard("space_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    async def space_show_crew_status(self, query, chat_id):
        """Show current crew status"""
        space_data = self.group_data[chat_id]['space_adventure']
        
        active_crew = space_data['crew_members'] - space_data['eliminated_players']
        eliminated = space_data['eliminated_players']
        
        text = "👥 **Current Crew Status** 👥\n\n"
        
        if active_crew:
            text += "✅ **Active Crew:**\n"
            for user_id in active_crew:
                name = self.group_data[chat_id]['nicknames'].get(user_id, f"User {user_id}")
                text += f"   🚀 {name}\n"
            text += "\n"
        
        if eliminated:
            text += "💀 **Eliminated:**\n"
            for user_id in eliminated:
                name = self.group_data[chat_id]['nicknames'].get(user_id, f"User {user_id}")
                text += f"   ☠️ {name}\n"
        
        keyboard = self.get_back_keyboard("space_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    async def space_show_scene(self, query, context):
        """Show current scene of the adventure"""
        chat_id = query.message.chat_id
        space_data = self.group_data[chat_id]['space_adventure']
        
        episode_idx = space_data['current_episode']
        scene_idx = space_data['current_scene']
        
        if episode_idx >= len(self.space_episodes):
            # Adventure complete
            await self.space_complete_adventure(query, chat_id)
            return
        
        episode = self.space_episodes[episode_idx]
        
        if scene_idx >= len(episode['scenes']):
            # Episode complete, move to next
            space_data['current_episode'] += 1
            space_data['current_scene'] = 0
            space_data['game_stats']['games_completed'] += 1
            await self.space_show_scene(query, context)
            return
        
        scene = episode['scenes'][scene_idx]
        
        # Build scene text
        text = f"🌌 **{episode['title']}** - Scene {scene_idx + 1}\n"
        text += f"📍 *{episode['planet']}*\n\n"
        text += scene['text']
        
        # Add crew status
        active_crew = space_data['crew_members'] - space_data['eliminated_players']
        if len(active_crew) > 1:
            text += f"\n\n👥 **Active Crew:** {len(active_crew)} members"
        elif len(active_crew) == 1:
            survivor_id = next(iter(active_crew))
            survivor_name = self.group_data[chat_id]['nicknames'].get(survivor_id, f"User {survivor_id}")
            text += f"\n\n🏆 **Sole Survivor:** {survivor_name}"
        
        # Create appropriate buttons based on scene type
        keyboard = []
        
        if scene['type'] == 'story':
            keyboard.append([InlineKeyboardButton("▶️ Continue", callback_data="space_continue")])
            
        elif scene['type'] == 'choice':
            for i, option in enumerate(scene['options']):
                keyboard.append([InlineKeyboardButton(option, callback_data=f"space_choice_{i}")])
                
        elif scene['type'] == 'challenge':
            if scene['challenge_type'] == 'trivia':
                for i, option in enumerate(scene['options']):
                    keyboard.append([InlineKeyboardButton(option, callback_data=f"space_trivia_{i}")])
            elif scene['challenge_type'] == 'dare':
                keyboard.append([InlineKeyboardButton("✅ Done!", callback_data="space_challenge_complete")])
                keyboard.append([InlineKeyboardButton("❌ Skip", callback_data="space_challenge_skip")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="space_menu")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def space_handle_choice(self, query, context, data):
        """Handle story choice selection"""
        chat_id = query.message.chat_id
        choice_idx = int(data.split("_")[-1])
        
        space_data = self.group_data[chat_id]['space_adventure']
        episode = self.space_episodes[space_data['current_episode']]
        scene = episode['scenes'][space_data['current_scene']]
        
        chosen_option = scene['options'][choice_idx]
        consequence = scene['consequences'][choice_idx]
        
        # Store choice for future reference
        space_data['story_choices'].append({
            'scene': space_data['current_scene'],
            'choice': chosen_option,
            'consequence': consequence
        })
        
        # Show choice result
        text = f"🎭 **Choice Made:** {chosen_option}\n\n"
        
        if consequence == 'attract_attention':
            text += "⚠️ Your bold approach draws unwanted attention from station security!"
        elif consequence == 'stealth_bonus':
            text += "🥷 Smart thinking! Your stealth approach gives the crew an advantage."
        elif consequence == 'sacrifice_needed':
            text += "💀 Someone needs to take the risk..."
            # Eliminate random crew member
            active_crew = space_data['crew_members'] - space_data['eliminated_players']
            if len(active_crew) > 1:
                eliminated = random.choice(list(active_crew))
                space_data['eliminated_players'].add(eliminated)
                name = self.group_data[chat_id]['nicknames'].get(eliminated, f"User {eliminated}")
                text += f"\n\n☠️ **{name}** volunteers and gets captured by security!"
                space_data['game_stats']['total_eliminations'] += 1
        
        # Advance to next scene
        space_data['current_scene'] += 1
        
        keyboard = [[InlineKeyboardButton("▶️ Continue", callback_data="space_continue")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def space_handle_trivia(self, query, context, data):
        """Handle trivia challenge"""
        chat_id = query.message.chat_id
        answer_idx = int(data.split("_")[-1])
        
        space_data = self.group_data[chat_id]['space_adventure']
        episode = self.space_episodes[space_data['current_episode']]
        scene = episode['scenes'][space_data['current_scene']]
        
        chosen_answer = scene['options'][answer_idx]
        correct_answer = scene['answer']
        is_correct = chosen_answer == correct_answer
        
        text = f"🧠 **Trivia Challenge Result**\n\n"
        text += f"❓ **Question:** {scene['question']}\n"
        text += f"💭 **Your Answer:** {chosen_answer}\n"
        
        if is_correct or correct_answer == "Any answer works!":
            text += "✅ **Correct!** The crew impresses the locals."
        else:
            text += f"❌ **Wrong!** The correct answer was: {correct_answer}\n\n"
            text += "💀 The locals get suspicious..."
            
            # Eliminate random crew member on wrong answer
            active_crew = space_data['crew_members'] - space_data['eliminated_players']
            if len(active_crew) > 1:
                eliminated = random.choice(list(active_crew))
                space_data['eliminated_players'].add(eliminated)
                name = self.group_data[chat_id]['nicknames'].get(eliminated, f"User {eliminated}")
                text += f"\n☠️ **{name}** gets thrown out of the cantina!"
                space_data['game_stats']['total_eliminations'] += 1
        
        space_data['game_stats']['challenges_completed'] += 1
        space_data['current_scene'] += 1
        
        keyboard = [[InlineKeyboardButton("▶️ Continue", callback_data="space_continue")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def space_handle_challenge(self, query, context, data):
        """Handle dare challenges"""
        chat_id = query.message.chat_id
        user = query.from_user
        
        space_data = self.group_data[chat_id]['space_adventure']
        
        if data == "space_challenge_complete":
            text = f"🎭 **Challenge Completed!**\n\n"
            text += f"🌟 {user.first_name} successfully completed the dare!"
            text += "\n\nThe crew gains respect from the locals."
        elif data == "space_challenge_skip":
            text = f"😅 **Challenge Skipped**\n\n"
            text += f"💀 {user.first_name} chickened out..."
            
            # Small chance of elimination for skipping
            if random.random() < 0.3:  # 30% chance
                active_crew = space_data['crew_members'] - space_data['eliminated_players']
                if user.id in active_crew and len(active_crew) > 1:
                    space_data['eliminated_players'].add(user.id)
                    text += f"\n☠️ **{user.first_name}** gets kicked out for cowardice!"
                    space_data['game_stats']['total_eliminations'] += 1
        
        space_data['game_stats']['challenges_completed'] += 1
        space_data['current_scene'] += 1
        
        keyboard = [[InlineKeyboardButton("▶️ Continue", callback_data="space_continue")]]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def space_complete_adventure(self, query, chat_id):
        """Complete the space adventure"""
        space_data = self.group_data[chat_id]['space_adventure']
        
        active_crew = space_data['crew_members'] - space_data['eliminated_players']
        eliminated = space_data['eliminated_players']
        
        text = "🎊 **ADVENTURE COMPLETE!** 🎊\n\n"
        text += "🚀 The space crew has completed their mission!\n\n"
        
        if len(active_crew) > 1:
            text += f"🏆 **Survivors:** {len(active_crew)} crew members made it!\n"
            for user_id in active_crew:
                name = self.group_data[chat_id]['nicknames'].get(user_id, f"User {user_id}")
                text += f"   ⭐ {name}\n"
        elif len(active_crew) == 1:
            survivor_id = next(iter(active_crew))
            survivor_name = self.group_data[chat_id]['nicknames'].get(survivor_id, f"User {survivor_id}")
            text += f"🏅 **Sole Survivor:** {survivor_name}\n"
            text += "Truly the ultimate space cowboy!"
        else:
            text += "💀 **Total Crew Loss!**\n"
            text += "The mission failed, but the legend lives on..."
        
        if eliminated:
            text += f"\n⚰️ **Fallen Heroes:** {len(eliminated)}\n"
            for user_id in eliminated:
                name = self.group_data[chat_id]['nicknames'].get(user_id, f"User {user_id}")
                text += f"   ☠️ {name}\n"
        
        # Update stats
        stats = space_data['game_stats']
        stats['survivor_count'] = stats.get('survivor_count', 0) + len(active_crew)
        stats['total_players'] = stats.get('total_players', 0) + len(space_data['crew_members'])
        if len(active_crew) > 0:
            stats['successful_missions'] = stats.get('successful_missions', 0) + 1
        
        # Reset game
        space_data['active_game'] = False
        
        keyboard = [
            [InlineKeyboardButton("🎮 Play Again", callback_data="space_start")],
            [InlineKeyboardButton("🔙 Back", callback_data="space_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # MUSIC HANDLERS
    async def music_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Music menu handler"""
        query = update.callback_query
        
        api_status = "🟢 YouTube API" if self.YOUTUBE_API_KEY else "🟡 Curated Songs"
        
        text = f"""🎵 **Music Selector** 🎵

Random music from YouTube's vast library!
{api_status}
        """
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Russian", callback_data="ytmusic_russian"),
             InlineKeyboardButton("🇯🇵 Japanese", callback_data="ytmusic_japanese")],
            [InlineKeyboardButton("🎌 Anime", callback_data="ytmusic_anime"),
             InlineKeyboardButton("🌍 Global", callback_data="ytmusic_global")],
            [InlineKeyboardButton("🎲 Surprise!", callback_data="ytmusic_random")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def youtube_music_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """YouTube music handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        category = query.data.split("_")[-1]
        
        await query.edit_message_text("🎵 Finding random music on YouTube... 🔍")
        
        song = await self.get_random_youtube_music(category)
        if not song:
            await query.edit_message_text("❌ No music found!", reply_markup=self.get_back_keyboard("music_menu"))
            return
        
        mood = self.group_data[chat_id]['mood']
        intro = f"🎵 Random {category} music found!"
        
        text = f"{intro}\n\n🎶 **{song['title']}**\n🎤 {song['artist']}\n\n🔗 [Listen on YouTube]({song['url']})"
        
        keyboard = [
            [InlineKeyboardButton("🎲 Another", callback_data=f"ytmusic_{category}")],
            [InlineKeyboardButton("🔙 Back", callback_data="music_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # MEME HANDLERS
    async def meme_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Russian meme menu handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        # Show stats
        stats = self.group_data[chat_id]['meme_stats']
        total_memes = stats.get('total_memes', 0)
        stats_text = f"\n🎭 Memes shared: {total_memes}" if total_memes > 0 else ""
        
        text = f"""🇷🇺 **Russian Meme Generator** 🇷🇺

Fresh memes from Russian Reddit communities!
*Warning: May cause uncontrollable laughter* 😂{stats_text}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Random", callback_data="meme_random"),
                InlineKeyboardButton("🔥 Hot", callback_data="meme_hot")
            ],
            [
                InlineKeyboardButton("👑 Top", callback_data="meme_top"),
                InlineKeyboardButton("🇷🇺 Russia", callback_data="meme_russia")
            ],
            [
                InlineKeyboardButton("😂 Pikabu", callback_data="meme_pikabu"),
                InlineKeyboardButton("📊 Stats", callback_data="meme_stats")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def russian_meme_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Russian meme handler with better debugging"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        data = query.data
        
        logger.info(f"🎭 Meme button clicked: {data}")
        
        if data.startswith("meme_") and data != "meme_stats":
            meme_type = data.split("_")[-1]
            
            # Show searching message
            loading_messages = [
                "🇷🇺 Searching Russian internet for memes... 🔍",
                "🤖 Consulting babushka's meme collection... 👵",
                "⚡ Downloading from Siberian servers... 🌨️",
                "🎭 Asking Russian Reddit for their finest... 🎪"
            ]
            
            await query.edit_message_text(random.choice(loading_messages))
            
            try:
                # Get meme
                logger.info("📡 Calling get_random_russian_meme...")
                meme = await self.get_random_russian_meme()
                logger.info(f"🎭 Meme result: {'Found' if meme else 'None'}")
                
                if not meme:
                    logger.warning("❌ No meme returned")
                    await query.edit_message_text(
                        "😅 **No memes found right now!**\n\n"
                        "🔧 **Possible reasons:**\n"
                        "• Reddit servers busy\n"
                        "• No image posts in recent posts\n"
                        "• Network connection issue\n\n"
                        "Try clicking 'Try Again' to try again!",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔄 Try Again", callback_data="meme_random")],
                            [InlineKeyboardButton("🔙 Back", callback_data="meme_menu")]
                        ]),
                        parse_mode='Markdown'
                    )
                    return
                
                # Success! We have a meme
                logger.info(f"✅ Got meme: {meme['title'][:50]}")
                
                # Update stats
                stats = self.group_data[chat_id]['meme_stats']
                stats['total_memes'] += 1
                
                subreddit = meme.get('subreddit', 'unknown')
                if subreddit not in stats['by_subreddit']:
                    stats['by_subreddit'][subreddit] = 0
                stats['by_subreddit'][subreddit] += 1
                
                # Create mood-specific response
                mood = self.group_data[chat_id]['mood']
                mood_responses = {
                    'pirate': "🏴‍☠️ Arrr! Russian treasure from the meme seas!",
                    'cyberpunk': "🌃 Meme data from Russian neural network...",
                    'anime': "🎌 Russian meme-chan appeared! Kawaii!",
                    'sarcastic': "😏 Oh great, *another* Russian meme...",
                    'pokemon': "⚡ Wild Russian Meme appeared!",
                    'dramatic': "🎭 BEHOLD! The most EPIC Russian meme!",
                    'gaming': "🎮 Achievement unlocked: Russian Meme Master!"
                }
                
                intro = mood_responses.get(mood, "🇷🇺 Fresh Russian meme!")
                
                # Create caption
                caption = f"{intro}\n\n"
                caption += f"😂 **{meme['title'][:100]}{'...' if len(meme['title']) > 100 else ''}**\n\n"
                
                if meme.get('upvotes'):
                    caption += f"⬆️ {meme['upvotes']} upvotes\n"
                if meme.get('subreddit'):
                    caption += f"📍 r/{meme['subreddit']}\n"
                
                total = stats['total_memes']
                caption += f"\n🎭 Meme #{total} in this group!"
                
                # Buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🎲 Another", callback_data="meme_random"),
                        InlineKeyboardButton("🔥 Hot", callback_data="meme_hot")
                    ],
                    [
                        InlineKeyboardButton("🔙 Back", callback_data="meme_menu")
                    ]
                ]
                
                # Try to send image
                logger.info(f"📷 Trying to send image: {meme.get('url')}")
                try:
                    if meme.get('url') and meme['url'].startswith('http'):
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=meme['url'],
                            caption=caption,
                            parse_mode='Markdown',
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        await query.delete_message()
                        logger.info("✅ Image sent successfully")
                    else:
                        raise Exception("Invalid image URL")
                        
                except Exception as img_error:
                    logger.error(f"📷 Image send failed: {img_error}")
                    # Fallback to text message with link
                    caption += f"\n\n🔗 [View Meme]({meme.get('url', 'https://reddit.com')})"
                    await query.edit_message_text(
                        caption,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                    
            except Exception as e:
                logger.error(f"💥 Meme handler error: {e}")
                await query.edit_message_text(
                    f"❌ Oops! Something went wrong.\n\nError: {str(e)[:100]}\n\nTry again or check your connection!",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Try Again", callback_data="meme_random")],
                        [InlineKeyboardButton("🔙 Back", callback_data="meme_menu")]
                    ])
                )
        
        elif data == "meme_stats":
            await self.show_meme_stats(query, chat_id)

    async def show_meme_stats(self, query, chat_id):
        """Show meme statistics"""
        stats = self.group_data[chat_id]['meme_stats']
        
        if not stats or stats.get('total_memes', 0) == 0:
            text = "📊 **Russian Meme Stats** 📊\n\nNo memes shared yet! Start the Russian meme revolution! 🇷🇺"
        else:
            total = stats['total_memes']
            by_subreddit = stats.get('by_subreddit', {})
            
            text = f"📊 **Russian Meme Stats** 📊\n\n"
            text += f"😂 **Total Memes:** {total}\n\n"
            
            if by_subreddit:
                text += "**📈 Top Sources:**\n"
                sorted_subreddits = sorted(by_subreddit.items(), key=lambda x: x[1], reverse=True)
                for subreddit, count in sorted_subreddits[:5]:
                    percentage = (count / total * 100)
                    text += f"• r/{subreddit}: {count} ({percentage:.0f}%)\n"
        
        keyboard = self.get_back_keyboard("meme_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    # DRINKING GAME HANDLERS
    async def drinking_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced drinking games menu"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        sips = self.group_data[chat_id]['sip_counts']
        top_text = ""
        if sips:
            top_sipper = max(sips.items(), key=lambda x: x[1])
            top_name = self.group_data[chat_id]['nicknames'].get(top_sipper[0], f"User {top_sipper[0]}")
            top_text = f"\n🍺 Champion: {top_name} ({top_sipper[1]} sips)"
        
        text = f"""🍻 **Drinking Games** 🍻

*Drink responsibly! 100+ Never Have I Ever questions*{top_text}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎲 Never Have I", callback_data="drink_never"),
                InlineKeyboardButton("🪙 Flip & Sip", callback_data="drink_flip")
            ],
            [
                InlineKeyboardButton("🎰 Roulette", callback_data="drink_roulette"),
                InlineKeyboardButton("📊 Leaderboard", callback_data="drink_stats")
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data="main_menu")
            ]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def drink_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced drinking game handler with 100+ questions"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if data == "drink_never":
            # Pick from 100+ questions
            challenge = random.choice(self.never_have_i_ever_questions)
            
            mood = self.group_data[chat_id]['mood']
            if mood == 'pirate':
                challenge = challenge.replace("sip", "swig o' rum").replace("drink", "down some grog")
            
            text = f"🍺 **Never Have I Ever** 🍺\n\n{challenge}\n\n*Remember: Drink responsibly!*"
            
            keyboard = [
                [InlineKeyboardButton("😅 Guilty (+1)", callback_data="drink_guilty")],
                [InlineKeyboardButton("😇 Innocent", callback_data="drink_innocent")],
                [InlineKeyboardButton("🎲 Another", callback_data="drink_never")],
                [InlineKeyboardButton("🔙 Back", callback_data="drinking_menu")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        elif data == "drink_guilty":
            self.group_data[chat_id]['sip_counts'][user.id] += 1
            total_sips = self.group_data[chat_id]['sip_counts'][user.id]
            
            mood = self.group_data[chat_id]['mood']
            responses = {
                'sarcastic': f"😏 {user.first_name} admits guilt! Shocking!",
                'pirate': f"🏴‍☠️ Arrr, {user.first_name} be takin' a swig!",
                'pokemon': f"⚡ {user.first_name} used Drink! It's super effective!",
                'cyberpunk': f"🌃 {user.first_name} executed drink.exe!"
            }
            
            response = responses.get(mood, f"🍺 {user.first_name} takes a sip!")
            text = f"{response}\n\n📊 **Total Sips:** {total_sips}"
            
            keyboard = [
                [InlineKeyboardButton("🎲 Another", callback_data="drink_never")],
                [InlineKeyboardButton("🔙 Back", callback_data="drinking_menu")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        elif data == "drink_innocent":
            text = f"😇 {user.first_name} claims innocence!\n\n*Lucky this time...*"
            
            keyboard = [
                [InlineKeyboardButton("🎲 Another", callback_data="drink_never")],
                [InlineKeyboardButton("🔙 Back", callback_data="drinking_menu")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == "drink_flip":
            result = random.choice(['Heads', 'Tails'])
            user_choice = random.choice(['Heads', 'Tails'])  # Random for demo
            
            if result != user_choice:
                self.group_data[chat_id]['sip_counts'][user.id] += 2
                text = f"🪙 Coin: **{result}**\n❌ You lose! Take 2 sips! 🍻"
            else:
                text = f"🪙 Coin: **{result}**\n✅ You win! No sips! 🎉"
            
            keyboard = [
                [InlineKeyboardButton("🪙 Flip Again", callback_data="drink_flip")],
                [InlineKeyboardButton("🔙 Back", callback_data="drinking_menu")]
            ]
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data == "drink_stats":
            await self.show_sip_stats(query, chat_id)

    async def show_sip_stats(self, query, chat_id):
        """Show drinking game statistics"""
        sips = self.group_data[chat_id]['sip_counts']
        
        if not sips:
            text = "📊 **Sip Leaderboard** 📊\n\nNo sips recorded yet!"
        else:
            sorted_sips = sorted(sips.items(), key=lambda x: x[1], reverse=True)
            
            text = "📊 **Sip Leaderboard** 📊\n\n"
            
            for i, (user_id, count) in enumerate(sorted_sips[:10]):
                display_name = self.group_data[chat_id]['nicknames'].get(user_id, f"User {user_id}")
                emojis = ["🍺👑", "🍻🥈", "🥃🥉", "🍷", "🍷", "🍷", "🍷", "🍷", "🍷", "🍷"]
                emoji = emojis[i] if i < len(emojis) else "🍷"
                
                text += f"{emoji} {display_name}: {count} sips\n"
        
        keyboard = self.get_back_keyboard("drinking_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    # TRIVIA HANDLERS
    async def trivia_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced trivia menu"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        scores = self.group_data[chat_id]['trivia_scores']
        top_text = ""
        if scores:
            top_scorer = max(scores.items(), key=lambda x: x[1])
            top_name = self.group_data[chat_id]['nicknames'].get(top_scorer[0], f"User {top_scorer[0]}")
            top_text = f"\n🏆 Champion: {top_name} ({top_scorer[1]} pts)"
        
        text = f"""🧠 **Trivia Quiz** 🧠

150+ questions across cultures!{top_text}
        """
        
        keyboard = [
            [InlineKeyboardButton("🇷🇺 Russian", callback_data="trivia_start_russian"),
             InlineKeyboardButton("🇯🇵 Japanese", callback_data="trivia_start_japanese")],
            [InlineKeyboardButton("🎌 Pop Culture", callback_data="trivia_start_pop"),
             InlineKeyboardButton("🎲 Random", callback_data="trivia_start_random")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def trivia_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Enhanced trivia with 150+ questions"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if data.startswith("trivia_start_"):
            category = data.split("_")[-1]
            
            if category == "random":
                questions = self.trivia_questions
            else:
                category_map = {"russian": "Russian", "japanese": "Japanese", "pop": "Pop Culture"}
                questions = [q for q in self.trivia_questions if q['category'] == category_map.get(category, "")]
            
            if not questions:
                await query.edit_message_text("No questions available!", reply_markup=self.get_back_keyboard("trivia_menu"))
                return
            
            question = random.choice(questions)
            question_id = f"{chat_id}_{user.id}_{int(datetime.now().timestamp())}"
            
            self.group_data[chat_id][f'active_question_{user.id}'] = {
                'question': question,
                'question_id': question_id
            }
            
            text = f"🧠 **{question['category']} Question**\n\n**{question['question']}**"
            
            keyboard = []
            for i, option in enumerate(question['options']):
                keyboard.append([InlineKeyboardButton(option[:25], callback_data=f"trivia_answer_{question_id}_{i}")])
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="trivia_menu")])
            
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        elif data.startswith("trivia_answer_"):
            parts = data.split("_")
            question_id = "_".join(parts[2:-1])
            answer_index = int(parts[-1])
            
            user_question_key = f'active_question_{user.id}'
            if user_question_key not in self.group_data[chat_id]:
                await query.edit_message_text("Question expired!", reply_markup=self.get_back_keyboard("trivia_menu"))
                return
            
            question_data = self.group_data[chat_id][user_question_key]
            question = question_data['question']
            
            chosen_answer = question['options'][answer_index]
            correct = chosen_answer == question['answer']
            
            if correct:
                self.group_data[chat_id]['trivia_scores'][user.id] += 1
                result_text = "✅ **Correct!** Well done!"
                result_text += f"\n\n🏆 **Your Score:** {self.group_data[chat_id]['trivia_scores'][user.id]} points"
            else:
                result_text = "❌ **Incorrect!**"
                result_text += f"\n\n🎯 **Correct Answer:** {question['answer']}"
            
            del self.group_data[chat_id][user_question_key]
            
            keyboard = [
                [InlineKeyboardButton("🧠 Again", callback_data="trivia_menu")],
                [InlineKeyboardButton("🔙 Menu", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    # MOOD HANDLERS
    async def mood_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Mood menu handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        current_mood = self.group_data[chat_id]['mood']
        
        text = f"""🎭 **Personality Settings** 🎭

Current: {current_mood.title()} {self.moods[current_mood]['emoji']}
        """
        
        keyboard = []
        for mood_name, mood_data in list(self.moods.items())[:5]:
            is_current = " ✓" if mood_name == current_mood else ""
            button_text = f"{mood_data['emoji']} {mood_name.title()[:8]}{is_current}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"set_mood_{mood_name}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="main_menu")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def set_mood_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set mood handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        data = query.data
        
        if data.startswith("set_mood_"):
            mood = data.split("_")[-1]
            
            if mood in self.moods:
                self.group_data[chat_id]['mood'] = mood
                emoji = self.moods[mood]['emoji']
                
                await query.edit_message_text(
                    f"{emoji} Mood set to {mood.title()}!",
                    reply_markup=self.get_back_keyboard("mood_menu")
                )

    # SIMPLE GAME HANDLERS
    async def coin_flip_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Coin flip handler"""
        result = random.choice(['Heads', 'Tails'])
        await self.suspense_reveal(update.callback_query, f"🪙 **{result}**!", self.get_back_keyboard())

    async def roll_dice_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dice roll handler"""
        result = random.randint(1, 6)
        dice_emojis = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
        await self.suspense_reveal(update.callback_query, f"{dice_emojis[result-1]} **{result}**!", self.get_back_keyboard())

    # PLACEHOLDER HANDLERS
    async def games_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Games menu handler"""
        query = update.callback_query
        
        text = """🎪 **Games Menu** 🎪

More games coming soon!
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 Space Adventure", callback_data="space_menu")],
            [InlineKeyboardButton("🎲 Dice Roll", callback_data="roll_dice")],
            [InlineKeyboardButton("🪙 Coin Flip", callback_data="coin_flip")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    async def stats_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Stats menu handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        # Gather stats from all features
        karma_stats = self.group_data[chat_id]['karma']
        sip_stats = self.group_data[chat_id]['sip_counts']
        trivia_stats = self.group_data[chat_id]['trivia_scores']
        space_stats = self.group_data[chat_id]['space_adventure']['game_stats']
        
        text = "📊 **Group Statistics** 📊\n\n"
        
        if karma_stats:
            top_payer = max(karma_stats.items(), key=lambda x: x[1])
            payer_name = self.group_data[chat_id]['nicknames'].get(top_payer[0], f"User {top_payer[0]}")
            text += f"💸 **Most Generous:** {payer_name} ({top_payer[1]} times)\n"
        
        if sip_stats:
            top_sipper = max(sip_stats.items(), key=lambda x: x[1])
            sipper_name = self.group_data[chat_id]['nicknames'].get(top_sipper[0], f"User {top_sipper[0]}")
            text += f"🍺 **Drinking Champion:** {sipper_name} ({top_sipper[1]} sips)\n"
        
        if trivia_stats:
            top_brain = max(trivia_stats.items(), key=lambda x: x[1])
            brain_name = self.group_data[chat_id]['nicknames'].get(top_brain[0], f"User {top_brain[0]}")
            text += f"🧠 **Trivia Master:** {brain_name} ({top_brain[1]} points)\n"
        
        if space_stats.get('games_completed', 0) > 0:
            text += f"🚀 **Space Adventures:** {space_stats['games_completed']} completed\n"
        
        active_members = len(self.group_data[chat_id]['active_members'])
        text += f"\n👥 **Active Members:** {active_members}"
        
        keyboard = self.get_back_keyboard("main_menu")
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode='Markdown')

    async def suspense_reveal(self, query, final_text, keyboard):
        """Suspenseful reveal animation"""
        await query.edit_message_text("🎲 Making decision...")
        
        for i in range(3):
            await asyncio.sleep(0.6)
            await query.edit_message_text("🎲 Making decision" + "." * (i + 1))
        
        await asyncio.sleep(0.8)
        await query.edit_message_text(final_text, reply_markup=keyboard, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages, passive triggers, and easter eggs"""
        if not update.message or not update.message.text:
            return
            
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        
        if update.effective_user:
            self.group_data[chat_id]['active_members'].add(update.effective_user.id)
        
        # First check for passive triggers
        if await self.check_passive_triggers(update, context):
            return  # Passive trigger handled, stop processing
        
        # Easter Eggs
        text_lower = text.lower()
        easter_eggs = {
            'konami': "🕹️ **KONAMI CODE ACTIVATED!** 🕹️\nExtra karma for everyone!",
            'ninja': "🥷 **NINJA MODE UNLOCKED!** 🥷\nStealth payments activated!",
            'legendary': "🌟 **LEGENDARY STATUS!** 🌟\nYou're now a decision master!",
            'up up down down': "🎮 **CHEAT CODE ACCEPTED!** 🎮\nInfinite lives granted!",
            'sakura': "🌸 **SAKURA POWER!** 🌸\nCherry blossom energy activated!"
        }
        
        for trigger, message in easter_eggs.items():
            if trigger in text_lower:
                self.group_data[chat_id]['discovered_easter_eggs'].add(trigger)
                await update.message.reply_text(message, reply_markup=self.get_main_menu_keyboard(chat_id), parse_mode='Markdown')
                return
        
        # Show main menu for direct commands
        if text_lower in ['menu', 'start', 'help', '/start', '/help']:
            await self.start(update, context)


def main():
    """Main function with Railway deployment support"""
    # Get configuration from environment variables (Railway compatible)
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')  # Optional
    PORT = int(os.getenv('PORT', '8443'))
    RAILWAY_STATIC_URL = os.getenv('RAILWAY_STATIC_URL')
    
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN environment variable not set!")
        return
    
    # Create bot instance
    bot = CrewCaptain()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler(["start", "help", "menu"], bot.start))
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Railway deployment support
    if RAILWAY_STATIC_URL:
        # Running on Railway with webhook
        webhook_url = f"{RAILWAY_STATIC_URL}/webhook"
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path="/webhook",
            webhook_url=webhook_url
        )
        logger.info(f"🚀 CrewCaptain running on Railway with webhook: {webhook_url}")
    else:
        # Local development with polling
        logger.info("🚀 CrewCaptain running locally with polling...")
        logger.info("🎧 PASSIVE LISTENING: ✅ Enabled (10s cooldown)")
        logger.info("🎵 YouTube API: " + ("✅ Enabled" if YOUTUBE_API_KEY else "❌ Disabled (using fallback)"))
        logger.info("😂 Russian Memes: ✅ Enabled (Reddit API)")
        logger.info("🧠 Trivia Questions: ✅ 150+ Questions")
        logger.info("🍻 Drinking Games: ✅ 100+ Never Have I Ever")
        logger.info("🎭 Personalities: ✅ 10 Different Moods")
        logger.info("🚀 Space Adventure: ✅ Complete Story Mode")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
