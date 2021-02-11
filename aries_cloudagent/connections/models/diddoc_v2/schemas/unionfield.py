"""
DID Document field Schema.

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

from marshmallow import fields
from marshmallow.exceptions import ValidationError


class ListOrStringField(fields.Field):
    """
    List or String field for Marshmallow
    """

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str) or isinstance(value, list):
            return value
        else:
            raise ValidationError("Field should be str or list")


class ListOrStringOrDictField(fields.Field):
    """
    List, String or Dict field for Marshmallow
    """

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str) or isinstance(value, list) or isinstance(value, dict):
            return value
        else:
            raise ValidationError("Field should be str, list or dict")


class PublicKeyField(fields.Field):
    """
    Public Key field for Marshmallow
    """

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""
        if isinstance(value, list):
            for idx, val in enumerate(value):
                if not isinstance(val, str):
                    value[idx] = val.serialize()
            return value
        else:
            return "".join(str(d) for d in value)

    def _deserialize(self, value, attr, data, **kwargs):
        from ..publickey import PublicKey

        if isinstance(value, list):
            for idx, val in enumerate(value):
                if isinstance(val, dict):
                    if (
                        (not val.get("id"))
                        or (not val.get("type"))
                        or (not val.get("controller"))
                    ):
                        raise ValidationError(
                            "VerificationMethod Map must have id, type & controler"
                        )
                    value[idx] = PublicKey(**val)
            return value
        else:
            raise ValidationError("Field should be str, list or dict")
