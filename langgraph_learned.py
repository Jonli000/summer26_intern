from typing import Annotated
import os
import dotenv
import json

from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_tavily import TavilySearch
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import ToolNode, tools_condition

from dotenv import load_dotenv
load_dotenv() #Load environment variables from .env file
os.environ["TAVILY_API_KEY"] = "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"

tool = TavilySearch(max_results=2)
tools = [tool]
tool.invoke("What is a 'node' of LangGraph?")

class State(TypedDict):
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

# 首先设置 LLM，然后再绑定工具
llm = ChatOpenAI(
    model_name=os.getenv("LLM_MODEL_ID","Qwen/Qwen2.5-14B-Instruct"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL"),
)
llm_with_tools = llm.bind_tools(tools)

class BasicToolNode:
    def __init__(self, tools : list) -> None:

        self.tools = {t.name: t for t in tools}
    
    def __call__(self, inputs: dict):
        if messages := inputs.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")
        outputs = []
        for tool_call in message.tool_calls:
            tool_result = self.tools[tool_call["name"]].invoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

tool_node = BasicToolNode(tools=[tool])

def chatbot(state : State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}
    
#Tge furst argument is the unique node name
#The second argument is the function or object that will be called whenever the node is used
graph_builder.add_node("tools", tool_node)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph = graph_builder.compile()

def route_tools(state : State):
    """
    Use the conditional_edge to route to the tools node if the user message has tool_calls.
    Otherwise, route to the end.
    """
    if isinstance(state, list):
        ai_message = state[-1]
    elif messages := state.get("messages", []):
        ai_message = messages[-1]
    else:
        raise ValueError(f"No message found in input state to tool_edge: {state}")
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return END


#The 'tools_condition' function returns "tools" if the chatbox asks to use a tool and 'END' otherwise.
#This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges("chatbot", tools_condition
)
graph_builder.add_edge("tools", "chatbot")
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


