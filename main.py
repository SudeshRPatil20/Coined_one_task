from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

# LangChain Imports (No agent modules needed)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from dotenv import load_dotenv
load_dotenv()
# ============================
# FASTAPI SETUP
# ============================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================
# DATA MODELS
# ============================

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class MortgageInputs(BaseModel):
    property_price: float
    down_payment: float
    tenure_years: int
    years_planned: int
    monthly_rent: Optional[float] = None
    monthly_income: Optional[float] = None


# ============================
# MORTGAGE MATH TOOLS
# ============================

def calculate_emi(principal: float, annual_rate: float, years: int) -> float:
    r = annual_rate / 12 / 100
    n = years * 12
    if r == 0:
        return principal / n
    emi = principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
    return round(emi, 2)


def compute_buy_vs_rent(data: MortgageInputs):
    result = {}

    # Minimum 20% down payment rule
    min_dp = 0.20 * data.property_price
    result["min_down_payment_required"] = min_dp
    result["is_down_payment_sufficient"] = data.down_payment >= min_dp

    loan_amount = data.property_price - data.down_payment
    result["loan_amount"] = loan_amount

    # EMI calculation with fixed 4.5% interest
    emi = calculate_emi(loan_amount, 4.5, data.tenure_years)
    result["emi"] = emi

    # Upfront costs (approx. 7% of property price)
    result["upfront_costs"] = 0.07 * data.property_price

    # Rent comparison
    if data.monthly_rent:
        result["total_rent_over_period"] = data.monthly_rent * 12 * data.years_planned

    # EMI-to-income affordability
    if data.monthly_income:
        result["emi_to_income_ratio"] = round(emi / data.monthly_income, 2)

    # Buy vs rent recommendation
    if data.years_planned < 3:
        result["recommendation"] = "rent"
    elif data.years_planned > 5:
        result["recommendation"] = "buy"
    else:
        result["recommendation"] = "depends"

    return result


# ============================
# LLM (Gemini)
# ============================

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    temperature=0,
    max_output_tokens=512,
    convert_system_message_to_human=True,
)


# ============================
# LOAD KNOWLEDGE BASE (RAG)
# ============================

def load_kb_text():
    kb_files = [
        "KB/mortgage_rules.txt",
        "KB/buy_vs_rent_heuristics.txt",
        "KB/uae_ltv_rules.txt",
        "KB/upfront_costs.txt"
    ]

    kb_text = ""
    for fpath in kb_files:
        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            full_path = os.path.join(base_path, fpath)

            with open(full_path, "r", encoding="utf-8") as f:
                kb_text += f.read() + "\n"
        except:
            pass
    return kb_text


def retrieve_relevant_facts(query):
    text = load_kb_text()
    lines = text.split("\n")

    q_words = query.lower().split()
    matched = [line for line in lines if any(w in line.lower() for w in q_words)]

    return "\n".join(matched) if matched else text


# ============================
# PROMPT
# ============================

SYSTEM_PROMPT = """
You are a UAE mortgage advisor.

RULES:
- Use the provided knowledge base ONLY.
- Never invent numbers.
- Never assume missing values.
- If EMI is needed, tell the user to call the /calculate API.
- Ask follow-up questions when needed.
- Keep answers simple and factual.

Knowledge Base:
{facts}

User Question:
{question}

Final Answer:
"""

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)


# ============================
# LLM CALL
# ============================

def call_llm(messages):
    user_query = messages[-1]["content"]
    facts = retrieve_relevant_facts(user_query)

    formatted_prompt = prompt.format(
        facts=facts,
        question=user_query
    )

    response = llm.invoke(formatted_prompt)
    return response.content


# ============================
# ROUTES
# ============================

@app.post("/chat")
def chat_api(request: ChatRequest):
    messages = [{"role": "system", "content": "UAE mortgage advisor"}]

    for m in request.messages:
        messages.append({"role": m.role, "content": m.content})

    reply = call_llm(messages)
    return {"reply": reply}


@app.post("/calculate")
def calculate_api(data: MortgageInputs):
    return compute_buy_vs_rent(data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)