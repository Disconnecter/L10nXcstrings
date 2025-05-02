# 🔤 Localization Keys Generator & Cleaner for iOS (SwiftGen-style)

This script (`L10nXcstrings.py`) automates the management of iOS localization strings using the new `Localizable.xcstrings` format. It helps you:

- ✅ Generate a Swift enum (`L10n`) with all localization keys as `case` constants
- ✅ Automatically annotate unused keys with `//TODO: Unused`
- ✅ Find and export a list of unused localization keys to `Unused.txt`

---

## 🛠 Features

- **Supports `.xcstrings`**: Parses Xcode's new JSON-based localization format.
- **CamelCase key formatting**: Converts `login.title_screen` → `loginTitleScreen`.
- **Safe enum generation**: Outputs a clean `Strings+Generated.swift` with `localize()` helper.
- **Usage analysis**: Scans your Swift codebase for usage of `L10n.<key>`.
- **Unused keys check**: Detects and marks localization keys that are not used anywhere in the codebase.

---

## 📦 File Structure Sample

```
SRC/
├── Resources/
│   ├── Localizable.xcstrings
│   └── Generated/
│       └── Strings+Generated.swift   ← ✅ Auto-generated
├── strings.py                        ← 🧠 This script
└── Unused.txt                        ← 📄 List of unused keys (if any)
```
---

## 🚀 Usage

1. **Place your `.xcstrings` file** in the correct path (`Resources/Localizable.xcstrings`)
2. **Run the script**:

```bash
python3 L10nXcstrings.py
```

3.	**🎉 You’ll get:**
- Strings+Generated.swift (updated)
- Unused.txt (if unused keys found)
- Output in terminal showing the count of unused keys

---

## 🧪 Requirements
- Python 3.6+
- Xcode .xcstrings file format (JSON)
- Swift codebase that uses L10n.<key> to reference localizations

---

## 📝 Notes
- The script automatically camelCases keys like k-about.welcome_screen → kAboutWelcomeScreen
- Unused keys are marked in the enum like so:

```
case loginTitle = "login.title" //TODO: Unused
```

To regenerate after .xcstrings updates or key usage changes, just re-run:

```bash
python3 L10nXcstrings.py
```


---
## 📝TODO:
- add parameters
- make a spm compatible
---

## 📄 License

MIT — free to use, modify, and contribute.

---

🙌 Contributions

Feel free to open issues or submit PRs to extend functionality — e.g., support for filtering folders, checking .localized() string usage, or CLI argument support.
