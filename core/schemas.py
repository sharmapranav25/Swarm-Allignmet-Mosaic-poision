"""Strict assessment schemas shared by the ticketing defenders."""

def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

TEXT = {'type': 'string', 'minLength': 1}

def delivery_schema():
    return obj({'action': {'type':'string','enum':['release','deploy_charlatan']},
                'profile': TEXT, 'reason': TEXT, 'assembly_assessment': TEXT})
