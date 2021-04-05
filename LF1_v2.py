import json
import boto3
import os
import sys
import uuid
import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime
from elasticsearch import Elasticsearch, RequestsHttpConnection
import hashlib
from requests.auth import HTTPBasicAuth

host2 = 'search-photos2-3kvhl7jjubuo2lmnpuavdyfx2q.us-east-1.es.amazonaws.com'
host='https://search-photos2-3kvhl7jjubuo2lmnpuavdyfx2q.us-east-1.es.amazonaws.com'
REGION = 'us-east-1'

def get_url(index, type):
    url = host + index + '/' + type
    return url


def lambda_handler(event, context):
    print("EVENT --- {}".format(json.dumps(event)))

    headers = { "Content-Type": "application/json" }
    rek = boto3.client('rekognition')
    
    s3 = boto3.client('s3')
    
    # get the image information from S3
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        size = record['s3']['object']['size'] # up to 5MB
        
        s3response = s3.head_object(
                                        Bucket=bucket,
                                        Key=key,
                                        )
        
        print("s3response --- {}".format(s3response))
        # print("Metadata label --- {}".format(s3response['Metadata']['custom-labels']))
        
        labelStr = s3response['Metadata']['custom-labels']
        print("Metadata label --- {}".format(labelStr))
        A = labelStr.split(",")
        
        print(A)
        # detect the labels of current image
        labels = rek.detect_labels(
            Image={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': key
                }
            },
            MaxLabels=10
        )
            
        print("IMAGE LABELS --- {}".format(labels['Labels']))
        
        # prepare JSON object
        obj = {}
        obj['objectKey'] = key
        obj["bucket"] = bucket
        obj["createdTimestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obj["labels"] = []
            
        for label in labels['Labels']:
            obj["labels"].append(label['Name'])
            
        for label in A:
            obj["labels"].append(label)
        
        print("JSON OBJECT --- {}".format(obj))
        
        print("Starting to add Elastic Index")

        
        #_____________________________________________________________________
        obj = json.dumps(obj)
        str_id = "{} {}".format(bucket, key)
        doc_id = hashlib.sha1(bytes(str_id, encoding="ascii")).hexdigest()
        path = '/photos/_doc/{}'.format(doc_id)
        auth = HTTPBasicAuth('root', 'CloudComputing21Spring!')
        service = 'es'
        credentials = boto3.Session().get_credentials()
        print("putting index")
        response = requests.put(host + path, auth=auth, data=obj, headers=headers)
        print("status :", response)

    return {
        'statusCode': 200,
        'body': json.dumps("Image labels have been successfully detected!"),
        'headers': {
            'Access-Control-Allow-Headers' : 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,PUT',
            'Content-Type': 'application/json'
        }
    }

# Add elastic search indeices after DB has been added
def addElasticIndex(obj):
    print(obj)

    region = "us-east-1"
    service = "es"
    credentials = boto3.Session().get_credentials()
    access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
    awsauth = AWS4Auth(access_key, secret_key, region, service, session_token=credentials.token)
    
    print(awsauth)

    es = Elasticsearch(
        hosts = [{'host': host2, 'port': 443}],
        use_ssl = True,
        http_auth = awsauth,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    
    print("try to connect es :")
    r = es.index(index="photos", doc_type="photo", id = obj['objectKey'], body=obj)
    print("response: ", r)

def indexData(photo,bucket,labels):

    path = 'photos/photo'
    region = 'us-east-1' 
    
    
    service = 'es'
    credentials = boto3.Session().get_credentials()
   
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    # es = Elasticsearch(
    #     hosts = [{'host': host, 'port': 443}],
    #     http_auth = awsauth,
    #     use_ssl = True,
    #     verify_certs = True,
    #     connection_class = RequestsHttpConnection
    # )
    
    date_timestamp = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
    url = host + path
    print("date", date_timestamp)
    headers = {'Content-Type':'application/json'}
    
    document = {
        'objectKey': photo,
        'bucket': bucket,
        'createdTimestamp': date_timestamp,
        'labels': labels
    }
    print("doc: ", document)
    
    # es.index(index="photos", doc_type="_doc", id=date_timestamp, body=document)
    r = requests.post(url, data=json.dumps(document), headers=headers, auth=awsauth)
    print("status :", r)
    
    # print(es.get(index="photos", doc_type="_doc", id=date_timestamp))
    print("elasticsearch: ", r.text)
    

def indexIntoES(document):
    index = 'photos'
    type = 'lambda-type'
    url = host + '/' + index + '/' + type
    service = 'es'
    region = 'us-east-1'
    headers = { "Content-Type": "application/json" }
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)
    r = requests.post(url, auth=awsauth, json=document, headers=headers)
    
    print("response: ",r)
    return r
