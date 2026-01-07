nutrimama/
│
├── README.md
├── requirements.txt
├── .env
│
├── app/
│   ├── main.py
│   │
│   ├── core/               # brain core (no ML, no LLM)
│   │   ├── __init__.py
│   │   ├── state.py        # maternal brain state
│   │   ├── memory.py       # memory (short + long)
│   │   ├── reasoning.py    # decides what to do
│   │   └── safety.py       # hard boundaries
│   │
│   ├── perception/         # understanding user input
│   │   ├── __init__.py
│   │   └── nlp.py
│   │
│   ├── learning/           # learning from outcomes
│   │   ├── __init__.py
│   │   └── adaptation.py
│   │
│   ├── models/             # ML models (CatBoost etc.)
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   └── predictors.py
│   │
│   ├── knowledge/          # nutrition facts (RAG later)
│   │   ├── __init__.py
│   │   └── nutrition.py
│   │
│   └── interface/          # LLM, voice, UI later
│       ├── __init__.py
│       └── responder.py
│
└── data/
    ├── raw/
    ├── processed/
    └── user_states/
