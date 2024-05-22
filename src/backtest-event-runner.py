import boto3

# Create SQS client
sqs = boto3.client('sqs', region_name='us-east-1')

queue_url = 'https://sqs.us-east-1.amazonaws.com/716418748259/baseball-backtest'

# Send message to SQS queue
response = sqs.send_message(
    QueueUrl=queue_url,
    DelaySeconds=10,
    MessageAttributes={
        'year': {
            'DataType': 'String',
            'StringValue': '2023'
        },
        'team_name': {
            'DataType': 'String',
            'StringValue': 'Philadelphia Phillies'
        },
        'team_id': {
            'DataType': 'String',
            'StringValue': '143'
        }
    },
    MessageBody=(
        'Phils'
        '2023'
    )

)

print(response['MessageId'])
