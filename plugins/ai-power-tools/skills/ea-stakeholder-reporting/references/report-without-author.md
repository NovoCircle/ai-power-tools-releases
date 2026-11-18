# A report without the Author line

EA's built-in report templates print each element's Author field, and EA fills that field with
the modeler's login name. The server can't change it: `generate_report` takes only a template
name. If the report goes outside the team, build a copy of the template without the Author
line, in EA's own template editor, then name that copy.

1. In EA, open Publish ribbon > Report Builder > Generate Documentation, and pick the Templates
   tab.
2. Click New. Give the copy a name, for example `Stakeholder (no author)`, and under Copy template
   pick the built-in template you normally use. Never edit the built-in one.
3. Select the new template and click Edit to open it in the template editor. Open the section
   that prints an element's details and delete the Author
   field from it. Check the Created and Modified sections too, where the author can print beside a date.
4. Save the template. EA stores it in the model, so it is there only for this model file.
5. Call `ea_repository(operation="generate_report", params={"package_id": ..., "template":
   "Stakeholder (no author)", "output_path": ...})`. Spell the name exactly as saved.
6. Open the output and search it for the login name. `generate_report` doesn't check the template
   name, and a misspelled one gives a default document that still has the Author lines.

Steps 1 to 3 were checked on EA 17.1 build 1716 (16 Nov 2026): Generate Documentation's Templates
tab lists the model's templates, and New opens a dialog with the name, the template type and Copy
template. If a step doesn't match your EA version, follow the prompts in the dialog and tell the
person what you changed.
