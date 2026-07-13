import json
import boto3

ec2 = boto3.client('ec2')

TAG_KEY = 'AutoStop'
TAG_VALUE = 'true' # Verified lowercase match[cite: 2]

def lambda_handler(event, context):
    print(json.dumps(event))
    
    action = event.get('action')
    
    if action not in ('stop', 'start'):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': f'Invalid or missing action: {action}'})
        }
    
    response = ec2.describe_instances(
        Filters=[
            {'Name': f'tag:{TAG_KEY}', 'Values': [TAG_VALUE]}
        ]
    )
    
    instance_ids = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])
    
    if not instance_ids:
        print('No tagged instances found.')
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No tagged instances found', 'action': action})
        }
    
    print(f'Found instances: {instance_ids}')
    
    if action == 'stop':
        ec2.stop_instances(InstanceIds=instance_ids)
        print(f'Stopping: {instance_ids}')
    elif action == 'start':
        ec2.start_instances(InstanceIds=instance_ids)
        print(f'Starting: {instance_ids}')
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'{action} triggered', 'instances': instance_ids})
    }
