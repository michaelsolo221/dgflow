class MockState(dict):
    pass


class MockCallbackContext:
    def __init__(self, state=None):
        self.state = MockState(state or {})
