from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from enum import Enum
import json
import asyncio
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# OpenAI Setup
import openai
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Create the main app without a prefix
app = FastAPI(title="Pathshala Coach API", description="AI-Powered Adaptive Microlearning for Competitive Exams")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class SubjectType(str, Enum):
    QUANTITATIVE = "quantitative"
    REASONING = "reasoning"
    ENGLISH = "english"
    GENERAL_KNOWLEDGE = "general_knowledge"
    CURRENT_AFFAIRS = "current_affairs"

class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class Language(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"

# Pydantic Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    phone: str
    target_exam: str  # SSC, Banking, State PSC
    preferred_language: Language = Language.ENGLISH
    skill_levels: Dict[str, str] = Field(default_factory=dict)  # subject -> difficulty
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    subject: SubjectType
    difficulty: DifficultyLevel
    question_text_en: str
    question_text_hi: str
    options_en: List[str]
    options_hi: List[str]
    correct_answer: int  # index of correct option
    explanation_en: str
    explanation_hi: str
    exam_type: str  # SSC, Banking, etc.

class Answer(BaseModel):
    question_id: str
    selected_option: int
    is_correct: bool
    time_taken: int  # in seconds

class Assessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    test_type: str  # diagnostic, practice, mock
    questions: List[str]  # question IDs
    answers: List[Answer] = Field(default_factory=list)
    score: float = 0.0
    subject_scores: Dict[str, float] = Field(default_factory=dict)
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StudyPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    date: str  # YYYY-MM-DD format
    subjects: List[str]
    questions_count: int = 20
    estimated_time: int = 20  # minutes
    status: str = "pending"  # pending, completed, skipped
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
class UserCreate(BaseModel):
    name: str
    phone: str
    target_exam: str
    preferred_language: Language = Language.ENGLISH

class QuestionRequest(BaseModel):
    user_id: str
    subject: Optional[SubjectType] = None
    difficulty: Optional[DifficultyLevel] = None
    count: int = 1
    language: Language = Language.ENGLISH

class SubmitAnswerRequest(BaseModel):
    assessment_id: str
    question_id: str
    selected_option: int
    time_taken: int

class FeedbackRequest(BaseModel):
    question_id: str
    user_answer: int
    language: Language = Language.ENGLISH

# Sample question bank - expanded to avoid repetition
SAMPLE_QUESTIONS = [
    {
        "subject": "quantitative",
        "difficulty": "beginner",
        "question_text_en": "What is 25% of 800?",
        "question_text_hi": "800 का 25% क्या है?",
        "options_en": ["150", "200", "250", "300"],
        "options_hi": ["150", "200", "250", "300"],
        "correct_answer": 1,
        "explanation_en": "25% of 800 = (25/100) × 800 = 200",
        "explanation_hi": "800 का 25% = (25/100) × 800 = 200",
        "exam_type": "SSC"
    },
    {
        "subject": "quantitative",
        "difficulty": "beginner", 
        "question_text_en": "If a man buys 12 apples for Rs. 60, what is the cost of one apple?",
        "question_text_hi": "यदि एक व्यक्ति 60 रुपये में 12 सेब खरीदता है, तो एक सेब की कीमत क्या है?",
        "options_en": ["Rs. 4", "Rs. 5", "Rs. 6", "Rs. 7"],
        "options_hi": ["₹4", "₹5", "₹6", "₹7"],
        "correct_answer": 1,
        "explanation_en": "Cost of one apple = Total cost / Number of apples = 60/12 = Rs. 5",
        "explanation_hi": "एक सेब की कीमत = कुल कीमत / सेब की संख्या = 60/12 = ₹5",
        "exam_type": "SSC"
    },
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "A train travels 180 km in 3 hours. What is its speed in km/hr?",
        "question_text_hi": "एक ट्रेन 3 घंटे में 180 किमी की यात्रा करती है। इसकी गति किमी/घंटा में क्या है?",
        "options_en": ["50 km/hr", "60 km/hr", "70 km/hr", "80 km/hr"],
        "options_hi": ["50 किमी/घंटा", "60 किमी/घंटा", "70 किमी/घंटा", "80 किमी/घंटा"],
        "correct_answer": 1,
        "explanation_en": "Speed = Distance / Time = 180 km / 3 hours = 60 km/hr",
        "explanation_hi": "गति = दूरी / समय = 180 किमी / 3 घंटे = 60 किमी/घंटा",
        "exam_type": "SSC"
    },
    {
        "subject": "reasoning",
        "difficulty": "beginner",
        "question_text_en": "If CODING is written as DPEJOH, how is FILING written?",
        "question_text_hi": "यदि CODING को DPEJOH लिखा जाता है, तो FILING कैसे लिखा जाएगा?",
        "options_en": ["GJMJOH", "GJMJPI", "GJLJOH", "GJMJNG"],
        "options_hi": ["GJMJOH", "GJMJPI", "GJLJOH", "GJMJNG"],
        "correct_answer": 0,
        "explanation_en": "Each letter is shifted by +1 in the alphabet. F→G, I→J, L→M, I→J, N→O, G→H",
        "explanation_hi": "प्रत्येक अक्षर को वर्णमाला में +1 से बदला जाता है। F→G, I→J, L→M, I→J, N→O, G→H",
        "exam_type": "SSC"
    },
    {
        "subject": "reasoning",
        "difficulty": "beginner",
        "question_text_en": "Complete the series: 2, 4, 8, 16, ?",
        "question_text_hi": "श्रृंखला पूरी करें: 2, 4, 8, 16, ?",
        "options_en": ["24", "28", "32", "36"],
        "options_hi": ["24", "28", "32", "36"],
        "correct_answer": 2,
        "explanation_en": "Each number is double the previous number. 16 × 2 = 32",
        "explanation_hi": "प्रत्येक संख्या पिछली संख्या की दोगुनी है। 16 × 2 = 32",
        "exam_type": "Banking"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "In a certain code, CAT is written as FDW. How is DOG written?",
        "question_text_hi": "एक निश्चित कूट में, CAT को FDW लिखा जाता है। DOG कैसे लिखा जाएगा?",
        "options_en": ["GRJ", "ERK", "FQI", "HRL"],
        "options_hi": ["GRJ", "ERK", "FQI", "HRL"],
        "correct_answer": 0,
        "explanation_en": "Each letter is shifted by +3 positions: D→G, O→R, G→J",
        "explanation_hi": "प्रत्येक अक्षर को +3 स्थान आगे बढ़ाया गया है: D→G, O→R, G→J",
        "exam_type": "SSC"
    },
    {
        "subject": "english",
        "difficulty": "beginner",
        "question_text_en": "Choose the correct synonym for 'ABUNDANT':",
        "question_text_hi": "'ABUNDANT' का सही समानार्थी शब्द चुनें:",
        "options_en": ["Scarce", "Plentiful", "Limited", "Rare"],
        "options_hi": ["दुर्लभ", "प्रचुर", "सीमित", "कम"],
        "correct_answer": 1,
        "explanation_en": "Abundant means existing in large quantities; plentiful.",
        "explanation_hi": "Abundant का अर्थ है बड़ी मात्रा में मौजूद; प्रचुर।",
        "exam_type": "Banking"
    },
    {
        "subject": "english",
        "difficulty": "beginner",
        "question_text_en": "Choose the correct antonym for 'HAPPY':",
        "question_text_hi": "'HAPPY' का सही विपरीतार्थी शब्द चुनें:",
        "options_en": ["Joyful", "Sad", "Cheerful", "Pleased"],
        "options_hi": ["खुशी", "दुखी", "प्रसन्न", "संतुष्ट"],
        "correct_answer": 1,
        "explanation_en": "The antonym of happy is sad.",
        "explanation_hi": "Happy का विपरीतार्थी शब्द sad है।",
        "exam_type": "SSC"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Fill in the blank: The meeting was _____ due to rain.",
        "question_text_hi": "रिक्त स्थान भरें: बारिश के कारण बैठक _____ थी।",
        "options_en": ["called off", "called on", "called up", "called for"],
        "options_hi": ["रद्द कर दी गई", "बुलाई गई", "फोन किया गया", "मांग की गई"],
        "correct_answer": 0,
        "explanation_en": "'Called off' means cancelled or postponed.",
        "explanation_hi": "'Called off' का अर्थ है रद्द या स्थगित करना।",
        "exam_type": "Banking"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "beginner",
        "question_text_en": "Who is the current President of India (as of 2024)?",
        "question_text_hi": "भारत के वर्तमान राष्ट्रपति कौन हैं (2024 तक)?",
        "options_en": ["Ram Nath Kovind", "Droupadi Murmu", "Pranab Mukherjee", "A.P.J. Abdul Kalam"],
        "options_hi": ["राम नाथ कोविंद", "द्रौपदी मुर्मू", "प्रणब मुखर्जी", "ए.पी.जे. अब्दुल कलाम"],
        "correct_answer": 1,
        "explanation_en": "Droupadi Murmu is the current President of India, serving since July 2022.",
        "explanation_hi": "द्रौपदी मुर्मू भारत की वर्तमान राष्ट्रपति हैं, जो जुलाई 2022 से सेवा कर रही हैं।",
        "exam_type": "State PSC"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "beginner",
        "question_text_en": "What is the capital of India?",
        "question_text_hi": "भारत की राजधानी क्या है?",
        "options_en": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
        "options_hi": ["मुंबई", "नई दिल्ली", "कोलकाता", "चेन्नई"],
        "correct_answer": 1,
        "explanation_en": "New Delhi is the capital of India.",
        "explanation_hi": "नई दिल्ली भारत की राजधानी है।",
        "exam_type": "SSC"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Which river is known as the 'Ganga of South India'?",
        "question_text_hi": "कौन सी नदी को 'दक्षिण भारत की गंगा' कहा जाता है?",
        "options_en": ["Krishna", "Godavari", "Cauvery", "Tungabhadra"],
        "options_hi": ["कृष्णा", "गोदावरी", "कावेरी", "तुंगभद्रा"],
        "correct_answer": 1,
        "explanation_en": "Godavari is known as the 'Ganga of South India' due to its length and cultural significance.",
        "explanation_hi": "गोदावरी को इसकी लंबाई और सांस्कृतिक महत्व के कारण 'दक्षिण भारत की गंगा' कहा जाता है।",
        "exam_type": "State PSC"
    }
]

# Mock data for when OpenAI API fails
MOCK_ADAPTIVE_QUESTIONS = [
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "If 2x + 3y = 12 and x - y = 1, what is the value of x?",
        "question_text_hi": "यदि 2x + 3y = 12 और x - y = 1, तो x का मान क्या है?",
        "options_en": ["2", "3", "4", "5"],
        "options_hi": ["2", "3", "4", "5"],
        "correct_answer": 1,
        "explanation_en": "Solving the system: x = 3, y = 2",
        "explanation_hi": "समीकरण हल करने पर: x = 3, y = 2",
        "exam_type": "SSC"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "If A is taller than B, and B is taller than C, who is the shortest?",
        "question_text_hi": "यदि A, B से लंबा है और B, C से लंबा है, तो सबसे छोटा कौन है?",
        "options_en": ["A", "B", "C", "Cannot be determined"],
        "options_hi": ["A", "B", "C", "निर्धारित नहीं किया जा सकता"],
        "correct_answer": 2,
        "explanation_en": "C is shorter than B, and B is shorter than A, so C is the shortest.",
        "explanation_hi": "C, B से छोटा है और B, A से छोटा है, इसलिए C सबसे छोटा है।",
        "exam_type": "Banking"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Choose the correct form: The committee _____ divided in their opinions.",
        "question_text_hi": "सही रूप चुनें: समिति अपनी राय में _____ विभाजित थी।",
        "options_en": ["is", "are", "was", "were"],
        "options_hi": ["is", "are", "was", "were"],
        "correct_answer": 3,
        "explanation_en": "'Committee' when referring to individual members takes plural verb 'were'.",
        "explanation_hi": "'Committee' जब व्यक्तिगत सदस्यों को संदर्भित करता है तो बहुवचन क्रिया 'were' लेता है।",
        "exam_type": "SSC"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Which state in India has the highest literacy rate?",
        "question_text_hi": "भारत में किस राज्य की साक्षरता दर सबसे अधिक है?",
        "options_en": ["Kerala", "Tamil Nadu", "Maharashtra", "Karnataka"],
        "options_hi": ["केरल", "तमिलनाडु", "महाराष्ट्र", "कर्नाटक"],
        "correct_answer": 0,
        "explanation_en": "Kerala has the highest literacy rate in India at over 93%.",
        "explanation_hi": "केरल में भारत में सबसे अधिक साक्षरता दर 93% से अधिक है।",
        "exam_type": "State PSC"
    }
]

MOCK_STUDY_PLANS = [
    {
        "subjects": ["quantitative", "reasoning"],
        "focus_area": "mathematical reasoning",
        "estimated_time": 20,
        "difficulty": "intermediate"
    },
    {
        "subjects": ["english", "general_knowledge"],
        "focus_area": "language and current affairs",
        "estimated_time": 20,
        "difficulty": "beginner"
    },
    {
        "subjects": ["quantitative", "english"],
        "focus_area": "mixed practice",
        "estimated_time": 20,
        "difficulty": "intermediate"
    }
]

# Mock study plans for when OpenAI API fails
MOCK_STUDY_PLANS = [
    {
        "subjects": ["quantitative", "reasoning"],
        "description": "Focus on basic arithmetic and logical reasoning",
        "difficulty": "beginner"
    },
    {
        "subjects": ["english", "general_knowledge"],
        "description": "Improve vocabulary and current affairs knowledge",
        "difficulty": "intermediate"
    },
    {
        "subjects": ["quantitative", "english", "reasoning"],
        "description": "Balanced practice across all subjects",
        "difficulty": "mixed"
    }
]

# Mock adaptive questions for when OpenAI API fails
MOCK_ADAPTIVE_QUESTIONS = [
    # SSC Questions
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "What is 15% of 240?",
        "question_text_hi": "240 का 15% क्या है?",
        "options_en": ["30", "36", "40", "45"],
        "options_hi": ["30", "36", "40", "45"],
        "correct_answer": 1,
        "explanation_en": "15% of 240 = (15/100) × 240 = 36",
        "explanation_hi": "240 का 15% = (15/100) × 240 = 36",
        "exam_type": "SSC"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "Find the next number in series: 2, 6, 12, 20, ?",
        "question_text_hi": "श्रृंखला में अगली संख्या ज्ञात करें: 2, 6, 12, 20, ?",
        "options_en": ["28", "30", "32", "34"],
        "options_hi": ["28", "30", "32", "34"],
        "correct_answer": 1,
        "explanation_en": "Pattern: n(n+1), so 5×6 = 30",
        "explanation_hi": "पैटर्न: n(n+1), इसलिए 5×6 = 30",
        "exam_type": "SSC"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Choose the correct synonym for 'Abundant':",
        "question_text_hi": "'Abundant' के लिए सही समानार्थी शब्द चुनें:",
        "options_en": ["Scarce", "Plentiful", "Rare", "Limited"],
        "options_hi": ["कम", "प्रचुर", "दुर्लभ", "सीमित"],
        "correct_answer": 1,
        "explanation_en": "Abundant means existing in large quantities; plentiful",
        "explanation_hi": "Abundant का अर्थ है बड़ी मात्रा में मौजूद; प्रचुर",
        "exam_type": "SSC"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Who is known as the 'Father of the Indian Constitution'?",
        "question_text_hi": "किसे 'भारतीय संविधान के पिता' के रूप में जाना जाता है?",
        "options_en": ["Mahatma Gandhi", "Jawaharlal Nehru", "Dr. B.R. Ambedkar", "Sardar Patel"],
        "options_hi": ["महात्मा गांधी", "जवाहरलाल नेहरू", "डॉ. बी.आर. अंबेडकर", "सरदार पटेल"],
        "correct_answer": 2,
        "explanation_en": "Dr. B.R. Ambedkar was the chairman of the Drafting Committee",
        "explanation_hi": "डॉ. बी.आर. अंबेडकर मसौदा समिति के अध्यक्ष थे",
        "exam_type": "SSC"
    },
    {
        "subject": "quantitative",
        "difficulty": "advanced",
        "question_text_en": "If a train 150m long passes a platform 300m long in 18 seconds, find its speed in km/h.",
        "question_text_hi": "यदि 150m लंबी ट्रेन 300m लंबे प्लेटफॉर्म को 18 सेकंड में पार करती है, तो उसकी गति km/h में ज्ञात करें।",
        "options_en": ["60", "75", "90", "100"],
        "options_hi": ["60", "75", "90", "100"],
        "correct_answer": 2,
        "explanation_en": "Total distance = 150+300 = 450m, Speed = 450/18 = 25 m/s = 90 km/h",
        "explanation_hi": "कुल दूरी = 150+300 = 450m, गति = 450/18 = 25 m/s = 90 km/h",
        "exam_type": "SSC"
    },
    
    # Banking Questions
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "A sum of money doubles itself in 5 years at simple interest. In how many years will it become 4 times?",
        "question_text_hi": "एक राशि साधारण ब्याज पर 5 वर्ष में दोगुनी हो जाती है। कितने वर्षों में यह 4 गुनी हो जाएगी?",
        "options_en": ["10 years", "15 years", "20 years", "25 years"],
        "options_hi": ["10 वर्ष", "15 वर्ष", "20 वर्ष", "25 वर्ष"],
        "correct_answer": 1,
        "explanation_en": "If money doubles in 5 years, rate = 20%. To become 4 times, it needs 15 years",
        "explanation_hi": "यदि पैसा 5 वर्ष में दोगुना होता है, तो दर = 20%। 4 गुना होने के लिए 15 वर्ष चाहिए",
        "exam_type": "Banking"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "In a certain code, 'COMPUTER' is written as 'RFUVQNPC'. How is 'MEDICINE' written in that code?",
        "question_text_hi": "एक निश्चित कोड में 'COMPUTER' को 'RFUVQNPC' लिखा जाता है। उस कोड में 'MEDICINE' कैसे लिखा जाएगा?",
        "options_en": ["MFEDJJOE", "EOJDEJFM", "MJDJEOFE", "EOJDJEFM"],
        "options_hi": ["MFEDJJOE", "EOJDEJFM", "MJDJEOFE", "EOJDJEFM"],
        "correct_answer": 1,
        "explanation_en": "Each letter is replaced by the letter at the same position from the end of alphabet",
        "explanation_hi": "प्रत्येक अक्षर को वर्णमाला के अंत से समान स्थिति के अक्षर से बदला जाता है",
        "exam_type": "Banking"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Choose the correctly spelled word:",
        "question_text_hi": "सही वर्तनी वाला शब्द चुनें:",
        "options_en": ["Accommodation", "Acommodation", "Accomodation", "Acomodation"],
        "options_hi": ["Accommodation", "Acommodation", "Accomodation", "Acomodation"],
        "correct_answer": 0,
        "explanation_en": "Accommodation has double 'c' and double 'm'",
        "explanation_hi": "Accommodation में दो 'c' और दो 'm' हैं",
        "exam_type": "Banking"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Which bank is known as the 'Banker's Bank' in India?",
        "question_text_hi": "भारत में किस बैंक को 'बैंकरों का बैंक' कहा जाता है?",
        "options_en": ["SBI", "RBI", "HDFC", "ICICI"],
        "options_hi": ["SBI", "RBI", "HDFC", "ICICI"],
        "correct_answer": 1,
        "explanation_en": "RBI (Reserve Bank of India) is the central bank and banker's bank",
        "explanation_hi": "RBI (भारतीय रिजर्व बैंक) केंद्रीय बैंक और बैंकरों का बैंक है",
        "exam_type": "Banking"
    },
    {
        "subject": "quantitative",
        "difficulty": "advanced",
        "question_text_en": "A man invests Rs. 10,000 at 10% compound interest for 2 years. What is the compound interest?",
        "question_text_hi": "एक व्यक्ति 2 वर्ष के लिए 10% चक्रवृद्धि ब्याज पर 10,000 रुपये निवेश करता है। चक्रवृद्धि ब्याज क्या है?",
        "options_en": ["Rs. 2,100", "Rs. 2,200", "Rs. 2,300", "Rs. 2,400"],
        "options_hi": ["2,100 रुपये", "2,200 रुपये", "2,300 रुपये", "2,400 रुपये"],
        "correct_answer": 0,
        "explanation_en": "CI = P[(1+r/100)^n - 1] = 10000[(1.1)^2 - 1] = 10000[1.21 - 1] = 2100",
        "explanation_hi": "चक्रवृद्धि ब्याज = P[(1+r/100)^n - 1] = 10000[(1.1)^2 - 1] = 2100",
        "exam_type": "Banking"
    },
    
    # State PSC Questions
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "The average of 5 numbers is 20. If one number is excluded, the average becomes 18. What is the excluded number?",
        "question_text_hi": "5 संख्याओं का औसत 20 है। यदि एक संख्या को हटा दिया जाए, तो औसत 18 हो जाता है। हटाई गई संख्या क्या है?",
        "options_en": ["26", "28", "30", "32"],
        "options_hi": ["26", "28", "30", "32"],
        "correct_answer": 1,
        "explanation_en": "Sum of 5 numbers = 100, Sum of 4 numbers = 72, Excluded number = 100-72 = 28",
        "explanation_hi": "5 संख्याओं का योग = 100, 4 संख्याओं का योग = 72, हटाई गई संख्या = 28",
        "exam_type": "State PSC"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "If 'PEN' is coded as 'QFO', then 'INK' will be coded as:",
        "question_text_hi": "यदि 'PEN' को 'QFO' के रूप में कोड किया जाता है, तो 'INK' को कैसे कोड किया जाएगा:",
        "options_en": ["JOL", "JOM", "JON", "JOP"],
        "options_hi": ["JOL", "JOM", "JON", "JOP"],
        "correct_answer": 0,
        "explanation_en": "Each letter is moved one position forward in the alphabet",
        "explanation_hi": "प्रत्येक अक्षर वर्णमाला में एक स्थान आगे बढ़ाया जाता है",
        "exam_type": "State PSC"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Choose the correct antonym for 'Benevolent':",
        "question_text_hi": "'Benevolent' के लिए सही विलोम शब्द चुनें:",
        "options_en": ["Kind", "Generous", "Malevolent", "Charitable"],
        "options_hi": ["दयालु", "उदार", "दुर्भावनापूर्ण", "दानशील"],
        "correct_answer": 2,
        "explanation_en": "Benevolent means kind and generous, so malevolent (evil) is its antonym",
        "explanation_hi": "Benevolent का अर्थ दयालु और उदार है, इसलिए malevolent (दुर्भावनापूर्ण) इसका विलोम है",
        "exam_type": "State PSC"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Which state is known as the 'Land of Five Rivers'?",
        "question_text_hi": "किस राज्य को 'पांच नदियों की भूमि' कहा जाता है?",
        "options_en": ["Punjab", "Haryana", "Uttar Pradesh", "Rajasthan"],
        "options_hi": ["पंजाब", "हरियाणा", "उत्तर प्रदेश", "राजस्थान"],
        "correct_answer": 0,
        "explanation_en": "Punjab means 'five waters' - the land of five rivers",
        "explanation_hi": "पंजाब का अर्थ 'पांच पानी' है - पांच नदियों की भूमि",
        "exam_type": "State PSC"
    },
    {
        "subject": "quantitative",
        "difficulty": "advanced",
        "question_text_en": "A rectangular field is 40m long and 30m wide. A path 2m wide runs around it. Find the area of the path.",
        "question_text_hi": "एक आयताकार मैदान 40m लंबा और 30m चौड़ा है। इसके चारों ओर 2m चौड़ा रास्ता है। रास्ते का क्षेत्रफल ज्ञात करें।",
        "options_en": ["296 sq m", "300 sq m", "304 sq m", "308 sq m"],
        "options_hi": ["296 वर्ग मी", "300 वर्ग मी", "304 वर्ग मी", "308 वर्ग मी"],
        "correct_answer": 0,
        "explanation_en": "Outer area = 44×34 = 1496, Inner area = 40×30 = 1200, Path area = 1496-1200 = 296",
        "explanation_hi": "बाहरी क्षेत्र = 44×34 = 1496, आंतरिक क्षेत्र = 40×30 = 1200, रास्ते का क्षेत्र = 296",
        "exam_type": "State PSC"
    },
    
    # Railway Questions
    {
        "subject": "quantitative",
        "difficulty": "intermediate",
        "question_text_en": "A train covers 120 km in 2 hours. What is its speed in m/s?",
        "question_text_hi": "एक ट्रेन 2 घंटे में 120 किमी की दूरी तय करती है। m/s में इसकी गति क्या है?",
        "options_en": ["16.67 m/s", "20 m/s", "25 m/s", "30 m/s"],
        "options_hi": ["16.67 m/s", "20 m/s", "25 m/s", "30 m/s"],
        "correct_answer": 0,
        "explanation_en": "Speed = 120/2 = 60 km/h = 60×1000/3600 = 16.67 m/s",
        "explanation_hi": "गति = 120/2 = 60 km/h = 60×1000/3600 = 16.67 m/s",
        "exam_type": "Railway"
    },
    {
        "subject": "reasoning",
        "difficulty": "intermediate",
        "question_text_en": "If 'TRAIN' is coded as 'USBIJ', then 'PLANE' will be coded as:",
        "question_text_hi": "यदि 'TRAIN' को 'USBIJ' के रूप में कोड किया जाता है, तो 'PLANE' को कैसे कोड किया जाएगा:",
        "options_en": ["QMBOF", "QNBOF", "QMBOG", "QNBOF"],
        "options_hi": ["QMBOF", "QNBOF", "QMBOG", "QNBOF"],
        "correct_answer": 0,
        "explanation_en": "Each letter is moved one position forward in the alphabet",
        "explanation_hi": "प्रत्येक अक्षर वर्णमाला में एक स्थान आगे बढ़ाया जाता है",
        "exam_type": "Railway"
    },
    {
        "subject": "english",
        "difficulty": "intermediate",
        "question_text_en": "Choose the correct meaning of 'Punctual':",
        "question_text_hi": "'Punctual' का सही अर्थ चुनें:",
        "options_en": ["Late", "On time", "Early", "Delayed"],
        "options_hi": ["देर से", "समय पर", "जल्दी", "विलंबित"],
        "correct_answer": 1,
        "explanation_en": "Punctual means being on time or prompt",
        "explanation_hi": "Punctual का अर्थ समय पर या तुरंत होना है",
        "exam_type": "Railway"
    },
    {
        "subject": "general_knowledge",
        "difficulty": "intermediate",
        "question_text_en": "Which is the longest railway platform in India?",
        "question_text_hi": "भारत में सबसे लंबा रेलवे प्लेटफॉर्म कौन सा है?",
        "options_en": ["Gorakhpur", "Kollam", "Kharagpur", "Bhubaneswar"],
        "options_hi": ["गोरखपुर", "कोल्लम", "खड़गपुर", "भुवनेश्वर"],
        "correct_answer": 0,
        "explanation_en": "Gorakhpur Junction has the longest railway platform in India (1,366.33 m)",
        "explanation_hi": "गोरखपुर जंक्शन में भारत का सबसे लंबा रेलवे प्लेटफॉर्म है (1,366.33 m)",
        "exam_type": "Railway"
    },
    {
        "subject": "quantitative",
        "difficulty": "advanced",
        "question_text_en": "Two trains start from stations A and B towards each other. Train from A travels at 60 km/h and from B at 40 km/h. If they meet after 2 hours, find the distance between A and B.",
        "question_text_hi": "दो ट्रेनें स्टेशन A और B से एक-दूसरे की ओर चलती हैं। A से ट्रेन 60 km/h और B से 40 km/h की गति से चलती है। यदि वे 2 घंटे बाद मिलती हैं, तो A और B के बीच की दूरी ज्ञात करें।",
        "options_en": ["200 km", "220 km", "240 km", "260 km"],
        "options_hi": ["200 km", "220 km", "240 km", "260 km"],
        "correct_answer": 0,
        "explanation_en": "Relative speed = 60+40 = 100 km/h, Distance = 100×2 = 200 km",
        "explanation_hi": "सापेक्ष गति = 60+40 = 100 km/h, दूरी = 100×2 = 200 km",
        "exam_type": "Railway"
    }
]

# Helper functions
async def get_openai_response(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Get response from OpenAI API"""
    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are an expert tutor for Indian competitive exams (SSC, Banking, State PSC). Provide accurate, helpful explanations in both English and Hindi."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return "I apologize, but I'm having trouble generating a response right now. Please try again."

async def generate_adaptive_question(subject: str, difficulty: str, user_performance: Dict) -> Dict:
    """Generate adaptive questions using OpenAI based on user performance"""
    prompt = f"""
    Generate a {difficulty} level {subject} question for Indian competitive exams (SSC, Banking, State PSC).
    
    User Performance Context: {user_performance}
    
    Please provide the response in the following JSON format:
    {{
        "question_text_en": "Question in English",
        "question_text_hi": "प्रश्न हिंदी में",
        "options_en": ["Option 1", "Option 2", "Option 3", "Option 4"],
        "options_hi": ["विकल्प 1", "विकल्प 2", "विकल्प 3", "विकल्प 4"],
        "correct_answer": 0,
        "explanation_en": "Detailed explanation in English",
        "explanation_hi": "हिंदी में विस्तृत व्याख्या"
    }}
    
    Make sure the question is relevant to {subject} and appropriate for Tier-2/3 city exam aspirants.
    """
    
    try:
        response = await get_openai_response(prompt)
        # Try to parse JSON from response
        question_data = json.loads(response)
        return question_data
    except:
        # Fallback to sample questions if OpenAI fails
        matching_questions = [q for q in SAMPLE_QUESTIONS if q["subject"] == subject and q["difficulty"] == difficulty]
        return random.choice(matching_questions) if matching_questions else SAMPLE_QUESTIONS[0]

# API Endpoints
@api_router.post("/users", response_model=User)
async def create_user(user_data: UserCreate):
    """Create a new user profile or return existing user"""
    # Check if user already exists by phone number
    existing_user = await db.users.find_one({"phone": user_data.phone})
    if existing_user:
        return User(**existing_user)
    
    # Create new user only if doesn't exist
    user = User(**user_data.dict())
    await db.users.insert_one(user.dict())
    return user

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user profile"""
    user_data = await db.users.find_one({"id": user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user_data)

@api_router.post("/diagnostic-test")
async def start_diagnostic_test(user_id: str):
    """Start a diagnostic assessment with 10 questions across all subjects"""
    # Get 2-3 questions from each subject with variety
    subjects = ["quantitative", "reasoning", "english", "general_knowledge"]
    questions = []
    used_questions = set()  # Track used questions to avoid duplicates
    
    for subject in subjects:
        # Get all questions for this subject
        subject_questions = [q for q in SAMPLE_QUESTIONS if q["subject"] == subject]
        # Sample 2-3 questions per subject without replacement
        available_questions = [q for q in subject_questions if id(q) not in used_questions]
        selected = random.sample(available_questions, min(3, len(available_questions)))
        questions.extend(selected)
        # Track used questions
        for q in selected:
            used_questions.add(id(q))
    
    # If we need more questions to reach 10, add remaining unique questions
    while len(questions) < 10:
        remaining_questions = [q for q in SAMPLE_QUESTIONS if id(q) not in used_questions]
        if remaining_questions:
            selected = random.choice(remaining_questions)
            questions.append(selected)
            used_questions.add(id(selected))
        else:
            break  # No more unique questions available
    
    # Shuffle the final question order
    random.shuffle(questions)
    
    # Create assessment
    assessment = Assessment(
        user_id=user_id,
        test_type="diagnostic",
        questions=[str(uuid.uuid4()) for _ in questions]  # Generate question IDs
    )
    
    # Store questions with assessment
    question_objects = []
    for i, q_data in enumerate(questions):
        # Create a copy of q_data and update the subject and difficulty to proper enums
        question_data = q_data.copy()
        question_data["subject"] = SubjectType(q_data["subject"])
        question_data["difficulty"] = DifficultyLevel(q_data["difficulty"])
        
        question = Question(
            id=assessment.questions[i],
            **question_data
        )
        question_objects.append(question.dict())
    
    await db.questions.insert_many(question_objects)
    await db.assessments.insert_one(assessment.dict())
    
    # Return serializable data
    return {
        "assessment_id": assessment.id,
        "questions": [
            {
                "id": q["id"],
                "subject": q["subject"],
                "difficulty": q["difficulty"],
                "question_text_en": q["question_text_en"],
                "question_text_hi": q["question_text_hi"],
                "options_en": q["options_en"],
                "options_hi": q["options_hi"],
                "exam_type": q["exam_type"]
            } for q in question_objects
        ],
        "total_questions": len(questions)
    }

@api_router.post("/submit-answer")
async def submit_answer(answer_data: SubmitAnswerRequest):
    """Submit answer for a question in assessment"""
    # Get assessment
    assessment_data = await db.assessments.find_one({"id": answer_data.assessment_id})
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Get question
    question_data = await db.questions.find_one({"id": answer_data.question_id})
    if not question_data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Check if answer is correct
    is_correct = answer_data.selected_option == question_data["correct_answer"]
    
    # Create answer object
    answer = Answer(
        question_id=answer_data.question_id,
        selected_option=answer_data.selected_option,
        is_correct=is_correct,
        time_taken=answer_data.time_taken
    )
    
    # Update assessment
    assessment = Assessment(**assessment_data)
    assessment.answers.append(answer)
    
    # Update in database
    await db.assessments.update_one(
        {"id": answer_data.assessment_id},
        {"$set": {"answers": [a.dict() for a in assessment.answers]}}
    )
    
    return {
        "is_correct": is_correct,
        "correct_answer": question_data["correct_answer"],
        "explanation": {
            "english": question_data["explanation_en"],
            "hindi": question_data["explanation_hi"]
        }
    }

@api_router.post("/complete-assessment")
async def complete_assessment(assessment_id: str):
    """Complete assessment and calculate scores"""
    assessment_data = await db.assessments.find_one({"id": assessment_id})
    if not assessment_data:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    assessment = Assessment(**assessment_data)
    
    # Calculate overall score
    total_questions = len(assessment.answers)
    correct_answers = sum(1 for a in assessment.answers if a.is_correct)
    overall_score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
    
    # Calculate subject-wise scores
    subject_scores = {}
    for answer in assessment.answers:
        question_data = await db.questions.find_one({"id": answer.question_id})
        if question_data:
            subject = question_data["subject"]
            if subject not in subject_scores:
                subject_scores[subject] = {"correct": 0, "total": 0}
            subject_scores[subject]["total"] += 1
            if answer.is_correct:
                subject_scores[subject]["correct"] += 1
    
    # Convert to percentages
    for subject in subject_scores:
        total = subject_scores[subject]["total"]
        correct = subject_scores[subject]["correct"]
        subject_scores[subject] = (correct / total) * 100 if total > 0 else 0
    
    # Update assessment
    assessment.score = overall_score
    assessment.subject_scores = subject_scores
    assessment.completed_at = datetime.now(timezone.utc)
    
    await db.assessments.update_one(
        {"id": assessment_id},
        {"$set": {
            "score": overall_score,
            "subject_scores": subject_scores,
            "completed_at": assessment.completed_at.isoformat()
        }}
    )
    
    # Update user skill levels based on performance
    user_data = await db.users.find_one({"id": assessment.user_id})
    if user_data:
        skill_levels = {}
        for subject, score in subject_scores.items():
            if score >= 80:
                skill_levels[subject] = "advanced"
            elif score >= 50:
                skill_levels[subject] = "intermediate"
            else:
                skill_levels[subject] = "beginner"
        
        await db.users.update_one(
            {"id": assessment.user_id},
            {"$set": {"skill_levels": skill_levels}}
        )
    
    return {
        "overall_score": overall_score,
        "subject_scores": subject_scores,
        "skill_levels": skill_levels,
        "total_questions": total_questions,
        "correct_answers": correct_answers
    }

@api_router.get("/adaptive-practice")
async def get_adaptive_practice(user_id: str, count: int = 5):
    """Get adaptive practice questions based on user's performance"""
    try:
        # Get user data
        user_data = await db.users.find_one({"id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user = User(**user_data)
        
        # Get recent performance
        recent_assessments = await db.assessments.find(
            {"user_id": user_id, "completed_at": {"$ne": None}}
        ).sort("completed_at", -1).limit(5).to_list(None)
        
        # Convert ObjectId to string for JSON serialization
        for assessment in recent_assessments:
            if "_id" in assessment:
                assessment["_id"] = str(assessment["_id"])
        
        # Create assessment for adaptive practice
        assessment = Assessment(
            id=str(uuid.uuid4()),
            user_id=user_id,
            assessment_type="adaptive_practice",
            test_type=user.target_exam,  # Use user's target exam
            questions=[],
            answers=[],
            score=0,
            status="in_progress"
        )
        await db.assessments.insert_one(assessment.dict())
        
        # Generate adaptive questions
        questions = []
        used_questions = set()  # Track used questions to avoid duplicates
    
        for _ in range(count):
            # Select subject based on weakest areas
            weakest_subjects = []
            if user.skill_levels:
                for subject, level in user.skill_levels.items():
                    if level == "beginner":
                        weakest_subjects.extend([subject] * 3)  # Higher weight
                    elif level == "intermediate":
                        weakest_subjects.extend([subject] * 2)
                    else:
                        weakest_subjects.append(subject)
            
            if not weakest_subjects:
                weakest_subjects = ["quantitative", "reasoning", "english", "general_knowledge"]
            
            selected_subject = random.choice(weakest_subjects)
            difficulty = user.skill_levels.get(selected_subject, "beginner")
        
            # Try to generate with OpenAI, fallback to sample questions
            try:
                question_data = await generate_adaptive_question(
                    selected_subject, 
                    difficulty, 
                    {"recent_performance": user.skill_levels}
                )
                
                question = Question(
                    subject=selected_subject,
                    difficulty=difficulty,
                    question_text_en=question_data["question_text_en"],
                    question_text_hi=question_data["question_text_hi"],
                    options_en=question_data["options_en"],
                    options_hi=question_data["options_hi"],
                    correct_answer=question_data["correct_answer"],
                    explanation_en=question_data["explanation_en"],
                    explanation_hi=question_data["explanation_hi"],
                    exam_type=user.target_exam
                )
                questions.append(question.dict())
                await db.questions.insert_one(question.dict())
                
            except Exception as e:
                logging.error(f"Error generating adaptive question: {e}")
                # Fallback to mock adaptive questions - avoid duplicates
                available_questions = [q for q in MOCK_ADAPTIVE_QUESTIONS if q["question_text_en"] not in used_questions]
                if not available_questions:
                    available_questions = MOCK_ADAPTIVE_QUESTIONS  # Reset if all used
                    used_questions.clear()
                
                mock_question = random.choice(available_questions)
                used_questions.add(mock_question["question_text_en"])
                
                question = Question(
                    id=str(uuid.uuid4()),
                    subject=mock_question["subject"],
                    difficulty=mock_question["difficulty"],
                    question_text_en=mock_question["question_text_en"],
                    question_text_hi=mock_question["question_text_hi"],
                    options_en=mock_question["options_en"],
                    options_hi=mock_question["options_hi"],
                    correct_answer=mock_question["correct_answer"],
                    explanation_en=mock_question["explanation_en"],
                    explanation_hi=mock_question["explanation_hi"],
                    exam_type=mock_question["exam_type"]
                )
                questions.append(question.dict())
                await db.questions.insert_one(question.dict())
    
        return {"questions": questions, "assessment_id": assessment.id}
    except Exception as e:
        logging.error(f"Error in adaptive practice: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@api_router.post("/ai-feedback")
async def get_ai_feedback(feedback_request: FeedbackRequest):
    """Get AI-powered feedback for wrong answers"""
    question_data = await db.questions.find_one({"id": feedback_request.question_id})
    if not question_data:
        raise HTTPException(status_code=404, detail="Question not found")
    
    # Generate personalized feedback using OpenAI
    prompt = f"""
    A student answered incorrectly on this competitive exam question:
    
    Question: {question_data['question_text_en']}
    Options: {question_data['options_en']}
    Correct Answer: {question_data['options_en'][question_data['correct_answer']]}
    Student's Answer: {question_data['options_en'][feedback_request.user_answer]}
    
    Provide encouraging, personalized feedback that:
    1. Explains why the student's answer was incorrect
    2. Explains the correct approach step-by-step
    3. Gives tips to avoid similar mistakes
    4. Provides additional practice suggestions
    
    Keep it concise but helpful for Indian competitive exam aspirants.
    Language: {"Hindi" if feedback_request.language == Language.HINDI else "English"}
    """
    
    ai_feedback = await get_openai_response(prompt)
    
    return {
        "feedback": ai_feedback,
        "correct_explanation": question_data[f"explanation_{feedback_request.language.value[:2]}"],
        "study_tips": "Focus on similar question patterns and practice daily for better retention."
    }

@api_router.get("/study-plan/{user_id}")
async def get_daily_study_plan(user_id: str):
    """Generate daily 20-minute study plan"""
    user_data = await db.users.find_one({"id": user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = User(**user_data)
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Check if plan already exists for today
    existing_plan = await db.study_plans.find_one({"user_id": user_id, "date": today})
    if existing_plan:
        return StudyPlan(**existing_plan)
    
    # Generate new study plan based on weak areas or use mock data
    weak_subjects = []
    if user.skill_levels:
        for subject, level in user.skill_levels.items():
            if level == "beginner":
                weak_subjects.extend([subject] * 2)  # Focus more on weak areas
            elif level == "intermediate":
                weak_subjects.append(subject)
    
    if not weak_subjects:
        # Use mock study plan when no skill levels available
        mock_plan = random.choice(MOCK_STUDY_PLANS)
        weak_subjects = mock_plan["subjects"]
    
    # Create daily plan
    plan = StudyPlan(
        user_id=user_id,
        date=today,
        subjects=list(set(weak_subjects[:3])),  # Max 3 subjects per day
        questions_count=20,
        estimated_time=20
    )
    
    await db.study_plans.insert_one(plan.dict())
    return plan

@api_router.get("/assessments/{user_id}")
async def get_user_assessments(user_id: str):
    """Get all assessments for a user"""
    assessments = await db.assessments.find(
        {"user_id": user_id}
    ).sort("created_at", -1).to_list(None)
    
    # Convert ObjectId to string for JSON serialization
    for assessment in assessments:
        if "_id" in assessment:
            assessment["_id"] = str(assessment["_id"])
    
    return {"assessments": assessments}

@api_router.get("/progress/{user_id}")
async def get_user_progress(user_id: str):
    """Get user's learning progress and analytics"""
    # Get user data
    user_data = await db.users.find_one({"id": user_id})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all completed assessments
    assessments = await db.assessments.find(
        {"user_id": user_id, "completed_at": {"$ne": None}}
    ).sort("completed_at", 1).to_list(None)
    
    # Convert ObjectId to string for JSON serialization
    for assessment in assessments:
        if "_id" in assessment:
            assessment["_id"] = str(assessment["_id"])
    
    # Calculate progress metrics
    total_assessments = len(assessments)
    avg_score = sum(a["score"] for a in assessments) / total_assessments if total_assessments > 0 else 0
    
    # Get recent 7 days performance
    recent_scores = [a["score"] for a in assessments[-7:]] if assessments else []
    
    # Calculate improvement trend
    improvement_trend = 0
    if len(recent_scores) >= 2:
        improvement_trend = recent_scores[-1] - recent_scores[0]
    
    return {
        "total_tests_taken": total_assessments,
        "average_score": round(avg_score, 2),
        "recent_scores": recent_scores,
        "improvement_trend": round(improvement_trend, 2),
        "skill_levels": user_data.get("skill_levels", {}),
        "strong_subjects": [s for s, l in user_data.get("skill_levels", {}).items() if l == "advanced"],
        "weak_subjects": [s for s, l in user_data.get("skill_levels", {}).items() if l == "beginner"]
    }

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Pathshala Coach API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()