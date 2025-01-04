import os
import platform
import zipfile


def compress_directory_to_zip(directory, prefix="archive"):
    os_name = platform.system().lower()
    processor = platform.processor().lower()

    if not processor:
        processor = "unknown"

    zip_filename = f"{prefix}-{os_name}-{processor}.zip"

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.relpath(file_path, directory))


if __name__ == "__main__":
    target_directory = 'dist'
    if os.path.isdir(target_directory):
        compress_directory_to_zip(target_directory, prefix="osh")
    else:
        print(f"Invalid directory path: {target_directory}")
