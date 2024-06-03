#!/usr/bin/env python3
"""
Merge build notes from the sub components and return final generated build notes data
Note: needs key2repo.json to map docker images to their github repos
"""
import base64
import json
import os
from typing import Any

import requests
from ruamel.yaml import YAML

GIT_TOKEN = os.environ.get("GH_TOKEN", "")


def download_file_from_github(
    username: str,
    repository_name: str,
    tag: str,
    file_path: str,
    github_token: str = "",
) -> str:
    """
    returns file contents from github
    """
    headers = {}
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    url = f"https://api.github.com/repos/{username}/{repository_name}/contents/{file_path}?ref={tag}"
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        file_content = data["content"]
        file_content_encoding = data.get("encoding")
        if file_content_encoding == "base64":
            file_content = base64.b64decode(file_content).decode()
        return file_content
    except Exception:
        return ""


class CustomBuildNotes:
    """
    Custom build notes data format
    """

    def __init__(self) -> None:
        """
        init function
        """
        self.author, self.date, self.tag = (
            "",
            "",
            "",
        )  # will be set in actual_to_custom method
        self.jira = {}
        self.new = {}
        self.changed = {}
        self.removed = {}
        self.deprecated_configs = {}
        self.limitations = set()
        self.deprecated_features = set()
        self.dependencies = set()

    def custom_to_actual(self) -> dict[Any, Any]:
        """
        convert custom data to build notes dumpable data
        """
        return_yaml = {}
        return_yaml["BuildNotes"] = {}
        return_yaml["BuildNotes"]["Author"] = self.author
        return_yaml["BuildNotes"]["Date"] = self.date
        return_yaml["BuildNotes"]["Tag"] = self.tag
        return_yaml["BuildNotes"]["Changes"] = []
        # set jira
        for k, v in self.jira.items():
            return_yaml["BuildNotes"]["Changes"].append(
                {
                    "JiraID": k,
                    "description": v.get("description", ""),
                    "pr": v.get("pr", ""),
                    "type": v.get("type", ""),
                    "component": v.get("component", ""),
                    "stepstoreproduce": v.get("stepstoreproduce", ""),
                    "impacts": v.get("impacts", ""),
                }
            )
        return_yaml["BuildNotes"]["Config Changes"] = {}
        # set new configs
        return_yaml["BuildNotes"]["Config Changes"]["New"] = []
        for k, v in self.new.items():
            new_entry = {"component": k, "files": []}
            for sk, sv in v.items():
                file_data = {"file": sk, "changes": sv}
                new_entry["files"].append(file_data)
            return_yaml["BuildNotes"]["Config Changes"]["New"].append(new_entry)

        # set changed configs
        return_yaml["BuildNotes"]["Config Changes"]["Changed"] = []
        for k, v in self.changed.items():
            changed_entry = {"component": k, "files": []}
            for sk, sv in v.items():
                file_data = {"file": sk, "changes": sv}
                changed_entry["files"].append(file_data)
            return_yaml["BuildNotes"]["Config Changes"]["Changed"].append(changed_entry)

        # set deprecated configs
        return_yaml["BuildNotes"]["Config Changes"]["Deprecated"] = []
        for k, v in self.deprecated_configs.items():
            deprecated_entry = {"component": k, "files": []}
            for sk, sv in v.items():
                file_data = {"file": sk, "changes": sv}
                deprecated_entry["files"].append(file_data)
            return_yaml["BuildNotes"]["Config Changes"]["Deprecated"].append(
                deprecated_entry
            )

        # set new configs
        return_yaml["BuildNotes"]["Config Changes"]["Removed"] = []
        for k, v in self.removed.items():
            removed_entry = {"component": k, "files": []}
            for sk, sv in v.items():
                file_data = {"file": sk, "changes": sv}
                removed_entry["files"].append(file_data)
            return_yaml["BuildNotes"]["Config Changes"]["Removed"].append(removed_entry)

        # set limitations
        return_yaml["BuildNotes"]["Limitations"] = list(self.limitations)
        return_yaml["BuildNotes"]["Dependencies"] = list(self.dependencies)
        return_yaml["BuildNotes"]["Deprecated Features"] = list(
            self.deprecated_features
        )

        return return_yaml

    def actual_to_custom(self, data: dict[Any, Any]) -> None:
        """
        convert build notes yaml dump data provided to custom data
        """
        self.author = data["BuildNotes"].get("Author", "")
        self.date = data["BuildNotes"].get("Date", "")
        self.tag = data["BuildNotes"].get("Tag", "")

        # jira map
        for e in data["BuildNotes"]["Changes"]:
            if e["JiraID"] not in self.jira:
                self.jira[e["JiraID"]] = {
                    "pr": e.get("pr", ""),
                    "type": e.get("type", ""),
                    "component": e.get("component", ""),
                    "description": e.get("description", ""),
                    "stepstoreproduce": e.get("stepstoreproduce", ""),
                    "impacts": e.get("impacts", ""),
                }
            else:
                pr, comp, desc, steps, imp = (
                    e.get("pr", ""),
                    e.get("component", ""),
                    e.get("description", ""),
                    e.get("stepstoreproduce", ""),
                    e.get("impacts", ""),
                )
                if pr:
                    self.jira[e["JiraID"]][
                        "pr"
                    ] = f'{self.jira[e["JiraID"]]["pr"]}, {comp}'
                if comp:
                    self.jira[e["JiraID"]][
                        "component"
                    ] = f'{self.jira[e["JiraID"]]["component"]}, {comp}'
                if desc:
                    self.jira[e["JiraID"]][
                        "description"
                    ] = f'{self.jira[e["JiraID"]]["description"]}, {desc}'
                if steps:
                    self.jira[e["JiraID"]][
                        "stepstoreproduce"
                    ] = f'{self.jira[e["JiraID"]]["stepstoreproduce"]}, {steps}'
                if imp:
                    self.jira[e["JiraID"]][
                        "impacts"
                    ] = f'{self.jira[e["JiraID"]]["impacts"]}, {imp}'
        # configs map
        # new configs
        cfgs = data["BuildNotes"].get("Config Changes", {})
        for e in cfgs.get("New", []):
            c = e["component"]
            if c not in self.new:
                self.new[c] = {}
            for f in e["files"]:
                if f["file"] not in self.new[c]:
                    self.new[c][f["file"]] = []
                self.new[c][f["file"]].extend(f["changes"])

        # changed configs
        for e in cfgs.get("Changed", []):
            c = e["component"]
            if c not in self.changed:
                self.changed[c] = {}
            for f in e["files"]:
                if f["file"] not in self.changed[c]:
                    self.changed[c][f["file"]] = []
                self.changed[c][f["file"]].extend(f["changes"])

        # deprecated configs
        for e in cfgs.get("Deprecated", []):
            c = e["component"]
            if c not in self.deprecated_configs:
                self.deprecated_configs[c] = {}
            for f in e["files"]:
                if f["file"] not in self.deprecated_configs[c]:
                    self.deprecated_configs[c][f["file"]] = []
                self.deprecated_configs[c][f["file"]].extend(f["changes"])

        # removed configs
        for e in cfgs.get("Removed", []):
            c = e["component"]
            if c not in self.removed:
                self.deprecated_configs[c] = {}
            for f in e["files"]:
                if f["file"] not in self.removed[c]:
                    self.removed[c][f["file"]] = []
                self.removed[c][f["file"]].extend(f["changes"])

        # limitations list
        for e in data["BuildNotes"].get("Limitations", []):
            self.limitations.add(e)
        # deprecated features list
        for e in data["BuildNotes"].get("Deprecated Features", []):
            self.deprecated_features.add(e)
        # dependencies list
        for e in data["BuildNotes"].get("Dependencies", []):
            self.dependencies.add(e)


class MergeBuildNotes:
    """
    Merge build notes of the current repo with it's sub components, if they exist
    """

    def __init__(self, tag: str):
        """
        init function
        """
        self.yaml: YAML = YAML()
        self.tag: str = tag
        with open("build_notes.yaml", mode="r", encoding="utf-8") as fh:
            self.data = self.yaml.load(fh)
        if os.path.exists("releases.yaml") and os.path.isfile("releases.yaml"):
            with open("releases.yaml", mode="r", encoding="utf-8") as fh:
                self.rls_data: Any = self.yaml.load(fh)
        else:
            self.rls_data: Any = {}

    def get_sub_components(self) -> dict[str, CustomBuildNotes]:
        """
        Get the sub components details and return map of those details

        Gets the sub components list from repo root by reading releases.yaml.
        Download build_notes.yaml from the repo and create the sub component map.

        Args:

        Returns:
            Sub component map, with key as component and value as build notes dump
            Sample sub component map:

            {"tinker": {
                "BuildNotes": ...
                },
            "sentinel": {
                "BuildNotes": ...
                },
            }
        """
        res = {}
        with open(".github/scripts/key2repo.json", mode="r", encoding="utf-8") as fh:
            k2r = json.load(fh)
            k2r = k2r["dockerImages"]
        for k, v in self.rls_data["dockerImages"].items():
            if k not in k2r:
                continue
            repo = k2r[k]
            username, repo = repo.split("/")
            tag = v.split(":")[-1]
            file_data = download_file_from_github(
                username, repo, tag, "build_notes.yaml", GIT_TOKEN
            )
            if not file_data:
                print(f"No build notes for {k} -> {tag}")
                continue
            file_data_dict = self.yaml.load(file_data)
            obj = CustomBuildNotes()
            obj.actual_to_custom(file_data_dict)
            res[k] = obj
        return res

    def merge_sub_components(
        self, data: dict[str, CustomBuildNotes]
    ) -> CustomBuildNotes:
        """
        Merge sub components' build notes with the current repo's build notes

        Merge sub components' build notes dict with the current repo's build notes dict and
        returns the final dict that can be dumped to build_notes.yaml

        Args:

        Returns:
            A dict with the format expected by the build_notes file
        """
        with open("build_notes.yaml", mode="r", encoding="utf-8") as fh:
            d = self.yaml.load(fh)
        final_obj = CustomBuildNotes()
        final_obj.actual_to_custom(d)
        for _, v in data.items():
            for subk, subv in v.jira.items():
                if subk in final_obj.jira:
                    final_obj.jira[subk][
                        "description"
                    ] = f"{final_obj.jira[subk]['description']}, {subv['description']}"
                    final_obj.jira[subk][
                        "stepstoreproduce"
                    ] = f"{final_obj.jira[subk]['stepstoreproduce']}, {subv['stepstoreproduce']}"
                    final_obj.jira[subk][
                        "impacts"
                    ] = f"{final_obj.jira[subk]['impacts']}, {subv['impacts']}"
                else:
                    final_obj.jira[subk] = subv

            # new configs
            for comp, deets in v.new.items():
                if comp not in final_obj.new:
                    final_obj.new[comp] = {}
                for f, fdeets in deets.items():
                    if f not in final_obj.new[comp]:
                        final_obj.new[comp][f] = []
                    final_obj.new[comp][f].extend(fdeets)

            # changed configs
            for comp, deets in v.changed.items():
                if comp not in final_obj.changed:
                    final_obj.changed[comp] = {}
                for f, fdeets in deets.items():
                    if f not in final_obj.changed[comp]:
                        final_obj.changed[comp][f] = []
                    final_obj.changed[comp][f].extend(fdeets)

            # deprecated_configs configs
            for comp, deets in v.deprecated_configs.items():
                if comp not in final_obj.deprecated_configs:
                    final_obj.deprecated_configs[comp] = {}
                for f, fdeets in deets.items():
                    if f not in final_obj.deprecated_configs[comp]:
                        final_obj.deprecated_configs[comp][f] = []
                    final_obj.deprecated_configs[comp][f].extend(fdeets)

            # removed configs
            for comp, deets in v.removed.items():
                if comp not in final_obj.removed:
                    final_obj.removed[comp] = {}
                for f, fdeets in deets.items():
                    if f not in final_obj.removed[comp]:
                        final_obj.removed[comp][f] = []
                    final_obj.removed[comp][f].extend(fdeets)

            for d in v.limitations:
                final_obj.limitations.add(d)
            for d in v.deprecated_features:
                final_obj.deprecated_features.add(d)
            for d in v.dependencies:
                final_obj.dependencies.add(d)

        return final_obj


def main():
    """
    Main function
    """
    tag = "v8.6.12"
    yaml = YAML()
    obj = MergeBuildNotes(tag)
    if not obj.rls_data:
        # if no releases file, return
        return
    sub_components = obj.get_sub_components()
    final_data = obj.merge_sub_components(sub_components)
    final_dumpable_data = final_data.custom_to_actual()
    with open("build_notes.yaml", mode="w", encoding="utf-8") as fh:
        yaml.dump(final_dumpable_data, fh)


if __name__ == "__main__":
    main()
