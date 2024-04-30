from dotenv import load_dotenv
import os
import time
import logging
import json
import requests
from PyPDF2 import PdfReader
import docx  
# from pathlib import Path


# from ai_image.ai_image import generate_image, image_gen_model   
from app.services.openai_service import generate_response
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI

def get_text_message_input(recipient, text):
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )

def send_message(data):
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}",
    }

    url = f"https://graph.facebook.com/{os.getenv('VERSION')}/{os.getenv('PHONE_NUMBER_ID')}/messages"

    try:
        response = requests.post(
            url, data=data, headers=headers, timeout=10
        )
        response.raise_for_status()
    except requests.Timeout:
        logging.error("Timeout occurred while sending message")
        return {"status": "error", "message": "Request timed out"}, 408
    except requests.RequestException as e:
        logging.error(f"Request failed due to: {e}")
        return {"status": "error", "message": "Failed to send message"}, 500
    else:
        logging.info("Message sent successfully")
        return {"status": "success", "message": "Message sent successfully"}, 200
    


def process_whatsapp_message(body):
    wa_id = body["entry"][0]["changes"][0]["value"]["contacts"][0]["wa_id"]
    message = body["entry"][0]["changes"][0]["value"]["messages"][0]

    # if "audio" in message:
    #     logging.info("Audio message received")
    #     # Handle audio message
    #     audio_message = message["audio"]
    #     audio_content = audio_message.get("content", None)

    #     if audio_content:
    #         # Decode base64 audio data
    #         audio_data = base64.b64decode(audio_content)
    #         recognized_text = recognize_audio(audio_data)
    #         if recognized_text:
    #             response = f"Recognized text from audio: {recognized_text}"
    #         else:
    #             response = "Failed to recognize speech from audio"
    #     else:
    #         logging.error("Audio content not found in the message.")
    #         response = {"status": "error", "message": "Audio content not found in the message."}
    # else:
    #   if "generate image" in message_body.lower():
    #     logging.info("Generate image request received")
    #     # Extract search query from the remaining text after "generate image"
    #     search_query = message_body.lower().replace("generate image", "").strip()

    #     try:
    #       # Call function to generate image (handle potential exceptions)
    #       generated_image = generate_image(search_query, image_gen_model)
    #       if generated_image:
    #         # Save the generated image with a unique filename
    #         import time
    #         timestamp = int(time.time())
    #         image_path = Path(f"generated_image_{timestamp}.png")
    #         generated_image.save(image_path)
    #         response = f"Here is the generated image: {image_path}"
    #       else:
    #         response = "Failed to generate the image."
    #     except Exception as e:
    #       logging.error(f"Error generating image: {e}")
    #       response = "An error occurred while generating the image."
    #   else:
    #     response = "No 'generate image' request found in the message."
    message_body = message["text"]["body"]
    if "news" in message_body.lower() and "fake news" not in message_body.lower():
        logging.info("News keyword found in text")
        keyword = message_body
        news_data = scrape_news(keyword)
        time.sleep(2)
        response = f"Here are the latest news articles related to '{keyword}':\n\n{news_data}"

    elif "climate" in message_body.lower():
        words = message_body.lower().split()
        index = words.index("climate") - 1
        if index >= 0:
            user_input = words[index]
            response = process_weather_report(user_input)  # Call function to process weather report
        else:
            response = "Please provide a location for the weather report."

    else:
        logging.info("No relevant keyword found in text")
        response = generate_response(message_body, wa_id)

    data = get_text_message_input(wa_id, response)
    return send_message(data)

def is_valid_whatsapp_message(body):
    return (
        body.get("object")
        and body.get("entry")
        and body["entry"][0].get("changes")
        and body["entry"][0]["changes"][0].get("value")
        and body["entry"][0]["changes"][0]["value"].get("messages")
        # and body["entry"][0]["changes"][0]["value"]["messages"][0]
    )

##################### Read files from documents #####################

load_dotenv()

# reads different file formats
def read_pdf(file_path):
    with open(file_path, "rb") as file:
        pdf_reader = PdfReader(file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text()
    return text

def read_word(file_path):
    doc = docx.Document(file_path)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def read_txt(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()
    return text

def read_documents_from_directory(directory):
    combined_text = ""
    for filename in os.listdir(directory):  
        file_path = os.path.join(directory, filename)
        if filename.endswith(".pdf"):
            combined_text += read_pdf(file_path)
        elif filename.endswith(".docx"):
            combined_text += read_word(file_path)
        elif filename.endswith(".txt"):
            combined_text += read_txt(file_path)
    return combined_text

train_directory = r'C:\Users\Cyril T Johnson\Desktop\fake news decition\Python_Whatsapp_bot\chat_bot_documents'
text = read_documents_from_directory(train_directory)

char_text_splitter = CharacterTextSplitter(separator="\n", chunk_size=1000, 
                                      chunk_overlap=200, length_function=len)

text_chunks = char_text_splitter.split_text(text)
  
embeddings = OpenAIEmbeddings()
docsearch = FAISS.from_texts(text_chunks, embeddings)

llm = OpenAI()
chain = load_qa_chain(llm, chain_type="stuff")


##################### Google news scraping #####################

from GoogleNews import GoogleNews
import logging

def scrape_news(keyword):
    logging.info(f"Scraping news for keyword: {keyword}")
    
    googlenews = GoogleNews(lang='en', region='IN', period='1d', encode='utf-8')
    googlenews.clear()
    googlenews.search(keyword)
    news_result = googlenews.result(sort=True)
    
    news_data = ""
    for news_item in news_result:
        news_data += f"Title: {news_item['title']}\n"
        news_data += f"Description: {news_item['desc']}\n"
        news_data += f"Link: {news_item['link']}\n\n"
    
    logging.info("News data scraped successfully")
    return news_data


##################### Weather Report #####################


def process_weather_report(user_input):
    api_key = 'f8039a9dc1afe11fc83f8a2b448dbf6f'
    weather_data = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={user_input}&units=metric&APPID={api_key}")

    if weather_data.status_code == 404:
        return "City Not Found"
    else:
        try:
            weather = weather_data.json()['weather'][0]['main']
            temp = round(weather_data.json()['main']['temp'])
            return f"The weather in {user_input} is {weather}\n" \
                   f"The temperature in {user_input} is {temp}°C"
        except KeyError:
            return "Error: Failed to retrieve weather information. Please check your input or try again later."




