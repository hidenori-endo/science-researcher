import unittest

from science_researcher.provider_http import OpenAICompatibleChatProvider


class ProviderConstructionTests(unittest.TestCase):
    def test_provider_builds_without_optional_dependencies(self) -> None:
        provider = OpenAICompatibleChatProvider(
            base_url="http://localhost:9999/v1",
            model="test-model",
        )
        self.assertEqual(provider.model, "test-model")
        self.assertEqual(provider.base_url, "http://localhost:9999/v1")


if __name__ == "__main__":
    unittest.main()
