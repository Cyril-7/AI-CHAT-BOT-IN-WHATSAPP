from openai import OpenAI
import shelve
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
client = OpenAI(api_key=OPENAI_API_KEY)

# def upload_files(folder_path):
#     files = os.listdir(folder_path)
#     uploaded_file_paths = []
#     for file_name in files:
#         file_path = os.path.join(folder_path, file_name)
#         with open(file_path, "rb") as file:
#             uploaded_file = client.files.create(
#                 file=file,
#                 purpose="assistants"
#             )
#             uploaded_file_paths.append(file_path)
#     return uploaded_file_paths


# def create_assistant(file_path):
#     with open(file_path, "rb") as file:
#         file_content = file.read()

#     assistant = client.beta.assistants.create(
#         name="Fake News",
#         instructions="Your assistant instructions here.",
#         tools=[{"type": "function", "function": {"name": "default"}}],  # Provide a function for the assistant
#         model="gpt-3.5-turbo-0125",
#     )

#     # Associate the file content with the assistant
#     document = client.files.create(file=file_content, purpose="assistants")
#     assistant.add_document(document.id)

#     return assistant


def check_if_thread_exists(wa_id):
    with shelve.open("threads_db") as threads_shelf:
        return threads_shelf.get(wa_id, None)

def store_thread(wa_id, thread_id):
    with shelve.open("threads_db", writeback=True) as threads_shelf:
        threads_shelf[wa_id] = thread_id


def run_assistant(thread, name):
    assistant = client.beta.assistants.retrieve(OPENAI_ASSISTANT_ID)
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )
    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    new_message = messages.data[0].content[0].text.value
    logging.info(f"Generated message: {new_message}")
    return new_message

def generate_response(message_body, wa_id):
    thread_id = check_if_thread_exists(wa_id)
    if thread_id is None:
        logging.info(f"Creating new thread for user with wa_id {wa_id}")
        thread = client.beta.threads.create()
        store_thread(wa_id, thread.id)
        thread_id = thread.id
    else:
        logging.info(f"Retrieving existing thread for user with wa_id {wa_id}")
        thread = client.beta.threads.retrieve(thread_id)
        message = client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message_body,
    )

    new_message = run_assistant(thread, "User")
    return new_message


# # Usage:
# folder_path = "chat_bot_documents"
# uploaded_files = upload_files(folder_path)
# assistant_file_path = uploaded_files[0]
# assistant = create_assistant(assistant_file_path)




