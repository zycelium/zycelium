"""
Based on: https://gist.github.com/izikeros/7b7496b0a71fda35156b5231859b9a72
"""

import functools
import os
import subprocess
from dataclasses import dataclass

from liccheck.command_line import (
    Level,
    check_package,
    generate_requirements_file_from_pyproject,
    get_packages_info,
    group_by,
    merge_args,
    read_strategy,
)


@dataclass
class Args:
    strategy_ini_file: str
    requirement_txt_file: str
    level: Level
    reporting_txt_file: str
    no_deps: bool


def analyze_package_licenses(
    requirement_file, strategy, level=Level.STANDARD, reporting_file=None, no_deps=False
):
    package_info = get_packages_info(requirement_file, no_deps)
    license_groups = group_by(
        package_info, functools.partial(check_package, strategy, level=level)
    )

    if reporting_file:
        license_report = []
        for status, packages in license_groups.items():
            license_report.extend(
                {
                    "name": pkg["name"],
                    "version": pkg["version"],
                    "license": (pkg["licenses"] or ["UNKNOWN"])[0],
                    "status": status,
                }
                for pkg in packages
            )
        return license_report


def check_package_licenses(args):
    config = merge_args(
        {
            "strategy_ini_file": args.strategy_ini_file,
            "requirement_txt_file": args.requirement_txt_file,
            "level": args.level,
            "reporting_txt_file": args.reporting_txt_file,
            "no_deps": args.no_deps,
            "dependencies": False,
            "optional_dependencies": [],
            "as_regex": False,
        }
    )
    license_strategy = read_strategy(config["strategy_ini_file"])
    if config["dependencies"] is True or len(config["optional_dependencies"]) > 0:
        config["requirement_txt_file"] = generate_requirements_file_from_pyproject(
            config["dependencies"], config["optional_dependencies"]
        )

    return analyze_package_licenses(
        config["requirement_txt_file"],
        license_strategy,
        config["level"],
        config["reporting_txt_file"],
        config["no_deps"],
    )


def get_package_license_file_url(pypi_package_name):
    import json

    import requests

    url = f"https://pypi.org/pypi/{pypi_package_name}/json"
    r = requests.get(url)
    data = json.loads(r.text)
    return data["info"]["license_file"]


def format_package(pkg):
    """Format package info as name==version."""
    return f"{pkg['name']}=={pkg['version']}"


def group_by_license(packages):
    """Group packages by their license."""
    license_groups = {}
    for pkg in packages:
        license_name = pkg["license"]
        if license_name not in license_groups:
            license_groups[license_name] = []
        license_groups[license_name].append(pkg)
    return license_groups


def main():
    # Generate requirements.txt from poetry
    subprocess.run(["poetry", "export", "-o", "requirements.txt"], check=True)

    config = Args(
        strategy_ini_file="pyproject.toml",
        requirement_txt_file="requirements.txt",
        level=Level.STANDARD,
        reporting_txt_file="reporting.txt",
        no_deps=False,
    )
    license_data = check_package_licenses(config)

    # Clean up temporary requirements file
    os.remove("requirements.txt")

    license_groups = group_by_license(license_data)

    report_lines = []
    for license_name, packages in sorted(license_groups.items()):
        report_lines.append(f"\n[{license_name}]")
        for pkg in sorted(packages, key=lambda x: x["name"]):
            report_lines.append(f"  {format_package(pkg)}")

    print("\n".join(report_lines).strip())
