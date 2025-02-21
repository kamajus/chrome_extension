import json
import os


def get_cache_file_path(cache_path: str) -> str:
    dr = os.path.abspath(os.path.join(cache_path, "package_storage.json"))
    return dr


class MethodNotImplemented(Exception):
    pass


class BasicStorageBackend:
    def get_item(self, item: str, default: any = None) -> str:
        raise MethodNotImplemented()

    def set_item(self, item: str, value: any) -> None:
        raise MethodNotImplemented()

    def remove_item(self, item: str) -> None:
        raise MethodNotImplemented()

    def clear(self) -> None:
        raise MethodNotImplemented()


class JSONStorageBackend(BasicStorageBackend):
    def __init__(self, cache_path: str) -> None:
        self.cache_path = cache_path
        self.refresh()

    def refresh(self):
        self.json_path = get_cache_file_path(self.cache_path)
        self.json_data = {}

        if not os.path.isfile(self.json_path):
            self.commit_to_disk()

        with open(self.json_path, "r") as json_file:
            self.json_data = json.load(json_file)

    def commit_to_disk(self):
        try:
            with open(self.json_path, "w") as json_file:
                json.dump(self.json_data, json_file, indent=4)
        except:
            print("erro")

    def get_item(self, key: str, default=None) -> str:
        if key in self.json_data:
            return self.json_data[key]
        return default

    def items(self):
        return self.json_data

    def set_item(self, key: str, value: any) -> None:
        self.json_data[key] = value
        self.commit_to_disk()

    def remove_item(self, key: str) -> None:
        if key in self.json_data:
            self.json_data.pop(key)
            self.commit_to_disk()

    def clear(self) -> None:
        if os.path.isfile(self.json_path):
            os.remove(self.json_path)
        self.json_data = {}
        self.commit_to_disk()


class LocalStorage:
    def __init__(self, cache_path: str) -> None:
        self.storage_backend_instance = JSONStorageBackend(cache_path)

    def refresh(self) -> None:
        self.storage_backend_instance.refresh()

    def get_item(self, item: str, default=None) -> any:
        return self.storage_backend_instance.get_item(item, default)

    def set_item(self, item: str, value: any) -> None:
        self.storage_backend_instance.set_item(item, value)

    def remove_item(self, item: str) -> None:
        self.storage_backend_instance.remove_item(item)

    def clear(self):
        self.storage_backend_instance.clear()

    def items(self):
        return self.storage_backend_instance.items()
