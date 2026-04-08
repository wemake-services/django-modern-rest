import uuid

from dirty_equals import IsStr
from faker import Faker

from dmr.plugins.msgspec import MsgspecSerializer


def test_to_python_complex_values(faker: Faker) -> None:
    """Ensures complex values are converted to primitives."""
    request_data = {
        'uid': uuid.uuid4(),
        'birthday': faker.date_object(),
        'wakeup_at': faker.time_object(),
    }

    primitives = MsgspecSerializer.to_python(request_data)

    assert primitives == {
        'uid': str(request_data['uid']),
        'birthday': IsStr(),
        'wakeup_at': IsStr(),
    }
