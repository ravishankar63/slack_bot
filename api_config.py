import os 
URL= os.environ['TYKE_API']
API_HEALTH=f"{URL}/api/health"
API_GET_WORKSPACES = f"{URL}/api/workspace?mini=true&" 
API_GET_API_COLLECTIONS = f"{URL}/api/collection?workspace_id="
API_GET_TAGS = f"{URL}/api/tag?resource_type=testsuite&"
API_POST_TEST_SUITE = f"{URL}/api/testsuite" 
API_GET_SERVICES= f"{URL}/api/service?workspace_id="
API_POST_API_COLLECTION= f"{URL}/api/collection"
API_GET_TEST_SUITE_BY_PAGE=f"{URL}/api/testsuite?workspace_id="
API_GET_TEST_SUITE_BY_PAGE_100_PER_ROW=f"{URL}/api/testsuite?page=1&page_size=20&workspace_id="
API_GET_API_COLLECTIONS_BY_PAGE= f"{URL}/api/collection?workspace_id="
API_TEST_SUITE_EXECUTE=f"{URL}/api/testsuite/execute"
API_GET_TEST_CASES=f"{URL}/api/testcase?testsuite_id="