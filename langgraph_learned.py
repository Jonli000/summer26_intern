from typing import Annotated
import os
import dotenv

from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from dotenv import load_dotenv
load_dotenv() #Load environment variables from .env file
os.environ["TAVILY_API_KEY"] = "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"

from langchain_tavily import TavilySearch

tool = TavilySearch(max_results=2)
tools = [tool]
tool.invoke("What is a 'node' of LangGraph?")

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

    
graph_builder = StateGraph(State)

llm_with_tools = llm.bind_tools(tools)
    
# Set up the chat model
llm = ChatOpenAI(
model_name=os.getenv("LLM_MODEL_ID","Qwen/Qwen2.5-14B-Instruct"),
api_key=os.getenv("LLM_API_KEY"),
base_url=os.getenv("LLM_BASE_URL"),
)

def chatbot(state : State):
    return {"messages": [llm.invoke(state["messages"])]}

    
#Tge furst argument is the unique node name
#The second argument is the function or object that will be called whenever the node is used
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)

while True:
    try:
        user_input = input("User: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        stream_graph_updates(user_input)
    except:
        # fallback if input() is not available
        user_input = "What do you know about LangGraph?"
        print("User: " + user_input)
        stream_graph_updates(user_input)
        break


