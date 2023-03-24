from flask import Flask, request
import logging
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, Response, jsonify
import os
from dotenv import load_dotenv
import json
import requests
from config import *
from datetime import datetime, timedelta
import pandas as pd
from pandas import json_normalize
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

import os
from slack_sdk.oauth import AuthorizeUrlGenerator
from slack_sdk.oauth.installation_store import FileInstallationStore, Installation
from slack_sdk.oauth.state_store import FileOAuthStateStore

# Issue and consume state parameter value on the server-side.
#state_store = FileOAuthStateStore(expiration_seconds=300, base_dir="./data")
# Persist installation data and lookup it by IDs.
#installation_store = FileInstallationStore(base_dir="/data/installations")

# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
# authorize_url_generator = AuthorizeUrlGenerator(
#     client_id=os.environ["SLACK_CLIENT_ID"],
#     scopes=["app_mentions:read", "chat:write"],
#     user_scopes=["search:read"],
# )

from flask import Flask, request, make_response

oauth_settings = OAuthSettings(
    client_id=os.environ["SLACK_CLIENT_ID"],
    client_secret=os.environ["SLACK_CLIENT_SECRET"],
    install_path="/slack/install",
    scopes=["app_mentions:read", "channels:history", "channels:manage", "chat:write","commands", "groups:history", "im:write","reactions:read", "files:write"],
    user_scopes=["admin","channels:history", "chat:write"],
    redirect_uri_path="/slack/oauth_redirect",
    installation_store= FileInstallationStore(base_dir="./data/installations"),
    state_store=FileOAuthStateStore(expiration_seconds=600, base_dir="./data/states"),
    
)


app = App(
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    oauth_settings=oauth_settings,
       
)

headers = {'Content-type': 'application/json', 'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImQ1OTRhMjA5LTY4NDUtNDkyMy04NWY1LTkxZjBkZTU3NWI5MSIsInVzZXJfaWQiOjEsInVzZXJuYW1lIjoiYWRtaW5AdHlrZS5haSIsInNlc3Npb25faWQiOiJjMGRiM2EwZS1jOTYwLTQzZWUtOThiNC1jMTBhMGJkOWIzOWQiLCJyb2xlIjoiQWRtaW4iLCJpc3N1ZWRfYXQiOiIyMDIzLTAzLTI0VDA1OjE0OjU4Ljk0NTU3ODY0MVoiLCJleHBpcmVkX2F0IjoiMjAyMy0wMy0yNVQwNToxNDo1OC45NDU1NzkxMjNaIn0.QrLe4ccjb203bNsWiVHEjK5fndKGAKZHddPEchit9kI'}

@app.middleware  # or app.use(log_request)
def log_request(logger, body, next):
    # logger.debug(body)
    return next()


@app.event("app_mention")
def event_test(body, say, logger):
    #logger.info(body)
    print("appmention")
    say("Hi! I'm Tyke Bot. Please check shortcuts to explore my functions.")


@app.message("Hello")
def say_hello(message, say):
    user = message['user']
    say(f"Hi there, <@{user}>!")

@app.shortcut("test_suite_create")
def open_modal(ack, shortcut, client):
    # Acknowledge the shortcut request
    ack()

    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        tags_res = requests.get(url=API_GET_TAGS, headers=headers)
        print(workspace_res.json())
        print(tags_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))
    tags_list = list(map(lambda x: {'name': x['name'], 'id': x['id']}, json.loads(
        tags_res.text)['data']))

    views = json.load(open('./user-interface/modals/test-suite-creation.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
    views['blocks'][2]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, tags_list))
    # print(views)
    # print(tags_list)
    # print(views)
    client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    with open('./user-interface/modals/test-suite-creation.json', "w") as outfile:
        json.dump(views, outfile)

@app.action("select-workspace-create-test-suite")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()
    # Call views_update with the built-in client
    print("Here", body["view"])

    workspace_id = body['actions'][0]['selected_option']['value']

    # print(API_COLLECTIONS + f"workspace_id={workspace_id}")
    try:
        collection_res = requests.get(
            url=API_GET_API_COLLECTIONS + f"{workspace_id}", headers=headers)
        print("Success get collections")
    except:
        print("An exception occurred")

    # print(json.loads(collection_res.text)['data'])
    collection_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, collection_res.json()['data']))

    views = json.load(open('./user-interface/modals/test-suite-creation.json'))

    # print(views['blocks'][1]['elements'][0]['options'])
    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, collection_list))
    print(views['blocks'][1]['element']['options'])
    response = client.views_update(    # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"], view=json.dumps(views))

@app.view("test-suite-create")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)
    # Validate the inputs
    errors = {}
    if selected_values['testsuitename']['plain_text_input-action']['value'] is not None and len(selected_values['testsuitename']['plain_text_input-action']['value']) <= 5:
        errors["testsuitename"] = "The value must be longer than 5 characters"
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    ack()

    
    selected_tags = []
    for i in range(0, len(selected_values['tags']['multi_static_select-action']['selected_options'])):
        selected_tags.append(
            selected_values['tags']['multi_static_select-action']['selected_options'][i]['value'])
    assertions=[{"category": "response_content", "field": "data", "condition": "match_expected",
                'options': {"ignore_identifiers": False, "ignore_timestamps": False, "schema_only": False}}]
    assertions[0]["options"][selected_values['includestatuscode']['radio_buttons-action']['selected_option']['text']['text'].replace(" ", "_").lower()]=True
    if(selected_values['includestatuscode']['radio_buttons-action']['selected_option']['value'] == 'True'):
        assertions.append({"category": "response_status", "field": "code",
                "condition": "match_expected"})
    
    testsuitename = selected_values['testsuitename']['plain_text_input-action']['value']  
    payload = {'name': testsuitename,
               'testcase_prefix': selected_values['testcaseprefix']['plain_text_input-action']['value'],
               'description': selected_values['description']['plain_text_input-action']['value'],
               'workspace_id': selected_values['workspace']['select-workspace-create-test-suite']['selected_option']['value'],
               'deduplicate_requests': selected_values['deduplicaterequests']['radio_buttons-action']['selected_option']['value'] == 'True',
               'duplicate': True,
               'assertions': assertions,
                'collection_id': selected_values['apicollection']['static_select-action']['selected_option']['value'],
                'tags': selected_tags}

    # Message to send user
    msg = ""
    try:
        testsuite_res = requests.post(
            url=API_POST_TEST_SUITE, data=json.dumps(payload), headers=headers)
        print("Response1", testsuite_res.json())
        print(json.dumps(payload))
        msg = f'Your test suite {testsuitename} created successfully'

    except Exception as e:
        print(e)
        msg = f"Your test suite {testsuitename} creation failed, due to {e}"

    # Message the user
    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

@app.shortcut("api_collection_create")
def open_modal(ack, shortcut, client):
    # Acknowledge the shortcut request
    ack()

    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        print(workspace_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))

    views = json.load(open('./user-interface/modals/api-collection-creation.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
   
    client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    
    with open('./user-interface/modals/api-collection-creation.json', "w") as outfile:
        json.dump(views, outfile)

@app.action("select-workspace-create-api-collection")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()
    # Call views_update with the built-in client
    print("Here", body["view"])

    workspace_id = body['actions'][0]['selected_option']['value']

    # print(API_COLLECTIONS + f"workspace_id={workspace_id}")
    try:
        services_res = requests.get(
            url=API_GET_SERVICES + f"{workspace_id}", headers=headers)
        print("Success get services")
    except:
        print("An exception occurred")

    # print(json.loads(collection_res.text)['data'])
    services_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, services_res.json()['data']))

    views = json.load(open('./user-interface/modals/api-collection-creation.json'))

    # print(views['blocks'][1]['elements'][0]['options'])
    views['blocks'][3]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, services_list))
    
    client.views_update(    # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"], view=json.dumps(views))

@app.view("api-collection-create")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)
    # Validate the inputs
    errors = {}
    if selected_values['apicollectionname']['plain_text_input-action']['value'] is not None and len(selected_values['apicollectionname']['plain_text_input-action']['value']) <= 5:
        errors['apicollectionname'] = "The value must be longer than 5 characters"
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    ack()
    apicollectionname= selected_values['apicollectionname']['plain_text_input-action']['value'];
    payload = {
    'name': apicollectionname, 
    'start_time': str(datetime.now() - timedelta(hours = float(selected_values['collectionperiod']['static_select-action']['selected_option']['value']))),
    'end_time': datetime.now().isoformat(),
    'service_id': selected_values['service']['static_select-action']['selected_option']['value'],
    'description': selected_values['description']['plain_text_input-action']['value'],
    'duplicate': True
    }
    
    # Message to send user
    msg = ""
    try:
        apicollection_res = requests.post(
            url=API_POST_API_COLLECTION, data=json.dumps(payload), headers=headers)
        print("Response", apicollection_res.json())
        print(json.dumps(payload))
        msg = f'Your collection {apicollectionname} created successfully'

    except Exception as e:
        print(e)
        msg = f"Your collection {apicollectionname} creation failed, due to {e}"

    # Message the user
    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

@app.command("/listtestsuite")
def open_modal(ack, logger,body, client):
    # Acknowledge command request
    ack()
    logger.info(body)
    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        print(workspace_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))

    views = json.load(open('./user-interface/modals/list-test-suite.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))

    client.views_open(
        trigger_id=body["trigger_id"], view=json.dumps(views))
    #respond(f"{command['text']}")

@app.view("list-test-suite")
def handle_submission(ack, body, client, view,say, respond):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    #print(selected_values)
    # Validate the inputs
    ack()
    workspace_id= selected_values['selectworkspace']['static_select-action']['selected_option']['value']
    page_no = selected_values['selectpage']['static_select-action']['selected_option']['value']
    channel_id = selected_values['selectconv']['convtext']['selected_conversation']
    #print(channel_id)
    try:
        testsuite_res = requests.get(url=API_GET_TEST_SUITE_BY_PAGE+ f"{workspace_id}" + f"&page={page_no}&page_size=20&", headers=headers)
        #print(testsuite_res.json()['data'])
    except:
        print("An exception occurred")
    print(selected_values['selectconv'])

    testsuitedf= pd.json_normalize(testsuite_res.json()['data'])
    testsuitedf=testsuitedf[['name', 'description','collection.name','total_test_cases','execution_count']]
    md_table = testsuitedf.to_markdown()
    print(testsuitedf.head())
    #say(channel=channel_id, text="Done")
    blocks = json.load(open('./user-interface/modals/list-test-suite-blocks.json'))
    blocks['blocks'][0]['text']['text']= "```\n" + md_table + "```\n"
    client.chat_postMessage(channel=channel_id, text="```\n" + md_table + "```\n")

@app.shortcut("execute_test_suite")
def open_modal(ack, shortcut, client):
    # Acknowledge the shortcut request
    ack()

    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        print(workspace_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))

    views = json.load(open('./user-interface/modals/execute-test-suite.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
   
    client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    
    with open('./user-interface/modals/execute-test-suite.json', "w") as outfile:
        json.dump(views, outfile)

@app.action("select-workspace-execute-test-suite")
def update_modal(ack, body, client):
   # Acknowledge the button request
    ack()
    # Call views_update with the built-in client
    print("Here", body["view"])

    workspace_id = body['actions'][0]['selected_option']['value']

    # print(API_COLLECTIONS + f"workspace_id={workspace_id}")
    try:
        testsuite_res = requests.get(
            url=API_GET_TEST_SUITE_BY_PAGE_100_PER_ROW + f"{workspace_id}", headers=headers)
        print("Success get services")
    except:
        print("An exception occurred")

    # print(json.loads(collection_res.text)['data'])
    testsuite_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, testsuite_res.json()['data']))

    views = json.load(open('./user-interface/modals/execute-test-suite.json'))

    # print(views['blocks'][1]['elements'][0]['options'])
    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, testsuite_list))
    
    client.views_update(    # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"], view=json.dumps(views)) 
    with open('./user-interface/modals/execute-test-suite.json', "w") as outfile:
        json.dump(views, outfile)
    client.files_upload

@app.view("execute-test-suite")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)

    ack()
    testsuite_name=selected_values['selecttestsuite']['static_select-action']['selected_option']['value']
    payload = {
    'exec_type': 'custom',
    'testsuite_id': testsuite_name
    }
    
    # Message to send user
    msg = ""
    try:
        execute_res = requests.post(
            url=API_TEST_SUITE_EXECUTE, data=json.dumps(payload), headers=headers)
        print("Response", execute_res.json())
        print(json.dumps(payload))
        message =execute_res.json()['message']
        msg = f'{message}'

    except Exception as e:
        print(e)
        msg = f"Your testsuite {testsuite_name} execution failed, due to {e}"

    # Message the user
    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")

@app.shortcut("export_test_cases")
def open_modal(ack, shortcut, client):
    # Acknowledge the shortcut request
    ack()

    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        print(workspace_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))

    views = json.load(open('./user-interface/modals/export-test-cases.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
   
    client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    
    with open('./user-interface/modals/export-test-cases.json', "w") as outfile:
        json.dump(views, outfile)

@app.action("select-workspace-export-test-cases")
def update_modal(ack, body, client):
   # Acknowledge the button request
    ack()
    # Call views_update with the built-in client
    print("Here", body["view"])

    workspace_id = body['actions'][0]['selected_option']['value']

    # print(API_COLLECTIONS + f"workspace_id={workspace_id}")
    try:
        testsuite_res = requests.get(
            url=API_GET_TEST_SUITE_BY_PAGE_100_PER_ROW + f"{workspace_id}", headers=headers)
        print("Success get services")
    except:
        print("An exception occurred")

    # print(json.loads(collection_res.text)['data'])
    testsuite_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, testsuite_res.json()['data']))

    views = json.load(open('./user-interface/modals/export-test-cases.json'))

    # print(views['blocks'][1]['elements'][0]['options'])
    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, testsuite_list))
    
    client.views_update(    # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"], view=json.dumps(views)) 
    with open('./user-interface/modals/export-test-cases.json', "w") as outfile:
        json.dump(views, outfile)

@app.view("export-test-cases")
def handle_submission(ack, body, client, view, logger):
    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)

    ack()
    testsuite_id=selected_values['selecttestsuite']['static_select-action']['selected_option']['value']
    print("Test Suite:", testsuite_id)
    # Message to send user
    msg = ""
    try:
        testcases_res = requests.get(
            url=API_GET_TEST_CASES+f"{testsuite_id}", headers=headers)
        #print("Response", testcases_res.json())

        testcases_data = pd.json_normalize(testcases_res.json(), record_path =['data'])
        #testcases_data.info()
    except Exception as e:
        print(e)
        msg = f"Your testcases was not possible to fetch due to {e}"
    
    client.files_upload(
        channels=user,
        initial_comment="Here's your test cases file :smile:",
        filetype="csv",
        filename="testcase.csv",
        content= testcases_data.to_string(index = False)
    )

@app.shortcut("list_api_collections")
def open_modal(ack, respond,shortcut, client):

    ack();
    try:
        workspace_res = requests.get(url=API_GET_WORKSPACES, headers=headers)
        print(workspace_res.json())
    except:
        print("An exception occurred")

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res.json()['data']))

    views = json.load(open('./user-interface/modals/list-api-collections.json'))
    # print(views['blocks'][0]['elements'][0]['options'])

    views['blocks'][0]['element'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
   
    client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    
    with open('./user-interface/modals/list-api-collections.json', "w") as outfile:
        json.dump(views, outfile)

@app.view("list-api-collections")
def handle_submission(ack, body, client, view,say, respond):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    #print(selected_values)
    # Validate the inputs
    ack()
    workspace_id= selected_values['selectworkspace']['static_select-action']['selected_option']['value']
    page_no = selected_values['selectpage']['static_select-action']['selected_option']['value']
    channel_id = selected_values['selectconv']['convtext']['selected_conversation']
    #print(channel_id)
    try:
        apicollec_res = requests.get(url=API_GET_API_COLLECTIONS+ f"{workspace_id}" + f"&page={page_no}&page_size=20&", headers=headers)
        #print(apicollec_res.json()['data'])
    except:
        print("An exception occurred")
    print(selected_values['selectconv'])

    apicollecdf= pd.json_normalize(apicollec_res.json()['data'])
    apicollecdf=apicollecdf[['name', 'description','collection.name','total_test_cases','execution_count']]
    md_table = apicollecdf.to_markdown()
    print(apicollecdf.head())
    #say(channel=channel_id, text="Done")
    blocks = json.load(open('./user-interface/modals/list-test-suite-blocks.json'))
    blocks['blocks'][0]['text']['text']= "```\n" + md_table + "```\n"
    client.chat_postMessage(channel=channel_id, text="```\n" + md_table + "```\n")

@app.event("app_home_opened")
def handle_app_home_opened_events(body, logger, client):
    logger.info(body['event']['user'])
    client.views_publish(
        user_id=body['event']['user'], view=json.dumps(json.load(open('./user-interface/modals/app-home.json'))))

flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# @flask_app.route("/slack/install", methods=["GET"])
# def oauth_start():
#     print("Yes1")
#     # Generate a random value and store it on the server-side
#     state = state_store.issue()
#     # https://slack.com/oauth/v2/authorize?state=(generated value)&client_id={client_id}&scope=app_mentions:read,chat:write&user_scope=search:read
#     url = authorize_url_generator.generate(state)
#     print("Yes2")
#     return f'<a href="{url}">' \
#            f'<img alt=""Add to Slack"" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>'


from slack_sdk.web import WebClient
client_secret = os.environ["SLACK_CLIENT_SECRET"]


# @flask_app.route("/slack/oauth/callback", methods=["GET"])
# def oauth_callback():
#     args = request.args
#     print("Yes1")
   
#     if "code" in request.args:
       
#         if state_store.consume(request.args["state"]):
#             client = WebClient() 
            
#             oauth_response = client.oauth_v2_access(
#                 client_id="3758031487061.4566211234965",
#                 client_secret=client_secret,
#                 redirect_uri="https://54.147.129.186/slack/oauth/callback",
#                 code=request.args["code"]
#             )

#             installed_enterprise = oauth_response.get("enterprise", {})
#             is_enterprise_install = oauth_response.get("is_enterprise_install")
#             installed_team = oauth_response.get("team", {})
#             installer = oauth_response.get("authed_user", {})
#             incoming_webhook = oauth_response.get("incoming_webhook", {})

#             bot_token = oauth_response.get("access_token")
           
#             bot_id = None
#             enterprise_url = None
#             if bot_token is not None:
#                 auth_test = client.auth_test(token=bot_token)
#                 bot_id = auth_test["bot_id"]
#                 if is_enterprise_install is True:
#                     enterprise_url = auth_test.get("url")

#             installation = Installation(
#                 app_id=oauth_response.get("app_id"),
#                 enterprise_id=installed_enterprise.get("id"),
#                 enterprise_name=installed_enterprise.get("name"),
#                 enterprise_url=enterprise_url,
#                 team_id=installed_team.get("id"),
#                 team_name=installed_team.get("name"),
#                 bot_token=bot_token,
#                 bot_id=bot_id,
#                 bot_user_id=oauth_response.get("bot_user_id"),
#                 bot_scopes=oauth_response.get("scope"), 
#                 user_id=installer.get("id"),
#                 user_token=installer.get("access_token"),
#                 user_scopes=installer.get("scope"),  
#                 incoming_webhook_url=incoming_webhook.get("url"),
#                 incoming_webhook_channel=incoming_webhook.get("channel"),
#                 incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
#                 incoming_webhook_configuration_url=incoming_webhook.get("configuration_url"),
#                 is_enterprise_install=is_enterprise_install,
#                 token_type=oauth_response.get("token_type"),
#             )

#             # Store the installation
#             installation_store.save(installation)

#             return "Thanks for installing this app!"
#         else:
#             return make_response(f"Try the installation again (the state value is already expired)", 400)

#     error = request.args["error"] if "error" in request.args else ""
#     return make_response(f"Something is wrong with the installation (error: {error})", 400)



@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

@flask_app.route("/listtestsuite", methods=["POST"])
def list_test_suite():
    return handler.handle(request)

@flask_app.route("/slack/interactive-endpoint", methods=["POST"])
def slack_interactive_endpoint():
    return handler.handle(request)

@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_redirect():
    return handler.handle(request)

@flask_app.route("/slack/install", methods=["GET"])
def slack_install():
    return handler.handle(request)


if __name__ == '__main__':
    #flask_app.run(host='0.0.0.0', port=5000)
    flask_app.run(host='0.0.0.0', port=5000, ssl_context=("/home/ubuntu/certs/tyke.ai.crt", "/home/ubuntu/certs/tyke.ai.key") )

# Start your app
