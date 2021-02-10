"""
DID Document Service classes.

Copyright 2021 Sicpa

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from marshmallow import Schema, fields, post_load, post_dump, pre_load, validate
from .unionfield import ListOrStringField, ListOrStringOrDictField
from ...resolver.did import DID_PATTERN
import re

DID_PATTERN = re.compile("{}#[a-zA-Z0-9._-]+".format(DID_PATTERN.pattern))


class ServiceSchema(Schema):
    """
    Based on https://w3c.github.io/did-core/#service-properties

    Example:

    {"id": "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-3",
     "type": "one",
     "priority": 1,

     "recipientKeys": [
         "did:sov:LjgpST2rjsoxYegQDRm7EL#keys-1"],
     "routingKeys": ["did:sov:LjgpST2rjsoxYegQDRm7EL#keys-4"],
     "serviceEndpoint": "LjgpST2rjsoxYegQDRm7EL;2"}
    """

    id = fields.Str(required=True, validate=validate.Regexp(DID_PATTERN))
    type = ListOrStringField(required=True)
    serviceEndpoint = ListOrStringOrDictField(required=True)
    priority = fields.Int(validate=validate.Range(min=0))
    recipientKeys = fields.List(fields.Str(validate=validate.Regexp(DID_PATTERN)))
    routingKeys = fields.List(fields.Str(validate=validate.Regexp(DID_PATTERN)))

    @post_load
    def make_service(self, data, **kwargs):
        from ..service import Service

        service = Service(**data)
        return service
