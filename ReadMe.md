# DynamoDB Data Marshalling

If you're familiar with DynamoDB, you that transforming your data into DynamoDB Marshalled Data can be cumbersome.

The following object:
```json
{
  "pk": "pk",
  "sk": "sk",
  "obj": {
    "attr1": "1",
    "attr2": [1, 2],
    "attr3": {
      "hello": "world"
    },
    "attr4": true
  },
  "ddbList": [
    1.2,
    "2",
    { "hello": "moon" }
  ]
}
```

must be "marshalled" to the following before being posted to DynamoDB:
```json
{
   "ddbList": {
       "L": [
           {"N": "1.2"},
           {"S": "2"},
           {"hello": {"S": "moon"}}
        ]
    },
    "obj": {
        "M": {
            "attr1": {"S": "1"},
            "attr2": {"L": [{"N": "1"}, {"N": "2"}]},
            "attr3": {"M": {"hello": {"S": "world"}}},
            "attr4": {"BOOL": true}
        }
     },
    "pk": {"S": "pk"},
    "sk": {"S": "sk"}
}
```

Luckily for us developers, both `boto3` and the `aws-sdk` provide higher level clients that handle the data marshalling and unmarshalling for us, right?

Kinda. While the `aws-sdk` offers the [DocumentClient](https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/DynamoDB/DocumentClient.html]), which covers a lot of the necessary functionality, `boto3`'s [DynamoDB Table](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#table) has more gaps than I would like. Recently at work, I needed to use DynamoDB Transactional Writes on 5 to 10 items at a time, but we use a `python` stack and `boto3`'s [Table](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/dynamodb.html#table) does not have a higher level method for transactional writes.

Wrather that painstakingly marshalling my items, I created a python class to handle it for me.

Why a class and not a function? I wanted to manage state at the item level. Since I implemented this functionality with recursion and I know that my items should never be too deeply nested, I can place a max recursion limit on my class and as soon as any of the top level attributes exceeds that limit, I can raise an exception. Additionally, I liked the idea of having some stateful info about my DynamoDB item, like the number of nested levels for each top-level item attribute.

---
## Usage
Using the class should be extremely straight forward -- the constructor only accepts two arguments:
1. `ddb_item`: This is the `python` dictionary that needs to be marshalled into a DynamoDB item.
2. `max_nesting_levels`: This argument sets the maximum number of nesting levels for each top-level item attribute. This number is defaulted to 3 and capped at 10.
    * Realistically, If an attribute in your DDB Item has more than 3 or 4 levels of nested objects, consider splitting this up.

### Examples
```python
sample = {
  'pk': 'pk',
  'sk': 'sk',
  'obj': {
    'attr1': '1',
    'attr2': [1, 2],
    'attr3': {'hello': {'1': 'world'}},
    'attr4': True
  },
  'ddbList': [1.2, '2', { 'hello': 'moon' }]
}

marshalled_data = MarshalItem(sample)
print(f'Marshalled Item: {marshalled_data.marshalled_item}')
print(f'Nested Attribute Levels: {marshalled_data.attribute_levels}')
```

Output:
```bash
Marshalled Item: {
  'pk': {'S': 'pk'},
  'sk': {'S': 'sk'},
  'obj': {
    'M': {
      'attr1': {'S': '1'},
      'attr2': {'L': [{'N': '1'}, {'N': '2'}]},
      'attr3': {'M': {'hello': {'S': 'world'}}},
      'attr4': {'BOOL': True}
    }
  },
  'ddbList': {'L': [{'N': '1.2'}, {'S': '2'}, {'hello': {'S': 'moon'}}]}}

Nested Attribute Levels: {'obj': 3, 'pk': 0, 'sk': 0, 'ddbList': 0}
```