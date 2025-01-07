import os
import sys
import platform
import zipfile
import argparse


def main():
    default_os_name = platform.system().lower()
    default_processor = platform.processor().lower()
    if not default_processor:
        default_processor = "unknown"

    parser = argparse.ArgumentParser('CI Artifact Collector')
    parser.add_argument('-d', '--target-dir', type=str, required=True, help='Directory to collect the artifacts from')
    parser.add_argument('-p', '--prefix', type=str, required=True, help='Archive prefix')
    parser.add_argument('-o', '--os-name', type=str, default=default_os_name, required=False,
                        help='Operating system name (will be included in the archive name)')
    parser.add_argument('-f', '--cpu-family', type=str, default=default_processor, required=False,
                        help='CPU family (will be included in the archive name)')

    args = parser.parse_args()

    target_directory = args.target_dir
    if not os.path.isdir(target_directory):
        raise RuntimeError(f'invalid target directory "{target_directory}"')

    os_name = args.os_name
    cpu_family = args.cpu_family
    prefix = args.prefix

    zip_filename = f"{prefix}-{os_name}-{cpu_family}.zip"

    all_files = []
    for root, _, files in os.walk(target_directory):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
            print(f'Found file: {file_path}')

    if len(all_files) == 0:
        raise RuntimeError(f'no files found in "{target_directory}"')

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in all_files:
            zf.write(file_path, os.path.relpath(file_path, target_directory))

    print(f'{len(all_files)} files archived into {zip_filename}')


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f'Artifact collection failed: {e}', file=sys.stderr)
        sys.exit(-1)
