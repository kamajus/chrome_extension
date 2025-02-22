import glob
import os
import re
from io import BytesIO
from threading import Lock
from urllib.parse import unquote, urlparse
from zipfile import BadZipFile, ZipFile

from .package_storage import LocalStorage
from requests import get


def download_and_unzip_chrome_extension(
    extension_id: str, download_dir: str, chrome_version: str
):
    crx_url = f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion={chrome_version}&x=id%3D{extension_id}%26installsource%3Dondemand%26uc&acceptformat=crx2,crx3"

    response = get(crx_url)

    if response.status_code != 200:
        raise Exception(f"Failed to download extension {extension_id}")

    try:
        with ZipFile(BytesIO(response.content)) as z:
            z.extractall(download_dir)
    except BadZipFile:
        raise Exception(
            "Failed to unzip the CRX file. It might not be a valid zip file."
        )


def extract_name(path):
    parts = path.split("/")
    return parts[-1] if parts else None


def extract_extension_id_and_name(path: str):
    pattern = r".+?\/([a-z]{32})(?=[\/#?]|$)"
    path = unquote(path.lstrip("/webstore"))

    match = re.search(pattern, path)
    if match:
        extension_id = match.group(1)
        name = extract_name(path.strip("/").replace(extension_id, "").strip("/"))
        if name:
            return name, extension_id
        else:
            raise Exception("Failed to extract extension name from link")

    raise Exception("Failed to extract extension ID from link")


def extract_path_from_link(link):
    return urlparse(link).path


class File:
    def __init__(self, path):
        self.path = path

    def update_contents(self, update_function):
        file_contents = self.get_contents()

        updated_contents = update_function(file_contents)

        if updated_contents is None:
            raise Exception("No content is returned from update_function")

        self.write_contents(updated_contents)

    def write_contents(self, updated_contents):
        with open(self.path, "w", encoding="utf-8") as file:
            file.write(updated_contents)

    def get_contents(self):
        with open(self.path, "r", encoding="utf-8") as file:
            file_contents = file.read()
        return file_contents


lock = Lock()


class Extension:
    def __init__(
        self,
        extension_link=None,
        extension_id=None,
        extension_name=None,
        force_update=False,
        chrome_version="120.0.0.0",
        download_dir="extensions/",
        **kwargs,
    ):
        os.makedirs(download_dir, exist_ok=True)
        self.package_storage = LocalStorage(download_dir)

        self.chrome_version = chrome_version
        self.extension_link = extension_link
        self.force_update = force_update

        if extension_link:
            extension_name, extension_id = extract_extension_id_and_name(
                extract_path_from_link(extension_link)
            )

        self.extension_id = extension_id
        self.extension_name = extension_name

        if not extension_id:
            raise ValueError("Extension ID is required.")

        if not extension_name:
            raise ValueError("Extension name is required.")

        self.kwargs = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

        if not download_dir:
            raise ValueError("You must specify a download directory.")

        self.download_dir = os.path.abspath(download_dir)

        self.extension_path = os.path.join(self.download_dir, extension_name)
        self.extension_absolute_path = self.extension_path

    def download(self):
        print(f"Downloading {self.extension_name} Extension to {self.download_dir} ...")

        download_and_unzip_chrome_extension(
            extension_id=self.extension_id,
            download_dir=self.extension_absolute_path,
            chrome_version=self.chrome_version,
        )

    def get_files(self, ext):
        files = glob.glob(self.extension_path + "/**/*" + ext, recursive=True)
        files = [os.path.abspath(file) for file in files]
        files = [File(file) for file in files]
        return files

    def exists(self):
        return os.path.exists(self.extension_absolute_path)

    def get_file(self, path):
        return File(os.path.join(self.extension_path, path))

    def get_js_files(self):
        return self.get_files(".js")

    def get_json_files(self):
        return self.get_files(".json")

    def get_html_files(self):
        return self.get_files(".html")

    def get_css_files(self):
        return self.get_files(".css")

    def should_update_files(self):
        item = self.package_storage.get_item(self.extension_absolute_path, {})
        extension_data = item.get(self.extension_id)
        if extension_data is None:
            return True
        return extension_data != self.kwargs

    def updated_extension_data(self):
        dirname = self.extension_absolute_path
        item = self.package_storage.get_item(dirname, {})
        item[self.extension_id] = self.kwargs
        self.package_storage.set_item(dirname, item)

    def update_files(self):
        pass

    def load(self, with_command_line_option=True):
        with lock:
            if not self.exists() or self.should_update_files() or self.force_update:
                self.download()
                self.update_files(**self.kwargs)
                self.updated_extension_data()

        extension_path = self.extension_absolute_path
        if with_command_line_option:
            return f"--load-extension={extension_path}"
        else:
            return extension_path
