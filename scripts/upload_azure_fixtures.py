from __future__ import annotations

import argparse
from pathlib import Path

from azure.identity import AzureCliCredential
from azure.storage.blob import ContainerClient, ContentSettings


def upload_directory(
    account_url: str,
    container_name: str,
    fixture_root: Path,
) -> None:
    container = ContainerClient(
        account_url=account_url,
        container_name=container_name,
        credential=AzureCliCredential(),
    )
    for path in sorted(fixture_root.iterdir()):
        if not path.is_file():
            continue
        content_type = (
            "application/json"
            if path.suffix == ".json"
            else "application/xml"
            if path.suffix == ".xml"
            else "text/plain"
        )
        container.upload_blob(
            path.name,
            path.read_bytes(),
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        print(f"Uploaded synthetic fixture {container_name}/{path.name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--milan-account-url", required=True)
    parser.add_argument("--utrecht-account-url", required=True)
    parser.add_argument("--container", default="source")
    arguments = parser.parse_args()

    root = Path(__file__).parents[1] / "src" / "collab" / "fixtures"
    upload_directory(
        arguments.milan_account_url,
        arguments.container,
        root / "milan",
    )
    upload_directory(
        arguments.utrecht_account_url,
        arguments.container,
        root / "utrecht",
    )


if __name__ == "__main__":
    main()
