from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from typing import Annotated, TypedDict, Literal
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from dotenv import load_dotenv
import os
import asyncio
import uvicorn


# initialize environment variables
_ = load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")


class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def search(query: str):
    """Call to search the web."""
    # this is a placeholder
    return ['Cloudy with a chance of hail.']
  
tools = [search]
tool_node = ToolNode(tools)

# set up the model
model = ChatOpenAI(temperature=0, streaming=True, model="gpt-4o")
model = model.bind_tools(tools)

# set of the langgraph nodes
def should_continue(state: State) -> Literal["__end__", "tools"]:
  messages = state['messages']
  last_message = messages[-1]
  # if there is no function call, then we are finished
  if not last_message.tool_calls:
    return END
  # if there is a tool, continue to tools
  else:
    return "tools"

# define the function that calls the model
async def call_model(state: State, config: RunnableConfig):
  messages = state['messages']
  response = await model.ainvoke(messages, config)
  # Wereturn a list, this will get added to the existing list
  return {'messages': response}


# define the graph
workflow = StateGraph(State)

# define the 2 nodes we will cycle between
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# set entry point as agent
workflow.set_entry_point("agent")

# set conditional edge
workflow.add_conditional_edges("agent", should_continue)

workflow.add_edge("tools", "agent")

# compile the graph
app = workflow.compile()

# app.get_graph().draw_mermaid_png(output_file_path="graph.png")

async def run_workflow():
  inputs = [HumanMessage(content="What is the weather in SF?")]
  async for event in app.astream_events({"messages": inputs}, version="v2"):
    kind = event["event"]
    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            # Empty content in the context of OpenAI or Anthropic usually means
            # that the model is asking for a tool to be invoked.
            # So we only print non-empty content
            # print(content, end="|")
            yield content
    elif kind == "on_tool_start":
        print("--")
        print(
            f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
        )
    elif kind == "on_tool_end":
        print(f"Done tool: {event['name']}")
        print(f"Tool output was: {event['data'].get('output')}")
        print("--")
        

server = FastAPI()

async def async_generator():
    for i in range(5):
        await asyncio.sleep(1)  # Simulate some async operation
        yield i

async def stream_results():
    async for item in run_workflow():
        processed_item = f"Processed item: {item}"
        print(processed_item)
        yield f"data: {processed_item}\n\n"
        # await asyncio.sleep(0.5)  # Simulate some processing time
    yield "data: [DONE]\n\n"

@server.get("/chat")
async def chat():
    return StreamingResponse(stream_results(), media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(server, host="0.0.0.0", port=8000)