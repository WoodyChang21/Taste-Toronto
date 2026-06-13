from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)

SYSTEM = """You are Taste Toronto — a warm local food guide for the Greater Toronto Area.
The user is making small talk or saying something off-topic.
Respond briefly and warmly, then invite them to describe what kind of restaurant they're after.
2 sentences max. No markdown."""


def chitchat_responder_node(state: dict) -> dict:
    ai_msg = _llm.invoke([
        SystemMessage(content=SYSTEM),
        HumanMessage(content=state["user_message"]),
    ])
    return {
        "response": ai_msg.content,
        "scored": [],
        "messages": [AIMessage(content=ai_msg.content)],
    }
