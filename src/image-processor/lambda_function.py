import json
import boto3
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

s3 = boto3.client('s3')
sns = boto3.client('sns')

# Placeholders kept intact for repository safety[cite: 2]
PROCESSED_BUCKET = 'nimbusflow-processed-<yoursuffix>' 
SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:ACCOUNT_ID:nimbusflow-image-notifications' 
MAX_WIDTH = 800
MAX_HEIGHT = 800
WATERMARK_TEXT = 'nimbusflow'

def lambda_handler(event, context):
    print(json.dumps(event))
    for record in event['Records']:
        source_bucket = record['s3']['bucket']['name']
        source_key = record['s3']['object']['key'].replace('+', ' ')
        try:
            response = s3.get_object(Bucket=source_bucket, Key=source_key)
            image_bytes = response['Body'].read()
            image = Image.open(BytesIO(image_bytes))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            image.thumbnail((MAX_WIDTH, MAX_HEIGHT))
            draw = ImageDraw.Draw(image)
            font = ImageFont.load_default()
            text_bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            padding = 10
            position = (
                image.width - text_width - padding,
                image.height - text_height - padding
            )
            draw.text(position, WATERMARK_TEXT, fill=(255, 255, 255), font=font)
            output_buffer = BytesIO()
            image.save(output_buffer, format='JPEG', quality=85)
            output_buffer.seek(0)
            filename = os.path.basename(source_key)
            output_key = f'processed-{filename}'
            s3.put_object(
                Bucket=PROCESSED_BUCKET,
                Key=output_key,
                Body=output_buffer,
                ContentType='image/jpeg'
            )
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='Image processed',
                Message=json.dumps({
                    'sourceBucket': source_bucket,
                    'sourceKey': source_key,
                    'processedBucket': PROCESSED_BUCKET,
                    'processedKey': output_key
                })
            )
            print(f'Successfully processed {source_key} -> {output_key}')
        except Exception as e:
            print(f'Error processing {source_key}: {str(e)}')
            raise e
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Processing complete'})
    }
