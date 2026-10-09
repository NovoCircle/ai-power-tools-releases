# `export_xmi` / `import_xmi` — full verification record

> **HISTORICAL. The defect recorded here was fixed in server 2.2.0.** Everything below was measured
> against v2.1.0 and is kept because the shape of the failure is worth knowing: both operations
> reported success while doing nothing, and only opening the file and counting rows revealed it.
> `export_xmi` now reads the file back and returns `xmi_export_wrong_format` or `xmi_export_empty`
> rather than a false success. Do not read the guidance below as current advice about the server.


*Server: AI Power Tools for Sparx EA v2.1.0. Model: the Westbrook Bank demo repository,
`<model-dir>\WestbrookBank.qea`. All calls below were made against packages that already existed
in the model — none of the source content was created for this test.*

## What was tested

Three `export_xmi` calls against three different Westbrook Bank packages, chosen to rule out
"it only breaks on this one package":

| Package | Content | `export_xmi` params |
|---|---|---|
| A component package with 4 `WBAVendorSystem`/`WBABusinessApplication` elements, tagged values, and `Uses` connectors | No diagram | `{"package_id": <id>, "path": "<scratch>\\export1.xml"}` |
| A component package with 7 elements | Has a Logical diagram | `{"package_id": <id>, "path": "<scratch>\\export2.xml"}` |
| A package containing a BPMN2.0 diagram | 5 elements, one BPMN process diagram | `{"package_id": <id>, "path": "<scratch>\\export3.xml"}` |

## What came back

The tool's JSON response looked correct — for the second and third packages it even reported
`"xmi_type": "XMI 2.1"` and `"status": "exported"` (the first package's response omitted the
`xmi_type` field entirely, an inconsistency worth noting but secondary to the finding below).

The **file written to disk**, in all three cases, was not XMI at all. It was an XPDL 2.2
workflow-package document — the format EA uses for BPMN process interchange — containing only a
package header and an empty type-declarations block:

```xml
<?xml  version='1.0' encoding='windows-1252' ?>
<Package xmlns="http://www.wfmc.org/2009/XPDL2.2" Id="EAPK_..." Name="...">
	<PackageHeader>
		<XPDLVersion>2.2</XPDLVersion>
		<Vendor>SparxSystems</Vendor>
		<Created>2026-09-23 15:17:07</Created>
	</PackageHeader>
	<TypeDeclarations/>
</Package>
```

No `<uml:Model>`, no `packagedElement`, no tagged values, no connectors — for any of the three
packages. The third package (the one with an actual BPMN diagram) additionally got a `<Pages>`
entry naming the diagram and an empty `<WorkflowProcess>` stub, but still no usable model
content:

```xml
	<Pages>
		<Page Id="EAID_..." Name="Consumer Loan Origination Overview"/>
	</Pages>
	<WorkflowProcesses>
		<WorkflowProcess Name="" Id="EAID_DP000000_...">
			<ProcessHeader/>
		</WorkflowProcess>
	</WorkflowProcesses>
```

File sizes were tiny in every case (346–620 bytes) for packages with 4–7 real elements each —
itself a signal that something is missing, before even opening the file.

## Import side — confirmed zero round trip

The exported file from the third package was imported into a scratch package created for this
purpose (`_sl41_scratch`, deleted immediately after this test — see below):

```python
ea_repository(operation="import_xmi", params={
    "path": "<scratch>\\export3.xml",
    "package_id": <scratch_package_id>,
})
# -> {"status": "imported", "import_type": "XMI 2.1", "result": ""}
```

The response again claimed success. Direct SQL against the target package immediately after
confirmed nothing was actually created:

```sql
SELECT COUNT(*) FROM t_object  WHERE Package_ID = <scratch_package_id>;   -- 0
SELECT COUNT(*) FROM t_package WHERE Parent_ID  = <scratch_package_id>;   -- 0
```

`ea_model(operation="list_elements_in_package")` and `list_child_packages` against the same
package both returned empty results, consistent with the SQL counts.

## Cleanup

The scratch package (`_sl41_scratch`, created under the model's `_scenario_tests` root
specifically for this test) was deleted with `ea_model(operation="delete_package")` immediately
after the import test. A follow-up `SELECT COUNT(*) FROM t_package WHERE Package_ID =
<scratch_package_id>` returned `0`, confirming removal. Nothing outside that scratch package was
touched.

## Conclusion

`export_xmi` in this server version does not perform a true XMI 1.1/2.1 model export for
non-BPMN content — it silently falls back to an XPDL workflow export that captures almost
nothing, while reporting success and (usually) claiming `"xmi_type": "XMI 2.1"`. `import_xmi`
compounds this by also reporting success on an import that creates nothing. Treat both
operations as unverified for any package until you have personally opened the output file (or,
for import, counted rows in the target package) and confirmed real content is present. This is a
defect to report via `ea-diagnostic`, not a modeling mistake to work around.
