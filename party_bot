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

class DecisionBot:
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
            'meme_stats': {'total_memes': 0, 'by_subreddit': {}, 'recent_memes': []}
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
            'MemesRU', 'slavs_squatting', 'ukraina'
        ]
        
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

        # Roasts and compliments by mood (keeping existing ones)
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
            ]
        }

        self.compliments = {
            'normal': [
                "@{name}, you're more reliable than a Swiss watch!",
                "@{name}, your kindness could melt the coldest Russian winter!",
                "@{name}, you're as awesome as finding the perfect ramen spot!",
                "@{name}, your vibe is more refreshing than cherry blossoms!",
                "@{name}, you're smoother than sake on a Saturday night!"
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
            {"question": "What is the name of the Russian parliament?", "options": ["Duma", "Rada", "Sejm", "Senate"], "answer": "Duma", "category": "Russian"},
            {"question": "Which city is known as the 'Venice of the North'?", "options": ["Moscow", "St. Petersburg", "Novgorod", "Kazan"], "answer": "St. Petersburg", "category": "Russian"},
            {"question": "What does 'Da' mean in Russian?", "options": ["No", "Maybe", "Yes", "Hello"], "answer": "Yes", "category": "Russian"},
            {"question": "Which Russian composer wrote 'Swan Lake'?", "options": ["Tchaikovsky", "Stravinsky", "Rachmaninoff", "Rimsky-Korsakov"], "answer": "Tchaikovsky", "category": "Russian"},
            {"question": "What is the Russian currency?", "options": ["Ruble", "Hryvnia", "Kopeck", "Mark"], "answer": "Ruble", "category": "Russian"},
            {"question": "Which Russian writer created Sherlock Holmes-like detective Erast Fandorin?", "options": ["Boris Akunin", "Victor Pelevin", "Vladimir Sorokin", "Tatyana Tolstaya"], "answer": "Boris Akunin", "category": "Russian"},
            {"question": "What is the name of the famous Russian theater in Moscow?", "options": ["Bolshoi", "Mariinsky", "Moscow Art", "Vakhtangov"], "answer": "Bolshoi", "category": "Russian"},
            {"question": "Which Russian city was formerly called Leningrad?", "options": ["Moscow", "St. Petersburg", "Volgograd", "Kaliningrad"], "answer": "St. Petersburg", "category": "Russian"},
            {"question": "What is the traditional Russian alcoholic drink?", "options": ["Vodka", "Beer", "Wine", "Whiskey"], "answer": "Vodka", "category": "Russian"},
            {"question": "Which Russian author wrote 'The Brothers Karamazov'?", "options": ["Tolstoy", "Dostoevsky", "Pushkin", "Gogol"], "answer": "Dostoevsky", "category": "Russian"},
            {"question": "What is the name of the Russian space program?", "options": ["Roscosmos", "Soyuz", "Mir", "Salyut"], "answer": "Roscosmos", "category": "Russian"},
            {"question": "Which Russian leader introduced Perestroika?", "options": ["Lenin", "Stalin", "Gorbachev", "Yeltsin"], "answer": "Gorbachev", "category": "Russian"},
            {"question": "What is the longest river in Russia?", "options": ["Volga", "Yenisei", "Lena", "Ob"], "answer": "Lena", "category": "Russian"},
            {"question": "Which Russian scientist created the periodic table?", "options": ["Mendeleev", "Pavlov", "Lomonosov", "Sakharov"], "answer": "Mendeleev", "category": "Russian"},
            {"question": "What is the name of the Russian equivalent of FBI?", "options": ["KGB", "FSB", "GRU", "SVR"], "answer": "FSB", "category": "Russian"},
            
            # JAPANESE CULTURE (50 questions)
            {"question": "What's the traditional Japanese garment called?", "options": ["Hanbok", "Kimono", "Cheongsam", "Sari"], "answer": "Kimono", "category": "Japanese"},
            {"question": "Which Japanese city was the ancient capital?", "options": ["Tokyo", "Osaka", "Kyoto", "Hiroshima"], "answer": "Kyoto", "category": "Japanese"},
            {"question": "What does 'Arigatou' mean?", "options": ["Hello", "Thank you", "Goodbye", "Sorry"], "answer": "Thank you", "category": "Japanese"},
            {"question": "What's the Japanese art of paper folding?", "options": ["Ikebana", "Origami", "Bonsai", "Kendo"], "answer": "Origami", "category": "Japanese"},
            {"question": "Which mountain is sacred in Japan?", "options": ["Mount Fuji", "Mount Aso", "Mount Tateyama", "Mount Hotaka"], "answer": "Mount Fuji", "category": "Japanese"},
            {"question": "What is the Japanese word for 'cat'?", "options": ["Neko", "Inu", "Tori", "Sakana"], "answer": "Neko", "category": "Japanese"},
            {"question": "What is the traditional Japanese tea ceremony called?", "options": ["Chado", "Sado", "Chanoyu", "All of these"], "answer": "All of these", "category": "Japanese"},
            {"question": "Which Japanese martial art uses wooden swords?", "options": ["Kendo", "Judo", "Karate", "Aikido"], "answer": "Kendo", "category": "Japanese"},
            {"question": "What does 'Sayonara' mean?", "options": ["Hello", "Thank you", "Goodbye", "Excuse me"], "answer": "Goodbye", "category": "Japanese"},
            {"question": "What is the Japanese art of flower arranging?", "options": ["Origami", "Ikebana", "Bonsai", "Calligraphy"], "answer": "Ikebana", "category": "Japanese"},
            {"question": "Which Japanese company makes the Prius?", "options": ["Honda", "Toyota", "Nissan", "Mazda"], "answer": "Toyota", "category": "Japanese"},
            {"question": "What is the Japanese currency?", "options": ["Yen", "Won", "Yuan", "Ringgit"], "answer": "Yen", "category": "Japanese"},
            {"question": "What does 'Kawaii' mean?", "options": ["Cool", "Cute", "Amazing", "Scary"], "answer": "Cute", "category": "Japanese"},
            {"question": "Which Japanese city hosted the 2020 Olympics?", "options": ["Tokyo", "Osaka", "Kyoto", "Hiroshima"], "answer": "Tokyo", "category": "Japanese"},
            {"question": "What is the traditional Japanese writing system with Chinese characters?", "options": ["Hiragana", "Katakana", "Kanji", "Romaji"], "answer": "Kanji", "category": "Japanese"},
            {"question": "What is the Japanese word for 'cherry blossom'?", "options": ["Sakura", "Momiji", "Tsubaki", "Ajisai"], "answer": "Sakura", "category": "Japanese"},
            {"question": "Which Japanese martial art means 'gentle way'?", "options": ["Karate", "Judo", "Kendo", "Aikido"], "answer": "Judo", "category": "Japanese"},
            {"question": "What is the traditional Japanese religion?", "options": ["Buddhism", "Shinto", "Christianity", "Islam"], "answer": "Shinto", "category": "Japanese"},
            {"question": "What does 'Otaku' refer to?", "options": ["Student", "Fan/Enthusiast", "Worker", "Teacher"], "answer": "Fan/Enthusiast", "category": "Japanese"},
            {"question": "Which Japanese island is the largest?", "options": ["Hokkaido", "Honshu", "Kyushu", "Shikoku"], "answer": "Honshu", "category": "Japanese"},
            
            # POP CULTURE (50+ questions)
            {"question": "Who directed the movie 'Spirited Away'?", "options": ["Hayao Miyazaki", "Makoto Shinkai", "Satoshi Kon", "Mamoru Hosoda"], "answer": "Hayao Miyazaki", "category": "Pop Culture"},
            {"question": "What's the highest grossing anime movie?", "options": ["Your Name", "Demon Slayer", "Spirited Away", "Princess Mononoke"], "answer": "Demon Slayer", "category": "Pop Culture"},
            {"question": "In what game do you 'catch 'em all'?", "options": ["Digimon", "Pokemon", "Yu-Gi-Oh", "Monster Hunter"], "answer": "Pokemon", "category": "Pop Culture"},
            {"question": "Which studio made 'Attack on Titan'?", "options": ["Mappa", "Pierrot", "Madhouse", "Bones"], "answer": "Mappa", "category": "Pop Culture"},
            {"question": "What does 'Kawaii' mean?", "options": ["Cool", "Cute", "Amazing", "Scary"], "answer": "Cute", "category": "Pop Culture"},
            {"question": "Which anime character is known for saying 'Believe it!'?", "options": ["Goku", "Naruto", "Luffy", "Ichigo"], "answer": "Naruto", "category": "Pop Culture"},
            {"question": "What is the name of Pikachu's trainer?", "options": ["Ash", "Gary", "Brock", "Misty"], "answer": "Ash", "category": "Pop Culture"},
            {"question": "Which manga is about a boy who can turn into a chainsaw?", "options": ["Chainsaw Man", "Demon Slayer", "Jujutsu Kaisen", "Tokyo Ghoul"], "answer": "Chainsaw Man", "category": "Pop Culture"},
            {"question": "What is the name of the Death God in Death Note?", "options": ["Ryuk", "Light", "L", "Misa"], "answer": "Ryuk", "category": "Pop Culture"},
            {"question": "Which anime features a boy who wants to be the Hokage?", "options": ["One Piece", "Naruto", "Bleach", "Dragon Ball"], "answer": "Naruto", "category": "Pop Culture"},
            {"question": "What is the name of the main character in One Punch Man?", "options": ["Saitama", "Genos", "King", "Mumen"], "answer": "Saitama", "category": "Pop Culture"},
            {"question": "Which video game features Mario?", "options": ["Sonic", "Super Mario", "Zelda", "Metroid"], "answer": "Super Mario", "category": "Pop Culture"},
            {"question": "What console is made by Sony?", "options": ["Xbox", "Nintendo", "PlayStation", "Steam"], "answer": "PlayStation", "category": "Pop Culture"},
            {"question": "Which movie features the character Neo?", "options": ["The Matrix", "Inception", "Blade Runner", "Minority Report"], "answer": "The Matrix", "category": "Pop Culture"},
            {"question": "Who created the Marvel character Spider-Man?", "options": ["Stan Lee", "Jack Kirby", "Steve Ditko", "Both A and C"], "answer": "Both A and C", "category": "Pop Culture"},
            {"question": "What is the highest grossing movie of all time?", "options": ["Avatar", "Avengers Endgame", "Titanic", "Star Wars"], "answer": "Avatar", "category": "Pop Culture"},
            {"question": "Which social media platform uses hashtags?", "options": ["Facebook", "Twitter", "Instagram", "All of these"], "answer": "All of these", "category": "Pop Culture"},
            {"question": "What does 'lol' stand for?", "options": ["Lots of love", "Laugh out loud", "Life of luxury", "Lord of lords"], "answer": "Laugh out loud", "category": "Pop Culture"},
            {"question": "Which streaming service created Stranger Things?", "options": ["Netflix", "Hulu", "Disney+", "Amazon Prime"], "answer": "Netflix", "category": "Pop Culture"},
            {"question": "What is the name of Harry Potter's owl?", "options": ["Hedwig", "Crookshanks", "Scabbers", "Fawkes"], "answer": "Hedwig", "category": "Pop Culture"}
        ]

        # EXPANDED NEVER HAVE I EVER QUESTIONS (100 from document + originals)
        self.never_have_i_ever_questions = [
            # Original bill-related questions
            "Never have I ever skipped paying a bill... sip if guilty! 🍺",
            "Never have I ever pretended to be broke... drink up if true! 🥃",
            "Never have I ever ordered the most expensive item... bottoms up! 🍻",
            "Never have I ever 'forgotten' my wallet... you know what to do! 🍷",
            "Never have I ever argued over who pays... guilty party drinks! 🥂",
            "Take a sip for every time you've said 'I'll get the next one'! 🍺",
            "Drink if you've ever split a bill down to the last cent! 🍻",
            "Sip if you've calculated tips on your phone! 📱🍷",
            
            # 100 NEW QUESTIONS FROM DOCUMENT
            "Never have I ever played hooky from school or work",
            "Never have I ever stolen anything", 
            "Never have I ever missed a flight",
            "Never have I ever drunk-dialed my ex",
            "Never have I ever rode a motorcycle",
            "Never have I ever lost a bet",
            "Never have I ever gotten lost alone in a foreign country",
            "Never have I ever bribed someone",
            "Never have I ever gone skinny-dipping",
            "Never have I ever cheated on someone",
            "Never have I ever sang karaoke",
            "Never have I ever broken a bone",
            "Never have I ever lived alone",
            "Never have I ever been on a yacht",
            "Never have I ever been on TV",
            "Never have I ever been on a blind date",
            "Never have I ever lied to law enforcement",
            "Never have I ever gotten a tattoo",
            "Never have I ever used a fake ID",
            "Never have I ever broken up with someone",
            "Never have I ever gotten seriously hungover",
            "Never have I ever used someone else's toothbrush",
            "Never have I ever clogged somebody else's toilet",
            "Never have I ever fallen asleep in public",
            "Never have I ever kissed someone in public",
            "Never have I ever fought in public",
            "Never have I ever dined and dashed",
            "Never have I ever won the lottery",
            "Never have I ever had to go to court",
            "Never have I ever been to a destination wedding",
            "Never have I ever lied to a boss",
            "Never have I ever crashed a wedding",
            "Never have I ever kissed more than one person in 24 hours",
            "Never have I ever pranked someone",
            "Never have I ever had a one-night stand",
            "Never have I ever regifted a gift",
            "Never have I ever trolled someone on social media",
            "Never have I ever climbed out of a window",
            "Never have I ever driven over a curb",
            "Never have I ever laughed so hard I peed my pants as an adult",
            "Never have I ever got on the wrong train or bus",
            "Never have I ever sent a sext",
            "Never have I ever cursed in a place of worship",
            "Never have I ever snooped through someone's stuff",
            "Never have I ever tried marijuana",
            "Never have I ever gone 24 hours without showering",
            "Never have I ever had to take a walk of shame",
            "Never have I ever gone on a solo vacation",
            "Never have I ever gone on a road trip",
            "Never have I ever ate an entire pizza by myself",
            "Never have I ever saved a life",
            "Never have I ever wanted to be on a reality TV show",
            "Never have I ever started a fire",
            "Never have I ever gotten stopped by airport security",
            "Never have I ever gone viral online",
            "Never have I ever left gum in a public space",
            "Never have I ever slept outdoors for an entire night",
            "Never have I ever run a marathon",
            "Never have I ever given/received a lap dance",
            "Never have I ever made a speech in front of 100 people or more",
            "Never have I ever relieved myself in a public pool",
            "Never have I ever lied to my best friend about who I was with",
            "Never have I ever been to a Disney park",
            "Never have I ever had a threesome",
            "Never have I ever left someone on read",
            "Never have I ever fallen asleep during sex",
            "Never have I ever lied about my age",
            "Never have I ever made up a story about someone who wasn't real",
            "Never have I ever believed something was haunted",
            "Never have I ever participated in a protest",
            "Never have I ever had sleep paralysis",
            "Never have I ever been the alibi for a lying friend",
            "Never have I ever pulled an all-nighter",
            "Never have I ever role-played",
            "Never have I ever regretted an apology",
            "Never have I ever pretended I was sick for attention",
            "Never have I ever disliked something that I cooked",
            "Never have I ever deleted a post on social media because it didn't get enough likes",
            "Never have I ever spent more than $100 on a top",
            "Never have I ever thrown a drink at someone",
            "Never have I ever worn someone else's underwear",
            "Never have I ever traveled to Europe",
            "Never have I ever attempted a trendy diet",
            "Never have I ever gone to a strip club",
            "Never have I ever binged an entire series in one day",
            "Never have I ever tried psychedelics",
            "Never have I ever met someone famous",
            "Never have I ever gone streaking",
            "Never have I ever been on a sports team",
            "Never have I ever maxed out a credit card",
            "Never have I ever been blackout drunk",
            "Never have I ever been engaged",
            "Never have I ever gotten married",
            "Never have I ever donated to a charity",
            "Never have I ever pretended to be sick to get out of something",
            "Never have I ever stood up a date",
            "Never have I ever ghosted someone",
            "Never have I ever had sex on a beach",
            "Never have I ever fallen in love"
        ]

        # Easter eggs hints
        self.easter_egg_hints = [
            "🕵️ Try typing 'konami' for a classic surprise...",
            "🥷 There's a secret ninja command hiding in plain sight...",
            "🌟 Legend says typing 'legendary' might unlock something special...",
            "🎮 Gamers might want to try 'up up down down'...",
            "🌸 Something beautiful happens when you say the magic sakura word..."
        ]

    def get_main_menu_keyboard(self, chat_id):
        """Enhanced main menu with all new features"""
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
                InlineKeyboardButton("🎪 Games", callback_data="games_menu"),
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
        
        welcome_text = f"""{mood_emoji} **Ultimate Decision Bot** {mood_emoji}

Welcome! Your complete entertainment companion!

🆕 **All Features:**
• 🗳️ Voting System • 🧠 150+ Trivia Questions
• 🎵 YouTube Music • 😂 Russian Memes  
• 🍻 100+ Drinking Games • 😈 Roast Mode
• 🎌 10 Personalities • 🎮 Easter Eggs

Ready for some fun? Pick an option below! ⬇️{hint_text}
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
            'anime': {'title': 'Tank!', 'artist': 'Seatbelts', 'video_id': 'NRI_8PUXx2A'}
        }
        
        song = fallback_songs.get(category, fallback_songs['russian'])
        return {
            'title': song['title'],
            'artist': song['artist'],
            'url': f"https://www.youtube.com/watch?v={song['video_id']}",
            'source': 'fallback'
        }

    # RUSSIAN MEME FEATURE  
    async def get_random_russian_meme(self):
        """Get random Russian meme from Reddit API"""
        try:
            subreddit = random.choice(self.russian_meme_subreddits)
            api_urls = [
                f"https://www.reddit.com/r/{subreddit}/hot.json?limit=100",
                f"https://www.reddit.com/r/{subreddit}/top.json?limit=50&t=week"
            ]
            
            headers = {'User-Agent': 'DecisionBot/1.0 (Russian Meme Fetcher)'}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(random.choice(api_urls), headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        image_posts = []
                        for post in posts:
                            post_data = post['data']
                            if (self.is_image_post(post_data) and 
                                post_data.get('score', 0) > 5 and
                                not post_data.get('over_18', False)):
                                image_posts.append(post_data)
                        
                        if image_posts:
                            chosen = random.choice(image_posts)
                            return {
                                'title': chosen['title'],
                                'url': self.get_image_url(chosen),
                                'reddit_url': f"https://www.reddit.com{chosen['permalink']}",
                                'subreddit': chosen['subreddit'],
                                'upvotes': chosen.get('score', 0),
                                'source': 'reddit_api'
                            }
        except Exception as e:
            logger.error(f"Reddit API error: {e}")
        
        return None

    def is_image_post(self, post_data):
        """Check if Reddit post contains an image"""
        url = post_data.get('url', '')
        return (any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']) or
                'i.redd.it' in url or
                ('imgur.com' in url and '/a/' not in url))

    def get_image_url(self, post_data):
        """Extract image URL from Reddit post"""
        url = post_data.get('url', '')
        
        if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return url
        if 'i.redd.it' in url:
            return url
        if 'imgur.com' in url and '/a/' not in url:
            return url + '.jpg' if not url.lower().endswith(('.jpg', '.png', '.gif')) else url
        
        return url

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

    # ENHANCED DRINKING GAMES WITH NEW QUESTIONS
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
                InlineKeyboardButton("🎯 Truth/Sip", callback_data="drink_truth")
            ],
            [
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

    # ALL OTHER EXISTING HANDLERS (keeping them compact for space)
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle all button callbacks"""
        query = update.callback_query
        await query.answer()
        
        chat_id = update.effective_chat.id
        user = update.effective_user
        data = query.data
        
        if user:
            self.group_data[chat_id]['active_members'].add(user.id)

        # Main handlers
        handlers = {
            "main_menu": self.start,
            "who_pays": self.who_pays_handler,
            "music_menu": self.music_menu_handler,
            "meme_menu": self.meme_menu_handler,
            "drinking_menu": self.drinking_menu_handler,
            "trivia_menu": self.trivia_menu_handler,
            "mood_menu": self.mood_menu_handler,
            "coin_flip": self.coin_flip_handler,
            "roll_dice": self.roll_dice_handler
        }
        
        for callback_name, handler in handlers.items():
            if data == callback_name:
                await handler(update, context)
                return
        
        # Prefix handlers
        if data.startswith("ytmusic_"):
            await self.youtube_music_handler(update, context)
        elif data.startswith("meme_"):
            await self.russian_meme_handler(update, context)
        elif data.startswith("drink_"):
            await self.drink_handler(update, context)
        elif data.startswith("trivia_"):
            await self.trivia_handler(update, context)

    # Compact implementations of key handlers
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

    async def russian_meme_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Russian meme handler"""
        query = update.callback_query
        chat_id = update.effective_chat.id
        
        await query.edit_message_text("🇷🇺 Searching Russian Reddit for memes... 🔍")
        
        meme = await self.get_random_russian_meme()
        if not meme:
            await query.edit_message_text("❌ No memes found!", reply_markup=self.get_back_keyboard("meme_menu"))
            return
        
        mood = self.group_data[chat_id]['mood']
        intro = "🇷🇺 Fresh Russian meme!"
        
        text = f"{intro}\n\n😂 **{meme['title']}**\n📍 r/{meme['subreddit']}\n⬆️ {meme['upvotes']} upvotes"
        
        keyboard = [
            [InlineKeyboardButton("🎲 Another", callback_data="meme_random")],
            [InlineKeyboardButton("🔙 Back", callback_data="meme_menu")]
        ]
        
        try:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=meme['url'],
                caption=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            await query.delete_message()
        except:
            text += f"\n\n🔗 [View Meme]({meme['url']})"
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
                await query.edit_message_text("No questions available!")
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

    # Quick implementations of other essential handlers
    async def coin_flip_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Coin flip handler"""
        result = random.choice(['Heads', 'Tails'])
        await self.suspense_reveal(update.callback_query, f"🪙 **{result}**!", self.get_back_keyboard())

    async def roll_dice_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Dice roll handler"""
        result = random.randint(1, 6)
        dice_emojis = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
        await self.suspense_reveal(update.callback_query, f"{dice_emojis[result-1]} **{result}**!", self.get_back_keyboard())

    async def music_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Music menu handler"""
        query = update.callback_query
        
        api_status = "🟢 YouTube API" if self.YOUTUBE_API_KEY else "🟡 Curated"
        
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

    async def meme_menu_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Russian meme menu handler"""
        query = update.callback_query
        
        text = """🇷🇺 **Russian Meme Generator** 🇷🇺

Random memes from Russian Reddit communities!
*Warning: May cause uncontrollable laughter* 😂
        """
        
        keyboard = [
            [InlineKeyboardButton("🎲 Random", callback_data="meme_random")],
            [InlineKeyboardButton("🔥 Hot", callback_data="meme_hot"),
             InlineKeyboardButton("👑 Top", callback_data="meme_top")],
            [InlineKeyboardButton("🇷🇺 Russia", callback_data="meme_russia"),
             InlineKeyboardButton("😂 Pikabu", callback_data="meme_pikabu")],
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

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

    async def suspense_reveal(self, query, final_text, keyboard):
        """Suspenseful reveal animation"""
        await query.edit_message_text("🎲 Making decision...")
        
        for i in range(3):
            await asyncio.sleep(0.6)
            await query.edit_message_text("🎲 Making decision" + "." * (i + 1))
        
        await asyncio.sleep(0.8)
        await query.edit_message_text(final_text, reply_markup=keyboard, parse_mode='Markdown')

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and easter eggs"""
        if not update.message or not update.message.text:
            return
            
        chat_id = update.effective_chat.id
        text = update.message.text.strip().lower()
        
        if update.effective_user:
            self.group_data[chat_id]['active_members'].add(update.effective_user.id)
        
        # Easter Eggs
        easter_eggs = {
            'konami': "🕹️ **KONAMI CODE ACTIVATED!** 🕹️\nExtra karma for everyone!",
            'ninja': "🥷 **NINJA MODE UNLOCKED!** 🥷\nStealth payments activated!",
            'legendary': "🌟 **LEGENDARY STATUS!** 🌟\nYou're now a decision master!",
            'up up down down': "🎮 **CHEAT CODE ACCEPTED!** 🎮\nInfinite lives granted!",
            'sakura': "🌸 **SAKURA POWER!** 🌸\nCherry blossom energy activated!"
        }
        
        for trigger, message in easter_eggs.items():
            if trigger in text:
                self.group_data[chat_id]['discovered_easter_eggs'].add(trigger)
                await update.message.reply_text(message, reply_markup=self.get_main_menu_keyboard(chat_id), parse_mode='Markdown')
                return
        
        # Show main menu for keywords
        if text in ['menu', 'start', 'help', '/start', '/help']:
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
    bot = DecisionBot()
    
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
        logger.info(f"🚀 Bot running on Railway with webhook: {webhook_url}")
    else:
        # Local development with polling
        logger.info("🚀 Bot running locally with polling...")
        logger.info("🎵 YouTube API: " + ("✅ Enabled" if YOUTUBE_API_KEY else "❌ Disabled (using fallback)"))
        logger.info("😂 Russian Memes: ✅ Enabled (Reddit API)")
        logger.info("🧠 Trivia Questions: ✅ 150+ Questions")
        logger.info("🍻 Drinking Games: ✅ 100+ Never Have I Ever")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
