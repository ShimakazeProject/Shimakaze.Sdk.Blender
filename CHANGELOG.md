# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial Blender 4.5 extension scaffold.
  - `blender_manifest.toml` with permissions, platforms and license declared.
  - Modular package: preferences, properties, operators, UI, keymap, utils.
  - Example operators: `shimakaze.hello`, `shimakaze.bump_asset_version`.
  - Build scripts (`build.ps1`, `Makefile`) and a GitHub Actions CI workflow.
