from typing import Annotated

import msgspec


class UserModel(msgspec.Struct):
    email: Annotated[
        str,
        msgspec.Meta(extra_json_schema={'example': 'user@example.com'}),
    ]
