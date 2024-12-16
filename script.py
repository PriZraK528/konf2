import subprocess
import os
import sys
import argparse
from tempfile import NamedTemporaryFile
import zlib
import os

def get_git_dependencies(repo_path):
    """
    Извлекает зависимости из коммитов в Git-репозитории, анализируя файлы в .git/objects.
    """
    git_dir = os.path.join(repo_path, ".git")
    objects_dir = os.path.join(git_dir, "objects")

    if not os.path.isdir(objects_dir):
        raise ValueError("Указанный путь не является Git-репозиторием.")

    def read_object(obj_path):
        """Считывает и декодирует содержимое объекта Git."""
        with open(obj_path, "rb") as f:
            compressed_data = f.read()
        return zlib.decompress(compressed_data)

    def parse_commit(commit_data):
        """Парсит объект commit и извлекает SHA-1 дерева."""
        try:
            # Разделяем данные на заголовок и содержимое
            _, body = commit_data.split(b'\x00', 1)

            # Перебираем строки тела
            for line in body.split(b'\n'):
                if line.startswith(b"tree "):
                    # Возвращаем SHA дерева
                    return line.split(b" ")[1].decode()

            # Если строка tree отсутствует
            print(f"Ошибка: объект commit не содержит строки tree. Данные: {commit_data}")
        except Exception as e:
            print(f"Ошибка при разборе объекта commit: {e}. Данные: {commit_data}", file=sys.stderr)
        return None

    def parse_tree(tree_data):
        """Парсит объект tree и извлекает файлы."""
        files = []
        idx = 0
        while idx < len(tree_data):
            space_idx = tree_data.index(b" ", idx)
            null_idx = tree_data.index(b"\x00", space_idx)
            file_name = tree_data[space_idx + 1:null_idx].decode()
            files.append(file_name)
            idx = null_idx + 21
        return files

    dependencies = {}
    for obj_dir in os.listdir(objects_dir):
        if len(obj_dir) != 2:  # Объекты хранятся в каталогах с двухсимвольными названиями
            continue

        obj_dir_path = os.path.join(objects_dir, obj_dir)
        if not os.path.isdir(obj_dir_path):
            continue

        for obj_file in os.listdir(obj_dir_path):
            obj_path = os.path.join(obj_dir_path, obj_file)
            full_hash = f"{obj_dir}{obj_file}"
            obj_data = read_object(obj_path)

            if obj_data.startswith(b"commit "):
                # Извлекаем дерево коммита
                tree_sha = parse_commit(obj_data)
                # Пример логирования, если дерево не найдено
                if not tree_sha:
                    print(f"Пропуск коммита {full_hash}: tree SHA не найден в объекте commit. Данные: {obj_data}", file=sys.stderr)
                    continue


                dependencies[full_hash] = []

                # Считываем дерево
                tree_dir = os.path.join(objects_dir, tree_sha[:2])
                tree_path = os.path.join(tree_dir, tree_sha[2:])
                if not os.path.exists(tree_path):
                    print(f"Пропуск дерева {tree_sha}: файл {tree_path} не найден.")
                    continue

                tree_data = read_object(tree_path).split(b'\x00', 1)[1]

                # Извлекаем файлы из дерева
                files = parse_tree(tree_data)
                dependencies[full_hash].extend(files)
                
    return dependencies



def generate_mermaid_graph(dependencies):
    """Создает граф в формате Mermaid."""
    graph = ["graph TD"]
    for commit, files in dependencies.items():
        graph.append(f"    {commit}:::commit")
        for file in files:
            graph.append(f"    {commit} --> {file}")
    return "\n".join(graph)


def visualize_graph(mermaid_code, visualizer_path):
    """Визуализирует Mermaid-граф с помощью mmdc и открывает результат."""
    with NamedTemporaryFile("w", delete=False, suffix=".mmd") as tmp_file:
        tmp_file.write(mermaid_code)
        tmp_file_path = tmp_file.name

    try:
        output_path = "graph_output.png"  # Имя выходного файла
        subprocess.run(
            [visualizer_path, "-i", tmp_file_path, "-o", output_path],
            check=True
        )
        print(f"Граф успешно сохранен в файл: {output_path}")
        
        # Открываем изображение
        print("Открытие файла...")
        if sys.platform == "win32":
            os.startfile(output_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", output_path])
        else:  # Linux и другие Unix-системы
            subprocess.run(["xdg-open", output_path])
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при визуализации графа: {e}", file=sys.stderr)
        raise
    finally:
        os.remove(tmp_file_path)


def main():
    parser = argparse.ArgumentParser(description="Визуализация графа зависимостей Git-репозитория.")
    parser.add_argument("visualizer_path", help="Путь к программе для визуализации графов.")
    parser.add_argument("repo_path", help="Путь к анализируемому репозиторию.")
    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        print("Указанный путь к репозиторию не существует или не является директорией.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.visualizer_path):
        print("Указанный путь к программе визуализации неверен.", file=sys.stderr)
        sys.exit(1)

    dependencies = get_git_dependencies(args.repo_path)
    graph_code = generate_mermaid_graph(dependencies)
    visualize_graph(graph_code, args.visualizer_path)


if __name__ == "__main__":
    main()
