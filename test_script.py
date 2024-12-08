import unittest
import subprocess
from unittest.mock import patch, MagicMock, ANY
from script import get_git_dependencies, generate_mermaid_graph, visualize_graph


class TestGitDependencies(unittest.TestCase):
    @patch("subprocess.check_output")
    def test_get_git_dependencies_success(self, mock_check_output):
        """Тест успешного извлечения зависимостей."""
        mock_check_output.return_value = "commit1\nfile1.txt\nfile2.txt\n\ncommit2\nfile3.txt\n"
        repo_path = "/dummy/repo"
        expected = {
            "commit1": ["file1.txt", "file2.txt"],
            "commit2": ["file3.txt"],
        }
        result = get_git_dependencies(repo_path)
        self.assertEqual(result, expected)

    @patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git"))
    def test_get_git_dependencies_error(self, mock_check_output):
        """Тест обработки ошибки команды git."""
        repo_path = "/dummy/repo"
        with self.assertRaises(SystemExit):
            get_git_dependencies(repo_path)


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
