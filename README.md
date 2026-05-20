# Localization Keys Generator and Cleaner for iOS

![Tests](https://github.com/Disconnecter/L10nXcstrings/actions/workflows/python-tests.yml/badge.svg)

`L10nXcstrings.py` generates Swift localization helpers from Xcode
`Localizable.xcstrings` catalogs and reports localization keys that are not used
from Swift code.

## Features

- Parses Xcode's JSON-based `.xcstrings` format.
- Reads plain string units and nested catalog variation values, including plural
  branches.
- Uses `sourceLanguage` by default, with `--language` override support.
- Fails when the selected language is missing for any key, unless
  `--allow-missing` is passed.
- Generates a Swift namespace enum with `public static var` and
  `public static func` helpers.
- Converts keys such as `login.title_screen` to `loginTitleScreen`.
- Escapes Swift keywords and reports identifier collisions.
- Adds stable hash suffixes for non-ASCII keys that cannot be represented by the
  ASCII Swift naming policy.
- Scans Swift source for explicit `L10n.key` usage, native localization calls
  such as `String(localized:)`, `NSLocalizedString`, SwiftUI title-key views,
  and custom call/member names supplied from the CLI.
- Writes unused original localization keys to `Unused.txt`.
- Verifies generated Swift with Swift 6 typechecking and runtime bundle-resource
  tests when `swiftc` is available.

## Install

```bash
brew tap disconnecter/l10n https://github.com/Disconnecter/homebrew-l10n
brew install l10n-xcstrings
```

## Usage

Place your catalog at `Localizable.xcstrings`, then run:

```bash
l10n-xcstrings
```

With explicit paths:

```bash
l10n-xcstrings \
  --input Resources/Localizable.xcstrings \
  --output-swift Resources/Generated/Strings+Generated.swift \
  --output-unused Unused.txt \
  --source-dir Sources \
  --ignore-dirs build DerivedData \
  --table-name Localizable \
  --bundle Bundle.module \
  --localized-call ChipTitle \
  --localized-member toolbarTitle
```

Generated Swift looks like this:

```swift
public enum L10n {
  /// Sign in
  public static var loginTitle: String {
    return tr(key: "login.title")
  }

  /// Count %d
  public static func countValue(_ p1: Int) -> String {
    return tr(key: "count.value", p1)
  }
}
```

Unused keys are annotated in generated Swift and written to `Unused.txt`:

```swift
#warning("Unused key: loginTitle")
public static var loginTitle: String {
  return tr(key: "login.title")
}
```

## Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `--input` | `Localizable.xcstrings` | Path to the source `.xcstrings` file. |
| `--output-swift` | `Generated/Strings+Generated.swift` | Path for generated Swift. |
| `--output-unused` | `Unused.txt` | Path for original unused keys. |
| `--source-dir` | `.` | Directory scanned for Swift usage. |
| `--ignore-dirs` | none | Space-separated directories to skip while scanning. |
| `--enum-name` | `L10n` | Generated Swift namespace name. |
| `--language` | `sourceLanguage` or `en` | Catalog language to read. |
| `--allow-missing` | off | Skip keys missing the selected language instead of failing. |
| `--table-name` | none | Localization table name passed to `NSLocalizedString`. |
| `--bundle` | `Bundle.main` | Swift bundle expression passed to `NSLocalizedString`. Use `Bundle.module` for Swift packages. |
| `--localized-call` | built-in Swift/iOS title-key calls | Additional function/type call whose first string literal argument is a localization key. Repeat for multiple names. |
| `--localized-member` | built-in SwiftUI title-key members | Additional member call whose first string literal argument is a localization key. Repeat for multiple names. |

## Requirements

- Python 3.9+
- Xcode `.xcstrings` JSON catalog
- Swift code that references generated helpers as `L10n.key` or typed shorthand
  values

## Tests

```bash
python3 -m pip install .[dev]
ruff check .
python3 -m unittest discover -s tests
```

When `swiftc` is installed, the tests also typecheck generated Swift with a
small Swift caller under Swift 6.

## Notes

- Literal percent signs in localized strings must be escaped as `%%`.
- Use `%@` for Swift string arguments. C string placeholders (`%s`) are rejected
  because passing Swift `String` values to `%s` compiles but formats incorrectly.
- Dynamic printf widths and precisions such as `%*d` are rejected.
- Plural placeholders such as `%#@items@` are accepted. Concrete variation
  branches are used to infer a stronger Swift argument type when possible, and
  generated Swift uses `String.localizedStringWithFormat` so `.stringsdict`
  plural resources are resolved at runtime.
- Positional placeholders must be complete and consistent, for example
  `%2$@ %1$d`.
- Version `0.0.6` changes generated Swift from value enum cases to static
  namespace properties/functions. Existing callers such as `L10n.title.string`
  should migrate to `L10n.title`; associated-value cases should migrate to
  generated static functions such as `L10n.countValue(3)`.
- Release tags use bare semantic versions such as `0.0.6`; the release workflow
  requires the tag to match `pyproject.toml`.

## License

MIT
