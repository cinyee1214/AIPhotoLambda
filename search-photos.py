import json
import boto3
import os
import sys
import uuid
import time
import requests
from requests_aws4auth import AWS4Auth
from requests.auth import HTTPBasicAuth

REGION = 'us-east-1'
service = "es"
credentials = boto3.Session().get_credentials()
access_key = os.environ.get('AWS_ACCESS_KEY_ID')
secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
awsauth = AWS4Auth(access_key, secret_key, REGION, service, session_token=credentials.token)

def lambda_handler(event, context):
	# recieve from API Gateway
	print("EVENT --- {}".format(json.dumps(event)))
	
	headers = { "Content-Type": "application/json" }
	lex = boto3.client('lex-runtime')

	query = event["queryStringParameters"]["q"]
	print("query --- {}".format(query))
	
	lex_response = lex.post_text(
		botName='photolex',
		botAlias='Prod',
		userId='admin',
		inputText=query
	)
	
	print("LEX RESPONSE --- {}".format(json.dumps(lex_response)))

	slots = lex_response['slots']
	print(slots)

	img_list = []
	for i, tag in slots.items():
		if tag:
			print(tag)
			searchData = get_photos_from_es(tag)
			print("es RESPONSE --- {}".format(searchData))
			
			for photo in searchData:
				img_url = 'https://b2-photo-bucket.s3.amazonaws.com/' + photo
				print(img_url)
				img_list.append(img_url)

	if img_list:
		img_list = list(set(img_list))
		print(img_list)
        
		return {
			'statusCode': 200,
			'headers': {
				'Access-Control-Allow-Headers' : 'Content-Type',
	            'Access-Control-Allow-Origin': '*',
	            'Access-Control-Allow-Methods': 'OPTIONS,GET',
	            'Content-Type': 'application/json'
			},
			'body': json.dumps(img_list)
		}
	return {
			'statusCode': 200,
			'headers': {
				'Access-Control-Allow-Headers' : 'Content-Type',
	            'Access-Control-Allow-Origin': '*',
	            'Access-Control-Allow-Methods': 'OPTIONS,GET',
	            'Content-Type': 'application/json'
			},
			'body': json.dumps("No such photos.")
		}


def es_search(criteria):
    URL = 'https://search-photos2-3kvhl7jjubuo2lmnpuavdyfx2q.us-east-1.es.amazonaws.com/photos/{}'
    url = URL.format('_search')
    return send_signed('get', url, body=json.dumps(criteria))

def get_photos_from_es(category):
    """Given a category, return a list of photo ids in that category"""
    criteria = {
        "query": { "match": {'labels': category} },
    }
    content = es_search(criteria)
    content = json.loads(content)
    return [rstr['_source']['objectKey'] for rstr in content['hits']['hits']]
    

def send_signed(method, url, service='es', region='us-east-1', body=None):
    credentials = boto3.Session().get_credentials()
    auth = HTTPBasicAuth('root', 'CloudComputing21Spring!')
	
    fn = getattr(requests, method)
    if body and not body.endswith("\n"):
        body += "\n"
    try:
        response = fn(url, auth=auth, data=body, 
                        headers={"Content-Type":"application/json"})
        if response.status_code != 200:
            raise Exception("{} failed with status code {}".format(method.upper(), response.status_code))
        return response.content
    except Exception:
        raise