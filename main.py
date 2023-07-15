import uuid
import pymongo as pym
from flask import Flask, request
from yake import KeywordExtractor
import re
from flask_cors import CORS
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
import os
# in file directory
from list_check import remove_elements, general_answer_dict

app = Flask(__name__)
cors = CORS(app, resources={r"/reply": {"origins": "*"}})
# logging
log_formatter = logging.Formatter("%(asctime)s -- %(levelname)s -- %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger() # root logger
# adding console hanlder to root logger
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)
# adding file handler to root logger
file_handler = RotatingFileHandler("logfile.log", backupCount=100, maxBytes=1024) # logs are stored in logfile.log
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

def configure() :
    load_dotenv("venv/.env")

url = "mongodb+srv://mlteam:"+str(os.getenv('gdsc_client_url'))+".mongodb.net/?retryWrites=true&w=majority"
gdsc_client_url = "mongodb+srv://mlteam:"+str(os.getenv('gdsc_client_url'))+".mongodb.net/?retryWrites=true&w=majority"
# all projects, events, and blogs
def all_gdsc(db_name, db_attribute) :
    client = pym.MongoClient(gdsc_client_url)
    db = client["test"]
    collection = db[db_name]
    result = []
    for item in collection.find() :
        result.append(item[db_attribute])
    if len(result) > 1:
        return (", ".join(result[:-1]) + " and " + result[-1])
    elif len(result) == 1:
        return result[0]
    else:
        return ""
def all_gdsc_questions(text) :
    if "projects" in text.split() :
        return (True, "the projects of GDSC till date - "+all_gdsc("projects", "name"))
    elif "events" in text.split() :
        return (True, "the events of GDSC till date - "+all_gdsc("events", "title"))
    elif "blogs" in text.split() :
        return (True, "the blogs of GDSC till date - "+all_gdsc("blogs", "title"))
    return (False, "")

# making specification list
# this function allows us to know whether the user is talking about event, blogs or project
def make_specification_list(text) :
    splitted_text = text.split()
    result_list = [0, 0, 0]
    # 0 -> event
    # 1 -> blog
    # 2 -> projects
    if "event" in splitted_text or "events" in splitted_text :
        result_list[0] = 1
    elif "blog" in splitted_text or "blogs" in splitted_text :
        result_list[1] = 1
    elif "project" in splitted_text or "website" in splitted_text or "application" in splitted_text or "app" in splitted_text :
        result_list[2] = 1
    if sum(result_list) == 1 :
        # if the user is talking about a specific thing
        return result_list
    else :
        return [1, 1, 1]

# yake functions
def clean_text(txt):
    txt = ' '.join(txt.split('\n'))
    txt = txt.lower()
    txt = re.sub(r"(@\[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)|^rt|http.+?", "", txt)
    return txt
def predict_context(para) :
    para = clean_text(para)
    kw_extractor = KeywordExtractor(lan="en", n=1, top=5)
    list_of_keywords = kw_extractor.extract_keywords(text=para)
    final_list = [itr[0] for itr in list_of_keywords]
    return final_list

# this function checks whether the text is a general question or not
def general_question(text) :
    text = text.strip()
    # about gdsc
    about_gdsc_list = ["tell me something about gdsc kgec",
     "what is gdsc", "what does gdsc do",
     "can you please tell me about gdsc",
     "can you please tell me what gdsc does",
     "what is the role of gdsc", "what is the role of gdsc kgec",
     "what is gdsc kgec",
     "what does gdsc kgec actually do"]
    new_about_gdsc_list = []
    for it in about_gdsc_list :
        new_about_gdsc_list.append(clean_text(it).strip())
    about_gdsc_list = new_about_gdsc_list
    if text in about_gdsc_list :
        return (True, general_answer_dict["about_gdsc"])
    # domain
    if text.find("domain") != -1 :
        return (True, general_answer_dict["domains"])
    # good bye
    if text.find("bye") != -1 :
        return (True, general_answer_dict["good_bye"])
    # thank you
    if text.find("thank") != -1 :
        return (True, general_answer_dict["thank_you"])
    # about
    about_list = ["you", "yourself", "your"]
    for it in about_list :
        if it in text.split() :
            return (True, general_answer_dict["about"])
    # greeting
    greet_list = ["hi", "hello"]
    for it in greet_list :
        if it in text.split() :
            return (True, general_answer_dict["greeting"])
    # connect
    if (text.find("in touch") != -1) or ("connect" in text.split()) or ("contact" in text.split()) or ("join" in text.split()) :
        return (True, general_answer_dict["connect"])

    return (False, "")

def get_response_from_responselist(response_list) :
    response_dict = response_list[0][0]
    if "event_link" in list(response_dict.keys()):
        # user is talking about an event
        response = "event - {e_name} \ndescription - {e_desc} \nlink to the gdsc event page - {e_link} \nconducted in - {e_time}".format(
            e_name=response_dict["title"], e_desc=response_dict["description"],
            e_link=response_dict["event_link"], e_time=response_dict["time"])
    elif "blog_link" in list(response_dict.keys()):
        # user is talking about a blog
        response = "blog - {b_name} \ndescription - {b_desc} \nlink to the blog - {b_link}".format(
            b_name=response_dict["title"], b_desc=response_dict["description"],
            b_link=response_dict["blog_link"])
    elif "repo_link" in list(response_dict.keys()):
        # user is talking about a project
        response = "project - {p_name} \ndescription - {p_about} \nlink to github - {p_link}".format(
            p_name=response_dict["name"], p_about=response_dict["about"], p_link=response_dict["repo_link"])
    else:
        response = "didn't find what you were looking for."
    return response
def search_keyword_in_gdsc_database(keyword, specification_list) :
    client = pym.MongoClient(gdsc_client_url)
    db = client["test"]
    collention_events = db["events"]
    collention_blogs = db["blogs"]
    collention_projects = db["projects"]
    response_list = []
    if specification_list[0] == 1 :
        for item in collention_events.find({'title': {"$regex": '{}.*'.format(keyword), "$options": 'i'}}):
            title = str(item["title"])
            desc = str(item["longDescription"])
            event_url = str(item["gdscPlatformLink"])
            time = str(item["date"])[:10]
            response_list.append(({"title" : title, "description" : desc, "event_link" : event_url, "time" : time}, 0))
    if specification_list[1] == 1 :
        for item in collention_blogs.find({'title': {"$regex": '{}.*'.format(keyword), "$options": 'i'}}):
            title = str(item["title"])
            blog_url = str(item["url"])
            desc = str(item["shortDescription"])
            response_list.append(({"title": title, "description": desc, "blog_link": blog_url}, 1))
    if specification_list[2] == 1 :
        for item in collention_projects.find({'name': {"$regex": '{}.*'.format(keyword), "$options": 'i'}}):
            name = str(item["name"])
            about = str(item["about"])
            repolink = str(item["repoLink"])
            response_list.append(({"name" : name, "about" : about, "repo_link" : repolink}, 2))
    return response_list
def predict_output(keyword, specification_list) :
    response_list = search_keyword_in_gdsc_database(keyword, specification_list)
    if len(response_list) < 1 :
        response = "didn't find what you were looking for."
    elif len(response_list) > 1 :
        collections_of_response = []
        for it in response_list :
            collections_of_response.append(it[1])
        collections_of_response = list(set(collections_of_response))
        if len(collections_of_response) == 1 :
            response = get_response_from_responselist(response_list)
        else :
            response = "didn't find a specific answer to your question."
    else :
        response = get_response_from_responselist(response_list)
    return  response

# database functions
def store_context(userID="123", context="DSC") :
    try :
        client = pym.MongoClient(url) # client
        db = client["chatbot_database"] # database
        collection = db["first_collection"] # collection
        db_dict = {"chatID" : userID, "context" : context}
        if collection.count_documents({"chatID": userID}) > 0 :
            collection.update_one({"chatID": userID}, {"$set": {"context": context}})
        else :
            collection.insert_one(db_dict)
    except :
        pass
def get_context(userID="123") :
    try:
        client = pym.MongoClient(url)  # client
        db = client["chatbot_database"]  # database
        collection = db["first_collection"]  # collection
        found = collection.find_one({"chatID" : userID})
        return found["context"]
    except :
        return "gdsc kgec"

def chatbot_response(text, uid):
    try :
        # SPECIAL CATEGORY QUESTIONS
        # if category is general
        text = str(text)
        if(general_question(clean_text(text))[0] == True) :
            return (general_question(clean_text(text))[1], text)
        # if all-gdsc questions
        if(all_gdsc_questions(clean_text(text))[0] == True) :
            return (all_gdsc_questions(clean_text(text))[1], text)
        # if there is an it, we replace it with the original context of the text
        if "it" in (clean_text(text).split()) :
            try :
                context = str(get_context(userID=uid))
                text = text.replace("it", context)
                keyword = context
            except :
                return ("What do you mean by it?", text)
        else :
            contx_list = predict_context(text)
            for it in remove_elements:
                if it in contx_list:
                    contx_list.remove(it)
            if len(contx_list) == 0 :
                return ("didn't understand your question", text)
            contx = contx_list[0] # most important context
            keyword = contx
            # print(contx)
            store_context(userID=uid, context=contx)

        # print(keyword)
        res = predict_output(keyword, make_specification_list(clean_text(text)))
        return (res, text)
    except Exception as exp :
        logger.warning(str(exp))
        return ("some unknown error occured", str(text))

def chatbot_response_without_uid(text, uid) :
    # if category is general
    text = str(text)
    # if there is an it, we return an error
    if "it" in (clean_text(text).split()):
        return "What do you mean by it?"
    return chatbot_response(text, uid)[0]

@app.route("/")
def default():
  value_to_be_returned = {
    "error": False,
    "message": "All Good!!"
  }
  return value_to_be_returned
  
@app.route('/reply', methods=['POST', 'GET'])
def reply_to_text():
    if request.method == 'POST':
        data = request.json
        keys_list = list(data.keys())
        # with user-id
        if len(keys_list) == 2 and "text" in keys_list and "user_id" in keys_list :
            text = data["text"]
            uid = data["user_id"]
            # print(text)

            value_to_be_returned = {
                "error": False,
                "reply": chatbot_response(text, uid)[0],
                "text" : chatbot_response(text, uid)[1]
            }
        # without user-id
        elif len(keys_list) == 1 and "text" in keys_list :
            text = data["text"]
            # new_user_id = str(uuid.uuid1())
            new_user_id = "7434eb6b-8951-11ed-acff-9f7e29ad42c1"
            response = chatbot_response_without_uid(text, new_user_id)
            value_to_be_returned = {
                "error" : False,
                # "user_id" : new_user_id,
                "reply" : response
            }
        else :
            value_to_be_returned = {
                "error" : True,
                "reply" : "invalid data"
            }

    else:
        value_to_be_returned = {
            "error": True,
            "message": "Only Post Allowed"
        }
    return value_to_be_returned

if __name__ == '__main__':
    configure()
    print('client url ->', "mongodb+srv://mlteam:"+str(os.getenv('gdsc_client_url'))+".mongodb.net/?retryWrites=true&w=majority")
    app.run(debug=True)