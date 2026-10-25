# Dataset schemas

These documents describe the standalone source-report Parquet files. See the
[conversion rules](../README.md#schemas-and-interpretation) for shared semantics.
Field IDs are stable within each dataset. Source headers show the primary accepted
spelling; documented aliases and normalized punctuation/case are also accepted.

The descriptions below explain what a row represents and how the reports
relate. They describe the converter in this checkout; previously published
generations may retain older schemas or normalization rules. The per-dataset
guides record those differences.

Use the [query API index](../../../lgd-query/docs/datasets/README.md) for Python
and CLI lookups over these report snapshots.

- Registers identify entities; mapping reports identify associations. A code
  lookup can return several rows without representing several entities.
- LGD, census and ECI identifiers are separate namespaces. `entity_code` needs
  its entity type; administrative-unit, office, block and local-body codes
  are not interchangeable.
- Supplied parent names and links can disagree across reports. The individual
  guides identify any normalization and the retained discrepancy evidence.
- Standalone snapshots contain the selected report's rows. History records
  observations and can carry earlier rows through reviewed missing coverage,
  with their actual source dates and a “not updated” flag. Observation dates
  do not establish the legal effective dates of changes.
- `changes` and `transactions` already describe events. Each is a cumulative
  table; neither uses the snapshot-history model.

| Dataset | Description | Columns | Report kind |
| --- | --- | ---: | --- |
| [assembly_constituencies](assembly_constituencies.md) | Assembly constituencies with LGD identifiers and parliamentary/state parent attributes. | 6 | Snapshot report |
| [blocks](blocks.md) | Development blocks and their reported district associations; one block may have several. | 8 | Snapshot report |
| [central_admin_dept_units](central_admin_dept_units.md) | Named central administrative units linked to their levels, including individual postal units. | 5 | Snapshot report |
| [central_admin_depts](central_admin_depts.md) | Central administrative-unit level definitions, such as postal levels, with hierarchy metadata. | 17 | Snapshot report |
| [central_org_designations](central_org_designations.md) | Central organization job titles and their named levels, without personnel records. | 7 | Snapshot report |
| [central_org_units](central_org_units.md) | Central organization offices/units, their parents, own levels and typed location codes. | 10 | Snapshot report |
| [central_orgs](central_orgs.md) | Central departments/organizations, their types and reported parent organizations. | 6 | Snapshot report |
| [changes](changes.md) | Discontinued cumulative entity-change events with typed entity references and reported dates. | 9 | Cumulative events |
| [constituencies_mapping_pri](constituencies_mapping_pri.md) | Historical village/body/block constituency links, including reported LGD-to-ECI codes. | 22 | Snapshot report |
| [constituencies_mapping_urban](constituencies_mapping_urban.md) | Urban ward/assembly links with district/subdistrict paths and reported ECI identifiers. | 16 | Snapshot report |
| [constituency_coverage](constituency_coverage.md) | Typed entity-to-constituency links; conflicting full/partial claims remain unresolved. | 12 | Snapshot report |
| [district_panchayats](district_panchayats.md) | Links between district panchayats and administrative districts, in either direction. | 6 | Snapshot report |
| [districts](districts.md) | Districts with their reported state and 2001/2011 census identifiers. | 6 | Snapshot report |
| [gp_mapping](gp_mapping.md) | Village-to-gram-panchayat links with administrative and census context. | 16 | Snapshot report |
| [invalidated_census_villages](invalidated_census_villages.md) | Villages listed as invalidated, with state and optional census references; no invalidation dates. | 6 | Snapshot report |
| [nofn_panchayats](nofn_panchayats.md) | Retired NOFN project membership list, with body codes and named geographic paths. | 6 | Snapshot report |
| [org_unit_coverage](org_unit_coverage.md) | Unit/type/target coverage associations or explicit no-details rows; flags and labels remain attributes. | 16 | Snapshot report |
| [org_unit_details](org_unit_details.md) | Office contact/address details, parent references and typed location names for state and central units. | 16 | Snapshot report |
| [parliament_constituencies](parliament_constituencies.md) | Parliamentary constituencies with LGD identifiers and state references; no ECI numbers. | 4 | Snapshot report |
| [parliament_constituencies_lb_mapping](parliament_constituencies_lb_mapping.md) | Legacy parliamentary-to-named-body links; assembly and body codes are not supplied. | 7 | Snapshot report |
| [pincode_urban](pincode_urban.md) | Reported urban-local-body/pincode links, with body and state names. | 6 | Snapshot report |
| [pincode_villages](pincode_villages.md) | Reported village/pincode links with administrative parents retained as attributes. | 9 | Snapshot report |
| [pri_local_bodies](pri_local_bodies.md) | Panchayati Raj bodies at district, intermediate and village levels, with parent codes. | 9 | Snapshot report |
| [pri_local_body_wards](pri_local_body_wards.md) | PRI wards with body/state attributes and names resolved from a dated PRI register when needed. | 11 | Snapshot report |
| [state_admin_dept_units](state_admin_dept_units.md) | Named state administrative units linked to their administrative-unit levels. | 7 | Snapshot report |
| [state_admin_depts](state_admin_depts.md) | State administrative-unit level definitions and hierarchy metadata, despite the department filename. | 19 | Snapshot report |
| [state_org_designations](state_org_designations.md) | State organization job titles and the levels where they are reported, without personnel records. | 9 | Snapshot report |
| [state_org_units](state_org_units.md) | State organization offices/units, their parents, own levels and typed location codes. | 12 | Snapshot report |
| [state_orgs](state_orgs.md) | State departments/organizations, their types and reported parent organizations. | 8 | Snapshot report |
| [states](states.md) | States and union territories, their LGD and census identifiers, names and classification. | 7 | Snapshot report |
| [statewise_ulbs_coverage](statewise_ulbs_coverage.md) | Urban-body coverage at district, subdistrict or village level, including partial paths. | 10 | Snapshot report |
| [subdistricts](subdistricts.md) | Subdistricts with version, district/state references and census identifiers. | 9 | Snapshot report |
| [tlb_villages](tlb_villages.md) | Village/block links to both PRI gram panchayats and traditional bodies, despite the filename. | 18 | Snapshot report |
| [traditional_local_bodies](traditional_local_bodies.md) | Traditional bodies and reported parent paths, with state-specific types and hierarchy gaps. | 11 | Snapshot report |
| [transactions](transactions.md) | Cumulative transaction events with operation, date, state scope and free-text descriptions. | 7 | Cumulative events |
| [urban_local_bodies](urban_local_bodies.md) | Urban bodies with state, body type, version and a separate census identifier. | 8 | Snapshot report |
| [urban_local_body_wards](urban_local_body_wards.md) | Urban wards with their parent body, state, names and ward number. | 8 | Snapshot report |
| [villages](villages.md) | Villages, their administrative parents, census identifiers and reported status/category. | 15 | Snapshot report |
| [villages_by_blocks](villages_by_blocks.md) | Village links to development blocks and supplied local bodies, with administrative paths. | 17 | Snapshot report |
