from api_request import api_request
from config import *
import psycopg2
from flask_cors import CORS, cross_origin
from flask import Flask, request, make_response
from slack_sdk.web import WebClient
from slack_sdk.oauth.installation_store import FileInstallationStore, Installation
from slack_sdk.oauth import AuthorizeUrlGenerator
from flask import Flask, request, redirect
import logging
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, Response, jsonify
import os
from dotenv import load_dotenv
import json
import requests
from api_config import *
from datetime import datetime, timedelta
import pandas as pd
from pandas import json_normalize
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store import FileInstallationStore
from slack_sdk.oauth.state_store import FileOAuthStateStore
import time
from url_generate import url_generate
load_dotenv()
logging.basicConfig(level=logging.DEBUG)

import datetime


slack_client_secret = os.environ["SLACK_CLIENT_SECRET"]
slack_client_id = os.environ["SLACK_CLIENT_ID"]
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
tyke_api_url = os.environ['TYKE_API']
tyke_ui_url = os.environ['TYKE_UI']
tyke_slack_url = os.environ['TYKE_SLACK']


def ExecuteQuery(query):
    try:
        conn = psycopg2.connect(
            dbname=DB_SOURCE,  # Replace with your database name
            user=DB_USERNAME,  # Replace with your username
            password=DB_PASSWORD,  # Replace with your password
            host=TESTS_STORE,  # Replace with your host
            port=DB_PORT  # Replace with your port (default is usually 5432)
        )

        cur = conn.cursor()
        cur.execute(query)

        rows = cur.fetchall()

        if rows is None:
            return [()]
        return rows
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error:", error)
    finally:
        if conn is not None:
            conn.commit()
            cur.close()
            conn.close()


# Issue and consume state parameter value on the server-side.
state_store = FileOAuthStateStore(
    expiration_seconds=300, base_dir="./data/states")
# Persist installation data and lookup it by IDs.
installation_store = FileInstallationStore(base_dir="./data/installations")

# Build https://slack.com/oauth/v2/authorize with sufficient query parameters
authorize_url_generator = AuthorizeUrlGenerator(
    client_id=slack_client_id,
    scopes=["app_mentions:read", "channels:history", "channels:manage", "chat:write",
            "commands", "groups:history", "im:write", "reactions:read", "files:write"],
    user_scopes=["admin", "channels:history", "chat:write"],
)

oauth_settings = OAuthSettings(
    client_id=slack_client_id,
    client_secret=slack_client_secret ,
    install_path="/slack/install",
    scopes=["app_mentions:read", "channels:history", "channels:manage", "chat:write",
            "commands", "groups:history", "im:write", "reactions:read", "files:write"],
    user_scopes=["admin", "channels:history", "chat:write"],
    redirect_uri_path="/slack/oauth_redirect",
    installation_store=installation_store,
    state_store=state_store,
)

app = App(
    signing_secret=slack_signing_secret,
    oauth_settings=oauth_settings,
)

headers = {'Content-type': 'application/json', 'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImYxNTU5NWJjLTI3MGItNDgyYS1hYjRkLTcyOWRhZjFjYmIxMSIsInVzZXJfaWQiOjksInVzZXJuYW1lIjoicmF2aS5jaGFuZHJhbkB0eWtlLmFpIiwic2Vzc2lvbl9pZCI6ImQxZGI3Njk0LTgwNmQtNDllOC1hNDJjLTUyNzA1MzU5Njk0ZCIsInJvbGUiOiJBZG1pbiIsImlzc3VlZF9hdCI6IjIwMjMtMDQtMTVUMTA6MTk6MjAuOTAwMTMxNzE4WiIsImV4cGlyZWRfYXQiOiIyMDIzLTA0LTE2VDEwOjE5OjIwLjkwMDEzMTg1N1oifQ.BeVXJ_bNxhAPOhnFqMRc_0blABUgznZSluRgZobBd5w'}


@app.middleware  # or app.use(log_request)
def middleware(client, body, next, logger):
    #logger.debug(body)   
    if "user" in body:
        team_id = body['user']['team_id']
        user_id = body['user']['id']
    elif "user_id" in body:
        team_id = body['team_id']
        user_id = body['user_id']
    else:
        pass
    install_store = installation_store.find_installation(
        enterprise_id=None, team_id=team_id, user_id=user_id)
    headers['Authorization'] = f"{install_store.custom_values['tyke_user_token']}"
    print(install_store.custom_values['tyke_user_token'])
    try:
        health = api_request(method='GET', url=API_HEALTH, headers=headers)
    except requests.exceptions.HTTPError as e:
        print("Reached",e.response.status_code)
        if e.response.status_code == 401:
            views = json.load(open('./user-interface/modals/login.json'))
            res = client.views_open(
                trigger_id=body["trigger_id"], view=json.dumps(views))

            views['blocks'][0]['accessory']['url']= url_generate(user_id=install_store.custom_values['user_id'], redirect_uri=tyke_slack_url+"/slack/oauth_post")
            client.views_update(
                view_id= res['view']['id'], view= views 
                )

    return next()


@app.event("app_mention")
def event_test(body, say, logger):
    # logger.info(body)
    print("appmention")
    say("Hi! I'm Tyke Bot. Please check shortcuts to explore my functions.")


@app.message("Hello")
def say_hello(message, say):
    user = message['user']
    say(f"Hi there, <@{user}>!")


@app.shortcut("test_suite_create")
def open_modal(ack, shortcut, client, logger):
    # Acknowledge the shortcut request
    ack()
    views = json.load(open('./user-interface/modals/test-suite-creation.json'))

    res = client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    print("Headers",headers)
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
        tags_res = api_request(method='GET', url=API_GET_TAGS, headers=headers)
    except Exception as e:
        logger.error(e)

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))
    tags_list = list(map(lambda x: {'name': x['name'], 'id': x['id']}, tags_res['data']))

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

    client.views_update(
        view_id= res['view']['id'], view= views 
    )
    with open('./user-interface/modals/test-suite-creation.json', "w") as outfile:
        json.dump(views, outfile)


@app.action("select-workspace-create-test-suite")
def update_modal(ack, body, client, logger):

    ack()

    workspace_id = body['actions'][0]['selected_option']['value']

    try:
        collection_res = api_request(method='GET',
                                     url=API_GET_API_COLLECTIONS + f"{workspace_id}", headers=headers)
    except Exception as e:
        logger.error(e)

    collection_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, collection_res['data']))

    views = json.load(open('./user-interface/modals/test-suite-creation.json'))

    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, collection_list))

    client.views_update(    
        view_id=body["view"]["id"],
        hash=body["view"]["hash"], view=json.dumps(views))


@app.view("test-suite-create")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)

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
    assertions = [{"category": "response_content", "field": "data", "condition": "match_expected",
                  'options': {"ignore_identifiers": False, "ignore_timestamps": False, "schema_only": False}}]
    assertions[0]["options"][selected_values['includestatuscode']['radio_buttons-action']
                             ['selected_option']['text']['text'].replace(" ", "_").lower()] = True
    if (selected_values['includestatuscode']['radio_buttons-action']['selected_option']['value'] == 'True'):
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
        testsuite_res = api_request(method='POST', 
            url=API_POST_TEST_SUITE, data=json.dumps(payload), headers=headers)

        if testsuite_res['error']:
            msg = f"Your test suite {testsuitename} creation failed. Error message: {testsuite_res['message']}"
        else:
            msg = f'Your test suite {testsuitename} created successfully'

    except Exception as e:
        logger.error(e)

    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")


@app.shortcut("api_collection_create")
def open_modal(ack, shortcut, client, logger):
    # Acknowledge the shortcut request
    ack()


    views = json.load(
        open('./user-interface/modals/api-collection-creation.json'))
    res = client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
    except Exception as e:
        logger.error(e)

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))


    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
    
    client.views_update(
        view_id= res['view']['id'], view= views 
    )

    with open('./user-interface/modals/api-collection-creation.json', "w") as outfile:
        json.dump(views, outfile)


@app.action("select-workspace-create-api-collection")
def update_modal(ack, body, client, logger):
    # Acknowledge the button request
    ack()

    workspace_id = body['actions'][0]['selected_option']['value']

    try:
        services_res = api_request(method='GET',
                                   url=API_GET_SERVICES + f"{workspace_id}", headers=headers)
    except Exception as e:
        logger.error(e)

    services_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, services_res['data']))

    views = json.load(
        open('./user-interface/modals/api-collection-creation.json'))

    views['blocks'][3]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, services_list))

    client.views_update(    
        view_id=body["view"]["id"],
        hash=body["view"]["hash"], view=json.dumps(views))


@app.view("api-collection-create")
def handle_submission(ack, body, client, view, logger):

    ack()
    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    errors = {}

    if selected_values['apicollectionname']['plain_text_input-action']['value'] is not None and len(selected_values['apicollectionname']['plain_text_input-action']['value']) <= 5:
        errors['apicollectionname'] = "The value must be longer than 5 characters"
    if len(errors) > 0:
        ack(response_action="errors", errors=errors)
        return

    
    apicollectionname = selected_values['apicollectionname']['plain_text_input-action']['value']
    payload = {
        'name': apicollectionname,
        'start_time': str(datetime.now() - timedelta(hours=float(selected_values['collectionperiod']['static_select-action']['selected_option']['value']))),
        'end_time': datetime.now().isoformat(),
        'service_id': selected_values['service']['static_select-action']['selected_option']['value'],
        'description': selected_values['description']['plain_text_input-action']['value'],
        'duplicate': True
    }

    msg = ""
    try:
        apicollection_res = api_request(method='POST', 
            url=API_POST_API_COLLECTION, data=json.dumps(payload), headers=headers)

        if apicollection_res['error']:
            msg = f"Your collection {apicollectionname} creation failed. Error message: {apicollection_res['message']}"
        else:
            msg = f'Your collection {apicollectionname} created successfully'

    except Exception as e:
        logger.error(e)

    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")


@app.command("/listtestsuite")
def open_modal(ack, logger, body, client):
    # Acknowledge command request
    ack()
    views = json.load(open('./user-interface/modals/list-test-suite.json'))
    res = client.views_open(
        trigger_id=body["trigger_id"], view=json.dumps(views))
    logger.info(body)
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
    except Exception as e:
        logger.error(e)

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))

    views['blocks'][0]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))
    
    client.views_update(
        view_id= res['view']['id'], view= views 
    )



@app.view("list-test-suite")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user_id = body["user"]["id"]

    ack()
    workspace_id = selected_values['selectworkspace']['static_select-action']['selected_option']['value']
    page_no = selected_values['selectpage']['static_select-action']['selected_option']['value']

    try:
        testsuite_res = api_request(method='GET', url=API_GET_TEST_SUITE_BY_PAGE +
                                    f"{workspace_id}" + f"&page={page_no}&page_size=20&", headers=headers)
    except Exception as e:
        logger.error(e)

    testsuitedf = pd.json_normalize(testsuite_res['data'])
    testsuitedf = testsuitedf[[
        'name', 'description', 'collection.name', 'total_test_cases', 'execution_count']]
    md_table = testsuitedf.to_markdown()

    blocks = json.load(
        open('./user-interface/modals/list-test-suite-blocks.json'))
    blocks['blocks'][0]['text']['text'] = "```\n" + md_table + "```\n"
    client.chat_postMessage(channel=user_id, text="```\n" + md_table + "```\n")


@app.shortcut("execute_test_suite")
def open_modal(ack, shortcut, client, logger):
    # Acknowledge the shortcut request
    ack()
    views = json.load(open('./user-interface/modals/execute-test-suite.json'))
    res = client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
    except Exception as e:
        logger.error(e)
    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))

    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))

    client.views_update(
        view_id= res['view']['id'], view= views 
    )
    with open('./user-interface/modals/execute-test-suite.json', "w") as outfile:
        json.dump(views, outfile)


@app.action("select-workspace-execute-test-suite")
def update_modal(ack, body, client, logger):
   # Acknowledge the button request
    ack()

    workspace_id = body['actions'][0]['selected_option']['value']

    try:
        testsuite_res = api_request(method='GET',
                                    url=API_GET_TEST_SUITE_BY_PAGE_100_PER_ROW + f"{workspace_id}", headers=headers)
    except Exception as e:
        logger.error(e)

    testsuite_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, testsuite_res['data']))

    views = json.load(open('./user-interface/modals/execute-test-suite.json'))

    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, testsuite_list))

    client.views_update(  
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"], view=json.dumps(views))
    with open('./user-interface/modals/execute-test-suite.json', "w") as outfile:
        json.dump(views, outfile)


@app.view("execute-test-suite")
def handle_submission(ack, body, client, view, logger):

    selected_values = view["state"]["values"]
    user = body["user"]["id"]

    ack()
    testsuite_name = selected_values['selecttestsuite']['static_select-action']['selected_option']['value']
    payload = {
        'exec_type': 'custom',
        'testsuite_id': testsuite_name
    }

    msg = ""
    try:
        execute_res = api_request(method='POST', 
            url=API_TEST_SUITE_EXECUTE, data=json.dumps(payload), headers=headers)
        message = execute_res['message']
        msg = f'{message}'

    except Exception as e:
        logger.error(e)

    try:
        client.chat_postMessage(channel=user, text=msg)
    except e:
        logger.exception(f"Failed to post a message {e}")


@app.shortcut("export_test_cases")
def open_modal(ack, shortcut, client, logger):
    # Acknowledge the shortcut request
    ack()
    views = json.load(open('./user-interface/modals/export-test-cases.json'))
    res = client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
    except Exception as e:
        logger.error(e)

    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))



    views['blocks'][0]['elements'][0]['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))

    client.views_update(
        view_id= res['view']['id'], view= views 
    )
    with open('./user-interface/modals/export-test-cases.json', "w") as outfile:
        json.dump(views, outfile)


@app.action("select-workspace-export-test-cases")
def update_modal(ack, body, client, logger):
   # Acknowledge the button request
    ack()

    workspace_id = body['actions'][0]['selected_option']['value']

    try:
        testsuite_res = api_request(method='GET',
                                    url=API_GET_TEST_SUITE_BY_PAGE_100_PER_ROW + f"{workspace_id}", headers=headers)
    except Exception as e:
        logger.error(e)

    testsuite_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, testsuite_res['data']))

    views = json.load(open('./user-interface/modals/export-test-cases.json'))

    views['blocks'][1]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, testsuite_list))

    client.views_update(    
        view_id=body["view"]["id"],
        hash=body["view"]["hash"], view=json.dumps(views))

    with open('./user-interface/modals/export-test-cases.json', "w") as outfile:
        json.dump(views, outfile)


@app.view("export-test-cases")
def handle_submission(ack, body, client, view, logger):
    selected_values = view["state"]["values"]
    user = body["user"]["id"]
    print(selected_values)

    ack()
    testsuite_id = selected_values['selecttestsuite']['static_select-action']['selected_option']['value']

    try:
        testcases_res = api_request(method='GET',
                                    url=API_GET_TEST_CASES+f"{testsuite_id}", headers=headers)

        testcases_data = pd.json_normalize(
            testcases_res, record_path=['data'])
    except Exception as e:
        logger.error(e)

    client.files_upload(
        channels=user,
        initial_comment="Here's your test cases file :smile:",
        filetype="csv",
        filename="testcase.csv",
        content=testcases_data.to_string(index=False)
    )


@app.shortcut("list_api_collections")
def open_modal(ack, shortcut, client, logger):

    ack()

    views = json.load(
        open('./user-interface/modals/list-api-collections.json'))
    res= client.views_open(
        trigger_id=shortcut["trigger_id"], view=json.dumps(views))
    
    try:
        workspace_res = api_request(
            method='GET', url=API_GET_WORKSPACES, headers=headers)
    except Exception as e:
        logger.error(e)
    workspace_list = list(
        map(lambda x: {'name': x['name'], 'id': x['id']}, workspace_res['data']))

    views['blocks'][0]['element']['options'] = list(map(lambda x: {
        'text': {
            "type": "plain_text",
            "text": x['name']
        },
        'value': x['id']}, workspace_list))

    client.views_update(
        view_id= res['view']['id'], view= views 
    )
    with open('./user-interface/modals/list-api-collections.json', "w") as outfile:
        json.dump(views, outfile)


@app.view("list-api-collections")
def handle_submission(ack, body, client, view, logger):

    ack()
    selected_values = view["state"]["values"]
    user_id = body["user"]["id"]

    workspace_id = selected_values['selectworkspace']['static_select-action']['selected_option']['value']
    page_no = selected_values['selectpage']['static_select-action']['selected_option']['value']

    try:
        apicollec_res = api_request(method='GET', url=API_GET_API_COLLECTIONS +
                                    f"{workspace_id}" + f"&page={page_no}&page_size=20&", headers=headers)
    except Exception as e:
        logger.error(e)
    apicollecdf = pd.json_normalize(apicollec_res['data'])
    apicollecdf = apicollecdf[['name', 'start_time',
                               'end_time', 'api_count', 'created_by.firstname']]
    md_table = apicollecdf.to_markdown()

    blocks = json.load(
        open('./user-interface/modals/list-test-suite-blocks.json'))
    blocks['blocks'][0]['text']['text'] = "```\n" + md_table + "```\n"

    client.chat_postMessage(channel=user_id, text="```\n" + md_table + "```\n")


@app.event("app_home_opened")
def handle_app_home_opened_events(body, logger, client):

    client.views_publish(
        user_id=body['event']['user'], view=json.dumps(json.load(open('./user-interface/modals/app-home.json'))))


flask_app = Flask(__name__)
cors = CORS(flask_app)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/install", methods=["GET"])
def oauth_start():
    state = state_store.issue()

    url = authorize_url_generator.generate(state)
    return f'<a href="{url}">' \
           f'<img alt=""Add to Slack"" height="40" width="139" src="https://platform.slack-edge.com/img/add_to_slack.png" srcset="https://platform.slack-edge.com/img/add_to_slack.png 1x, https://platform.slack-edge.com/img/add_to_slack@2x.png 2x" /></a>'

@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_callback():
    # Retrieve the auth code and state from the request params
    if "code" in request.args:
        # Verify the state parameter
        if request.args["state"]:
            state = request.args["state"]
            client = WebClient()  # no prepared token needed for this

            # Complete the installation by calling oauth.v2.access API method
            oauth_response = client.oauth_v2_access(
                client_id= slack_client_id,
                client_secret=slack_client_secret,
                redirect_uri=f"{tyke_slack_url}/slack/oauth_redirect",
                code=request.args["code"]
            )

            installed_enterprise = oauth_response.get("enterprise", {})
            is_enterprise_install = oauth_response.get("is_enterprise_install")
            installed_team = oauth_response.get("team", {})
            installer = oauth_response.get("authed_user", {})
            incoming_webhook = oauth_response.get("incoming_webhook", {})
            bot_token = oauth_response.get("access_token")

            if installed_enterprise is None:
                installed_enterprise = {'id': None, 'name': None}
            # NOTE: oauth.v2.access doesn't include bot_id in response
            bot_id = None
            enterprise_url = None
            if bot_token is not None:
                auth_test = client.auth_test(token=bot_token)
                bot_id = auth_test["bot_id"]
                if is_enterprise_install is True:
                    enterprise_url = auth_test.get("url")

       
            get_row = ExecuteQuery(
                "SELECT id FROM tyke.user WHERE uuid='{}'".format(state))
      

            insert_query="INSERT INTO tyke.slack_users ( user_id, app_id, enterprise_id, enterprise_url, team_id, team_name, bot_token, bot_id, bot_user_id, slack_user_id, slack_user_token, installed_at) VALUES( {}, '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}');".format(
                get_row[0][0],
                oauth_response.get("app_id"),
                installed_enterprise.get("id"),
                enterprise_url,
                installed_team.get("id"),
                installed_team.get("name"),
                bot_token,
                bot_id,
                oauth_response.get("bot_user_id"),
                installer.get("id"),
                installer.get("access_token"),
                time.time()
            )
            update_row = ExecuteQuery(insert_query)

            installation = Installation(
                app_id=oauth_response.get("app_id"),
                enterprise_id=installed_enterprise.get("id"),
                enterprise_name=installed_enterprise.get("name"),
                enterprise_url=enterprise_url,
                team_id=installed_team.get("id"),
                team_name=installed_team.get("name"),
                bot_token=bot_token,
                bot_id=bot_id,
                bot_user_id=oauth_response.get("bot_user_id"),
                bot_scopes=oauth_response.get(
                    "scope"),  # comma-separated string
                user_id=installer.get("id"),
                user_token=installer.get("access_token"),
                user_scopes=installer.get("scope"),  # comma-separated string
                incoming_webhook_url=incoming_webhook.get("url"),
                incoming_webhook_channel=incoming_webhook.get("channel"),
                incoming_webhook_channel_id=incoming_webhook.get("channel_id"),
                incoming_webhook_configuration_url=incoming_webhook.get(
                    "configuration_url"),
                is_enterprise_install= is_enterprise_install,
                token_type= oauth_response.get("token_type"),
                custom_values={
                'tyke_user_token':'',
                'user_id': state
                }
            )
            print(installation)
            # Store the installation
            installation_store.save(installation)

            return redirect(tyke_ui_url+"/slack/success")
        else:
            return make_response(f"Try the installation again (the state value is already expired)", 400)

    error = request.args["error"] if "error" in request.args else ""
    return make_response(f"Something is wrong with the installation (error: {error})", 400)

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

@flask_app.route("/slack/oauth_post", methods=["POST"])
def oauth_post():
    # print("Reached")
    body = request.json
    try:
        get_user = ExecuteQuery(
                "SELECT id FROM tyke.user WHERE uuid='{}'".format(body['user']))
      

        get_row = ExecuteQuery(
                f"SELECT team_id, slack_user_id, enterprise_id FROM tyke.slack_users WHERE user_id='{get_user[0][0]}'")
        
        installation = installation_store.find_installation(team_id=get_row[0][0], user_id= get_row[0][1], enterprise_id=None)
        installation.custom_values['tyke_user_token']=f"Bearer {body['access_token']}"
        installation_store.save(installation) 
        return make_response("Success", 201)       
    except Exception as e:
        return make_response("Error:{e}", 400)


if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port= SLACK_API_PORT)
    #flask_app.run(host='0.0.0.0', port=SLACK_API_PORT, ssl_context=("/etc/ssl/tyke.ai.crt", "/etc/ssl/tyke.ai.key") )

# Start your app
