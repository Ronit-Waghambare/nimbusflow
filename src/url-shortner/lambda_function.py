import json
import boto3
import string
import random
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('nimbusflow-urls')

def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def lambda_handler(event, context):
    print(json.dumps(event))  # temporary debug line — still present, not removed
    http_method = event['requestContext']['http']['method']

    if http_method == 'POST':
        try:
            body = json.loads(event.get('body', '{}'))
            original_url = body.get('url')

            if not original_url:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Missing "url" in request body'})
                }

            short_code = generate_short_code()

            table.put_item(
                Item={'shortCode': short_code, 'originalUrl': original_url}
            )

            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'shortCode': short_code,
                    'shortUrl': f'/redirect/{short_code}',
                    'originalUrl': original_url
                })
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }

    elif http_method == 'GET':
        try:
            short_code = event.get('pathParameters', {}).get('shortCode')

            if not short_code:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Missing shortCode in path'})
                }

            response = table.get_item(Key={'shortCode': short_code})
            item = response.get('Item')

            if not item:
                return {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Short code not found'})
                }

            return {
                'statusCode': 302,
                'headers': {'Location': item['originalUrl']},
                'body': ''
            }
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': str(e)})
            }

    return {
        'statusCode': 405,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'error': 'Method not allowed'})
    }
