# MDG Technology XML file encoding

Shared by every skill that reads, writes, or deploys a Sparx EA MDG Technology XML file.

MDG Technology XML files must **declare and use `utf-8` encoding** — the declaration and the
actual byte encoding of the file must agree:

```xml
<?xml version="1.0" encoding="utf-8"?>
```

This matches what the Claude Code `Write` tool already produces, so a file authored with `Write`
needs no extra handling. EA **rejects the file outright** if the declaration and the actual byte
encoding disagree — so if you ever hand-edit or receive a file from elsewhere, verify both,
don't just fix one.

## Read/write code patterns

```python
# Writing
with open("WBA_MDG.xml", "w", encoding="utf-8") as f:
    f.write(xml_content)

# Reading, to pass to ImportTechnology
with open("WBA_MDG.xml", encoding="utf-8") as f:
    xml = f.read()
```

## Legacy files

Older EA versions and hand-written MDG files sometimes used `windows-1252` instead. If you
receive one of these:

1. Re-save the file as UTF-8.
2. Update the `encoding=` declaration in the XML prolog to match.

Do this together — updating only the declaration without re-saving the bytes (or vice versa)
recreates the disagreement that makes EA reject the file.
