import os
import tempfile
import unittest
import subprocess
import shutil
from unittest.mock import patch, MagicMock, ANY
from script import get_git_dependencies, generate_mermaid_graph, visualize_graph

class TestGitDependencies(unittest.TestCase):

    def setUp(self):
        # Создаем временную директорию для репозитория
        self.test_dir = tempfile.mkdtemp()
        self.git_dir = os.path.join(self.test_dir, '.git')

        # Инициализируем новый Git-репозиторий
        subprocess.run(['git', 'init', self.test_dir], check=True)
        os.chmod(self.git_dir, 0o755)

        # Создаем несколько файлов и коммитов
        self.create_file_and_commit("file1.txt", "Добавить file1")
        self.create_file_and_commit("file2.txt", "Добавить file2")

    def tearDown(self):
        # Снимаем ограничения на доступ к файлам/папкам
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for file in files:
                file_path = os.path.join(root, file)
                os.chmod(file_path, 0o777)  # Устанавливаем полный доступ
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                os.chmod(dir_path, 0o777)  # Устанавливаем полный доступ
        os.chmod(self.test_dir, 0o777)  # Устанавливаем полный доступ для корневой директории

        # Удаляем временную директорию
        shutil.rmtree(self.test_dir)


    def create_file_and_commit(self, filename, message):
        # Создаем файл и добавляем его в Git
        with open(os.path.join(self.test_dir, filename), 'w') as f:
            f.write(f"Содержимое файла {filename}\n")

        subprocess.run(['git', 'add', filename], cwd=self.test_dir, check=True)
        subprocess.run(['git', 'commit', '-m', message], cwd=self.test_dir, check=True)

    def test_get_git_dependencies(self):
        # Вызываем функцию для анализа зависимостей
        result = get_git_dependencies(self.test_dir)

        # Извлекаем реальные коммиты и их файлы
        commit_hashes = subprocess.check_output(
            ["git", "log", "--format=%H"], cwd=self.test_dir
        ).decode().strip().split("\n")
        commit_hashes.reverse()  # Порядок должен соответствовать порядку добавления коммитов

        # Ожидаемые зависимости
        expected_result = {
            commit_hashes[0]: ["file1.txt"],
            commit_hashes[1]: ["file1.txt", "file2.txt"],
        }

        # Проверяем, что результат совпадает
        self.assertEqual(result, expected_result)


    @patch("os.path.isdir", side_effect=lambda path: False if ".git" in path else True)
    @patch("os.listdir", return_value=["ab", "cd"])
    def test_get_git_dependencies_error(self, mock_listdir, mock_isdir):
        with self.assertRaises(ValueError):
            get_git_dependencies(self.test_dir)



class TestGenerateMermaidGraph(unittest.TestCase):
    def test_generate_mermaid_graph(self):
        """Тест генерации Mermaid-графа."""
        dependencies = {
            "commit1": ["file1.txt", "file2.txt"],
            "commit2": ["file3.txt"],
        }
        expected = (
            "graph TD\n"
            "    commit1:::commit\n"
            "    commit1 --> file1.txt\n"
            "    commit1 --> file2.txt\n"
            "    commit2:::commit\n"
            "    commit2 --> file3.txt"
        )
        result = generate_mermaid_graph(dependencies)
        self.assertEqual(result, expected)


class TestVisualizeGraph(unittest.TestCase):
    @patch("script.NamedTemporaryFile", autospec=True)
    @patch("os.remove", autospec=True)
    @patch("subprocess.run", autospec=True)
    def test_visualize_graph_success(self, mock_run, mock_remove, mock_tempfile):
        """Тест успешной визуализации графа."""
        visualizer_path = "C:\\Users\\komko\\AppData\\Roaming\\npm\\mmdc.cmd"
        mermaid_code = "graph TD\ncommit1:::commit\ncommit1 --> file1.txt\n"

        # Настраиваем mock для временного файла
        temp_file_mock = MagicMock()
        temp_file_mock.name = "tempfile.mmd"
        mock_tempfile.return_value.__enter__.return_value = temp_file_mock

        visualize_graph(mermaid_code, visualizer_path)

        # Проверяем, что временный файл был создан
        mock_tempfile.assert_called_once()

        # Проверяем вызов визуализатора
        mock_run.assert_called_once_with(
            [visualizer_path, "-i", temp_file_mock.name, "-o", "graph_output.png"],
            check=True
        )

        # Проверяем удаление временного файла
        mock_remove.assert_called_once_with(temp_file_mock.name)


    @patch("subprocess.run", autospec=True)
    def test_visualize_graph_error(self, mock_run):
        """Тест обработки ошибки при визуализации."""
        visualizer_path = "path"
        mermaid_code = "graph TD\ncommit1:::commit\ncommit1 --> file1.txt\n"

        # Настраиваем mock для выброса исключения
        mock_run.side_effect = subprocess.CalledProcessError(1, "mmdc")

        # Проверяем, что исключение вызвано
        with self.assertRaises(subprocess.CalledProcessError):
            visualize_graph(mermaid_code, visualizer_path)

        # Проверяем, что subprocess.run был вызван с ожидаемыми аргументами
        mock_run.assert_called_once_with(
            [visualizer_path, "-i", ANY, "-o", "graph_output.png"],
            check=True
        )


if __name__ == "__main__":
    unittest.main()
