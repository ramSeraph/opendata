# Dataset schemas

[Converter and common rules](../README.md#schemas-and-interpretation) · [Query index](../../../lgd-query/docs/datasets/README.md)

There are 37 snapshot-report schemas and two cumulative event schemas. Each
page describes its row identity, fields and normalization. **Queries** links to
its Python/CLI guide. Published generations may use older schema rules; inspect
the pinned manifest with `lgd-query resolve DATASET --manifest`.

In field tables, **Column may be absent** refers to a missing header, not a blank
supplied value. Optional absent columns become NULL; supplied blanks and sentinel
values follow the documented rules. Field IDs are stable within each dataset.

## Geography

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [states](states.md) | States and union territories, their LGD and census identifiers, names and classification. | [Queries](../../../lgd-query/docs/datasets/states.md) |
| [districts](districts.md) | Districts with their reported state and 2001/2011 census identifiers. | [Queries](../../../lgd-query/docs/datasets/districts.md) |
| [subdistricts](subdistricts.md) | Subdistricts with version, district/state references and census identifiers. | [Queries](../../../lgd-query/docs/datasets/subdistricts.md) |
| [villages](villages.md) | Villages, their administrative parents, census identifiers and reported status/category. | [Queries](../../../lgd-query/docs/datasets/villages.md) |
| [blocks](blocks.md) | Development blocks and their reported district associations; one block may have several. | [Queries](../../../lgd-query/docs/datasets/blocks.md) |

## Local bodies and wards

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [pri_local_bodies](pri_local_bodies.md) | Panchayati Raj bodies at district, intermediate and village levels, with parent codes. | [Queries](../../../lgd-query/docs/datasets/pri_local_bodies.md) |
| [traditional_local_bodies](traditional_local_bodies.md) | Traditional bodies and reported parent paths, with state-specific types and hierarchy gaps. | [Queries](../../../lgd-query/docs/datasets/traditional_local_bodies.md) |
| [urban_local_bodies](urban_local_bodies.md) | Urban bodies with state, body type, version and a separate census identifier. | [Queries](../../../lgd-query/docs/datasets/urban_local_bodies.md) |
| [pri_local_body_wards](pri_local_body_wards.md) | PRI wards with body/state attributes and names resolved from a dated PRI register when needed. | [Queries](../../../lgd-query/docs/datasets/pri_local_body_wards.md) |
| [urban_local_body_wards](urban_local_body_wards.md) | Urban wards with their parent body, state, names and ward number. | [Queries](../../../lgd-query/docs/datasets/urban_local_body_wards.md) |

## Geographic mappings

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [district_panchayats](district_panchayats.md) | Links between district panchayats and administrative districts, in either direction. | [Queries](../../../lgd-query/docs/datasets/district_panchayats.md) |
| [villages_by_blocks](villages_by_blocks.md) | Village links to development blocks and supplied local bodies, with administrative paths. | [Queries](../../../lgd-query/docs/datasets/villages_by_blocks.md) |
| [gp_mapping](gp_mapping.md) | Village-to-gram-panchayat links with administrative and census context. | [Queries](../../../lgd-query/docs/datasets/gp_mapping.md) |
| [tlb_villages](tlb_villages.md) | Village/block links to both PRI gram panchayats and traditional bodies, despite the filename. | [Queries](../../../lgd-query/docs/datasets/tlb_villages.md) |
| [statewise_ulbs_coverage](statewise_ulbs_coverage.md) | Urban-body coverage at district, subdistrict or village level, including partial paths. | [Queries](../../../lgd-query/docs/datasets/statewise_ulbs_coverage.md) |

## Constituencies

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [parliament_constituencies](parliament_constituencies.md) | Parliamentary constituencies with LGD identifiers and state references; no ECI numbers. | [Queries](../../../lgd-query/docs/datasets/parliament_constituencies.md) |
| [assembly_constituencies](assembly_constituencies.md) | Assembly constituencies with LGD identifiers and parliamentary/state parent attributes. | [Queries](../../../lgd-query/docs/datasets/assembly_constituencies.md) |
| [constituency_coverage](constituency_coverage.md) | Typed entity-to-constituency links; conflicting full/partial claims remain unresolved. | [Queries](../../../lgd-query/docs/datasets/constituency_coverage.md) |
| [constituencies_mapping_pri](constituencies_mapping_pri.md) | Historical village/body/block constituency links, including reported LGD-to-ECI codes. | [Queries](../../../lgd-query/docs/datasets/constituencies_mapping_pri.md) |
| [constituencies_mapping_urban](constituencies_mapping_urban.md) | Urban ward/assembly links with district/subdistrict paths and reported ECI identifiers. | [Queries](../../../lgd-query/docs/datasets/constituencies_mapping_urban.md) |
| [parliament_constituencies_lb_mapping](parliament_constituencies_lb_mapping.md) | Legacy parliamentary-to-named-body links; assembly and body codes are not supplied. | [Queries](../../../lgd-query/docs/datasets/parliament_constituencies_lb_mapping.md) |

## Organizations and administration

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [state_orgs](state_orgs.md) | State departments/organizations, their types and reported parent organizations. | [Queries](../../../lgd-query/docs/datasets/state_orgs.md) |
| [central_orgs](central_orgs.md) | Central departments/organizations, their types and reported parent organizations. | [Queries](../../../lgd-query/docs/datasets/central_orgs.md) |
| [state_org_units](state_org_units.md) | State organization offices/units, their parents, own levels and typed location codes. | [Queries](../../../lgd-query/docs/datasets/state_org_units.md) |
| [central_org_units](central_org_units.md) | Central organization offices/units, their parents, own levels and typed location codes. | [Queries](../../../lgd-query/docs/datasets/central_org_units.md) |
| [org_unit_details](org_unit_details.md) | Office contact/address details, parent references and typed location names for state and central units. | [Queries](../../../lgd-query/docs/datasets/org_unit_details.md) |
| [org_unit_coverage](org_unit_coverage.md) | Unit/type/target coverage associations or explicit no-details rows; flags and labels remain attributes. | [Queries](../../../lgd-query/docs/datasets/org_unit_coverage.md) |
| [state_org_designations](state_org_designations.md) | State organization job titles and the levels where they are reported, without personnel records. | [Queries](../../../lgd-query/docs/datasets/state_org_designations.md) |
| [central_org_designations](central_org_designations.md) | Central organization job titles and their named levels, without personnel records. | [Queries](../../../lgd-query/docs/datasets/central_org_designations.md) |
| [state_admin_depts](state_admin_depts.md) | State administrative-unit level definitions and hierarchy metadata, despite the department filename. | [Queries](../../../lgd-query/docs/datasets/state_admin_depts.md) |
| [central_admin_depts](central_admin_depts.md) | Central administrative-unit level definitions, such as postal levels, with hierarchy metadata. | [Queries](../../../lgd-query/docs/datasets/central_admin_depts.md) |
| [state_admin_dept_units](state_admin_dept_units.md) | Named state administrative units linked to their administrative-unit levels. | [Queries](../../../lgd-query/docs/datasets/state_admin_dept_units.md) |
| [central_admin_dept_units](central_admin_dept_units.md) | Named central administrative units linked to their levels, including individual postal units. | [Queries](../../../lgd-query/docs/datasets/central_admin_dept_units.md) |

## Postal and census records

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [pincode_villages](pincode_villages.md) | Reported village/pincode links with administrative parents retained as attributes. | [Queries](../../../lgd-query/docs/datasets/pincode_villages.md) |
| [pincode_urban](pincode_urban.md) | Reported urban-local-body/pincode links, with body and state names. | [Queries](../../../lgd-query/docs/datasets/pincode_urban.md) |
| [invalidated_census_villages](invalidated_census_villages.md) | Villages listed as invalidated, with state and optional census references; no invalidation dates. | [Queries](../../../lgd-query/docs/datasets/invalidated_census_villages.md) |

## Events

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [changes](changes.md) | Discontinued cumulative entity-change events with typed entity references and reported dates. | [Queries](../../../lgd-query/docs/datasets/changes.md) |
| [transactions](transactions.md) | Cumulative transaction events with operation, date, state scope and free-text descriptions. | [Queries](../../../lgd-query/docs/datasets/transactions.md) |

## Retired collection

| Dataset / schema | Contents | Query API |
| --- | --- | --- |
| [nofn_panchayats](nofn_panchayats.md) | Retired NOFN project membership list, with body codes and named geographic paths. | [Queries](../../../lgd-query/docs/datasets/nofn_panchayats.md) |
