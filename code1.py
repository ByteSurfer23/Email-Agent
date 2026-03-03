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


load_dotenv()
IMAP_HOST = os.getenv('IMAP_HOST')
IMAP_USER = os.getenv('IMAP_USER')
IMAP_PASSWORD = os.getenv('IMAP_PASSWORD')
IMAP_FOLDER = 'INBOX'

CHAT_MODEL='qwen3:8b'


class ChatState(TypedDict):
    messages:list

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
    response = llm.invoke(state['messages'])
    return {
        'messages':state['messages']+[response]
    }

def router(state):
    last_message = state['messages'][-1]
    return 'tools' if getattr(last_message,'tool_calls',None) else 'end'
    #if statement gets the attribute of last_message object , and the attribute is called tool_calls , if no attribute returns none as the fall back value
    # if no attr then it returns end to complete the graph


tool_node = ToolNode([list_unread_emails , summarize_email])

def tools_node(state):
    result = tool_node.invoke(state)
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