import os


def pytest_configure(config):
    os._called_from_test = True


def pytest_unconfigure(config):
    del os._called_from_test
