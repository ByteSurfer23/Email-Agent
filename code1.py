import os 
import json 
from typing import TypedDict
from dotenv import load_dotenv
from imap_tools import MailBox , AND
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph,START,END
import streamlit as st
from tools.blood_test.bt_ingest import process_uploaded_pdf

load_dotenv()
IMAP_HOST = os.getenv('IMAP_HOST')
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD')
IMAP_FOLDER = 'INBOX'

CHAT_MODEL='qwen3:8b'


class ChatState(TypedDict):
    messages:list


uploaded_file = st.file_uploader("Upload Health Report (PDF)", type=["pdf"])

if uploaded_file:

    with st.spinner("Parsing PDF..."):
        success, message, data = process_uploaded_pdf(uploaded_file)

    if success:
        st.success(message)
        st.subheader("Extracted JSON")
        st.json(data)
    else:
        st.error(message)

def connect():
    mail_box = MailBox(IMAP_HOST)
    mail_box.login(IMAP_USER,IMAP_PASSWORD,initial_folder=IMAP_FOLDER)
    return mail_box





@tool
def list_unread_emails():
    """
    Return a bullet list of every UNREAD message's UID , subject , date and sender
    """
    print('List Unread Emails Tools Called')
    with connect() as mb:
        unread = list(mb.fetch(criteria=AND(seen=False), headers_only=True , mark_seen=False))
        if not unread : 
            return "You have no unread messages"
    response = json.dumps([
        {
            'uid':mail.uid,
            'date':mail.date.astimezone().strftime('%Y-%m-%d %H:%M'),
            'subject':mail.subject,
            'sender':mail.from_
        } for mail in unread[:10]
    ])
    print(response)
    return response





@tool
def summarize_email(uid):
    """
    Summarize a single e-mail given its IMAP UID . Return a short summary of the e-mails content / body in plain text
    """
    print('Summarize Email Tool Called on',uid)
    with connect() as mb: 
        mail = next(mb.fetch(AND(uid=uid), mark_seen=False),None)
        if not mail : 
            return f'Could not summarize email with UID{uid}'

        propmt = (
            "Summarize this e-mail concisely:\n\n"
            f"Subject:{mail.subject}\n"
            f"Sender:{mail.from_}\n"
            f"Date:{mail.date}\n\n"
            f"{mail.text or mail.html}"
        )
        #Feed this prompt into llm and obtain results 
        print(response)
        return raw_llm.invoke(prompt).content

llm = init_chat_model(CHAT_MODEL,model_provider='ollama',temperature=0)
llm = llm.bind_tools([list_unread_emails,summarize_email])
raw_llm = init_chat_model(CHAT_MODEL,model_provider='ollama',temperature=0)

def llm_node(state):
    system_prompt = SystemMessage(content=(
        "You are a strict Email Assistant. "
        "DECISION RULE: If the user is just greeting you (hi, hello, etc.), "
        "respond with text ONLY. "
        "DO NOT use tools unless the user specifically asks to 'list', 'show', "
        "or 'summarize' an email. "
        "Be concise."
    ))
    response = llm.invoke(state['messages'])#AImessage object is the response 
    return {
        'messages':state['messages']+[response]
    }

def router(state):
    last_message = state['messages'][-1]
    return 'tools' if getattr(last_message,'tool_calls',None) else 'end'
    #if statement gets the attribute of last_message object , and the attribute is called tool_calls , if no attribute returns none as the fall back value
    # if no attr then it returns end to complete the graph


tool_node = ToolNode([list_unread_emails , summarize_email])#tool node has the tools bound to it 

def tools_node(state):
    result = tool_node.invoke(state)#result of the tool
    return {
        'messages':state['messages']+result['messages']
    }
builder = StateGraph(ChatState)
builder.add_node('llm',llm_node)
builder.add_node('tools',tools_node)
builder.add_edge(START,'llm')
builder.add_edge('tools','llm')
builder.add_conditional_edges('llm',router,{'tools':'tools', "end":END})
# here we say if the router returns tools string then go to tools node 
# if it returns end string then go to end node

graph = builder.compile()



def main():
    print("Hello from agentic-ai!")


if __name__ == "__main__":
    state = {'messages':[]}
    print('Type an instruction \n')

    while True:
        user_message = input('>')
        if user_message.lower() =='quit':
            break
        state['messages'].append({'role':'user', 'content':user_message})
        state=graph.invoke(state)
        print(state['messages'][-1].content,'\n')

# chat state is class which defines the kind of data which will be present in the state 
# state is nothing but a list called messages 
# each message in the message contains query and response 
# and each message will also contain the tool used to generate it , this happens as you bind the llm with the tools in line 77 
# when llm.invoke(state) (line 86) is used a message called AImessage is generated and this contains the tool_calls attribute 
# AImessage contains tool_calls attribute which has name , id etc 
# and that ai message is added to the state as the most recent one 
# if the tool_calls is empty for that message we go to end state 
# if there is tool_calls present then we go to the tools node which has the tools that must be called bound to the node and this node can use the tools 
# and that generates another message which is appended to the state of messages
# it is called tool_message which has content , name of the tool called , tool_call_id which must match the id in the AImessage id 
# this one is a recursive graph where the llm is called 2 times