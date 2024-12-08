import subprocess
import os
import sys
import argparse
from tempfile import NamedTemporaryFile


def get_git_dependencies(repo_path):
    """Извлекает зависимости из коммитов в указанном Git-репозитории."""
    try:
        output = subprocess.check_output(
            ["git", "-C", repo_path, "log", "--pretty=format:%H", "--name-only"],
            text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при выполнении git: {e}", file=sys.stderr)
        sys.exit(1)

    dependencies = {}
    current_commit = None
    for line in output.splitlines():
        if line.strip() == "":
            current_commit = None
            continue

        if not current_commit:
            current_commit = line.strip()
            dependencies[current_commit] = []
        else:
            dependencies[current_commit].append(line.strip())
    
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
