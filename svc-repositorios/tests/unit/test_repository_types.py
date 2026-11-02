import unittest

from app.domain.entities.repository_types import StatusEnum, TipoRepositorioEnum


class RepositoryTypeTests(unittest.TestCase):
    def test_repository_types_keep_api_values(self):
        self.assertEqual(
            [item.value for item in TipoRepositorioEnum],
            ["local", "cdn", "gdrive"],
        )

    def test_status_values_remain_unchanged(self):
        self.assertEqual([item.value for item in StatusEnum], ["ativo", "inativo", "erro"])


if __name__ == "__main__":
    unittest.main()
