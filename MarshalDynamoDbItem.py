import json
from typing import List, Optional


class MarshalItem:
    """A class to convert a python dictionary to a DynamoDB marshalled item

    A class to convert a dictionary to a DynamoDB marshalled Item.
    Since the attributes in my data object should never exceed 3 levels of nesting,
    this class caps the item level nesting to 3 levels. This is done to prevent
    memory issues from the recursive call.

    >>> sample = MarshalItem({'item': {'dict': {'str': 's', 'int': 1, 'float': 1.2, 'bool': True}}})
    >>> sample.marshalled_item
    {'item': {'M': {'dict': {'M': {'str': {'S': 's'}, 'int': {'N': 1}, 'float': {'N': 1.2}, 'bool': {'BOOL': True}}}}}}

    >>> MarshalItem({'1': {'2': {'3': {'4': {'throw': 'ex'}}}}})
    Traceback (most recent call last):
    ...
    Exception: Item key, '1' exceeds maximum nesting levels of 3

    >>> MarshalItem(1)
    Traceback (most recent call last):
    ...
    ValueError: Expected `class <dict>`, received <class 'int'>

    >>> MarshalItem({'1': '2'}, 0)
    Traceback (most recent call last):
    ...
    ValueError: Expected an integer between 1 and 10 inclusive for max_nesting_level, received 0

    Attributes
    ----------
    marshalled_item: dict
      DynamoDB marshalled item from the item passed into the constructor.
    attribute_levels: dict
      The number of nested levels for each attribute in the item.
      0 if the item is not a dictionary.
    """
    DDB_PRIMITIVES_MAP = {
        str: 'S',  # DynamoDB String Attribute Type
        int: 'N',  # DynamoDB Number Attribute Type
        float: 'N',  # DynamoDB Number Attribute Type
        bool: 'BOOL',  # DynamoDB Boolean Attribute Type
        dict: 'M',  # DynamoDB Dictionary Attribute Type
        list: 'L',  # DynamoDB List Attribute Type
    }

    def __init__(self, ddb_item: dict, max_nesting_level: int = 3):
        """Creates Marshalled Item from the ddb_item.

        Parameters
        ----------
        ddb_item: dict
          The data to be converted to a DynamoDB marshalled item.
        max_nesting_levels: int
          The maximum nested dictionaries allowed for any top-level item key.
        """
        if type(ddb_item) != dict:
            raise ValueError(f'Expected `class <dict>`, received {type(ddb_item)}')
        if (
            type(max_nesting_level) != int
            or max_nesting_level > 10
            or max_nesting_level < 1
        ):
            raise ValueError(
                f'Expected an integer between 1 and 10 inclusive for max_nesting_level, received {max_nesting_level}'
            )

        self.max_nesting_level = max_nesting_level
        self.__attribute_levels = {key: 0 for key in ddb_item.keys()}
        self.__marshalled_item = self.__marshal_object(ddb_item)

    @property
    def marshalled_item(self) -> dict:
        return self.__marshalled_item

    @property
    def attribute_levels(self) -> dict:
        """Returns the number of nested levels for each top-level item attribute.

        Reverse sorts based on an attributes number of levels
        """
        sorted_count = {
            k: v
            for k, v in sorted(
                self.__attribute_levels.items(), key=lambda item: -item[1]
            )
        }
        return sorted_count

    def __repr__(self):
        return json.dumps(self.__marshalled_item, indent=4)

    def __marshal_object(self, ddb_item: dict, top_key: Optional[str] = None):
        """Convert dicitonary into DynamoDB marshalled item

        Parameters
        ----------
        ddb_item: any
          The data to be converted to a DynamoDB marshalled item.
        top_key: str | None
          Top Level item key provided when we need to increment the nesting level

        Returns
        -------
        marshalled_item: dict
          DynamoDB Marshalled Item.
        """

        if top_key:
            if self.__attribute_levels[top_key] < self.max_nesting_level:
                self.__attribute_levels[top_key] += 1
            else:
                raise Exception(
                    f'Item key, \'{top_key}\' exceeds maximum nesting levels of {self.max_nesting_level}'
                )

        marshalled_item = {}

        if type(ddb_item) in [str, int, float, bool]:
            marshalled_type = self.DDB_PRIMITIVES_MAP[type(ddb_item)]
            marshalled_item[marshalled_type] = (
                ddb_item if marshalled_type != 'N' else str(ddb_item)
            )
            return marshalled_item

        for key, value in ddb_item.items():
            marshalled_type = self.DDB_PRIMITIVES_MAP[type(value)]
            if marshalled_type in 'L':
                marshalled_item[key] = {marshalled_type: []}
                for list_item in value:
                    marshalled_item[key][marshalled_type].append(
                        self.__marshal_object(list_item)
                    )
            elif marshalled_type in 'M':
                top_level_attr = top_key if top_key else key
                marshalled_item[key] = {
                    marshalled_type: self.__marshal_object(
                        value, top_key=top_level_attr
                    )
                }
            else:
                marshalled_item[key] = { marshalled_type: value}

        return marshalled_item