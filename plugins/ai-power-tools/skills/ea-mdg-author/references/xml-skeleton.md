# MDG XML skeleton and file encoding

Back to [SKILL.md](../SKILL.md).

## Canonical EA 17 File Structure

```xml
<?xml version="1.0" encoding="utf-8"?>
<MDG.Technology version="1.0" id="WBA" name="Westbrook Bank Architecture">

  <Documentation id="WBA" name="Westbrook Bank Architecture" version="1.0"
                 notes="Description shown in Manage Technologies dialog."
                 filename="" date="2026-01-01"/>

  <!-- SECTION 1: UML Profile — element/connector stereotypes + tagged values -->
  <UMLProfiles>
    <UMLProfile profiletype="uml2">
      <Documentation id="WBA"
                     name="WBADomainProfile"
                     version="1.0"
                     alias="WBA Profile"
                     notes="Stereotype definitions"/>
      <Content>
        <Stereotypes>
          <!-- stereotypes go here -->
        </Stereotypes>
        <TaggedValueTypes/>
      </Content>
    </UMLProfile>
  </UMLProfiles>

  <!-- SECTION 2: Diagram Profile — custom diagram types -->
  <DiagramProfile>
    <UMLProfile profiletype="uml2">
      <Documentation id="WBA-Diag" name="WBADiagrams" version="1.0"
                     alias="WBA Diagrams" notes="Custom diagram types"/>
      <Content>
        <Stereotypes>
          <!-- diagram stereotypes go here -->
        </Stereotypes>
        <TaggedValueTypes/>
      </Content>
    </UMLProfile>
  </DiagramProfile>

  <!-- SECTION 3: Toolboxes — palette pages shown in EA toolbox panel -->
  <UIToolboxes>
    <UMLProfile profiletype="uml2">
      <Documentation id="WBA-TB" name="WBA Toolboxes" version="1.0"
                     notes="WBA element and connector palettes"/>
      <Content>
        <Stereotypes>
          <!-- toolbox page stereotypes go here -->
        </Stereotypes>
        <TaggedValueTypes/>
      </Content>
    </UMLProfile>
  </UIToolboxes>

</MDG.Technology>
```

**Critical rules:**
- `<MDG.Technology id="WBA">` and `<Documentation id="WBA">` must match exactly — this is the tech ID used in COM API calls
- The UMLProfile `<Documentation id="WBA">` must also match the technology id for toolbox `WBA::StereotypeName` namespace resolution to work
- All three sections use the same `<UMLProfile profiletype="uml2">` wrapper

---

## File Encoding (Critical)

MDG Technology XML files must declare and use `utf-8` encoding, matching the Claude Code `Write`
tool's own output — the declaration and the actual byte encoding must agree, or EA rejects the
file outright. Full guidance (legacy `windows-1252` handling, read/write code patterns):
[`../../_shared/references/file-encoding.md`](../../_shared/references/file-encoding.md).
