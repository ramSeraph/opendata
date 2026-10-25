# Dataset query APIs

These helpers are unreleased. Install from this checkout to use them.

Every module returns DuckDB relations over source-report Parquet files. See
[query conventions](../QUERIES.md) for matching, filters, dependencies and dates.

For a description of every report and its relationships, browse the
[dataset catalogue](../../../lgd/parquet/datasets/README.md). Each API guide
also links to its CSV → Parquet field definitions.

`Primary lookup` below is the code selected by `by_code`, not necessarily a
unique row key. Mapping reports can return several associations for one code.
Descriptions reflect the converter in this checkout; older published
generations can retain earlier schemas or normalization rules.

For the organization reports, start with the [data and source diagrams](../ORGANIZATION_DATA.md).
They explain departments, offices, designations, administrative units and coverage.

State/central org units and org-unit details can
[follow typed location references](../ORGANIZATION_DATA.md#follow-entity-references-to-registers)
to full register records. Org-unit coverage has the equivalent lookup for
covered targets. These `entities` APIs have explicit register dependencies,
separate from the name-search dependencies listed below.

| Dataset / query API | CSV → Parquet | Primary lookup | Census years | Additional name sources |
| --- | --- | --- | --- | --- |
| [states](states.md) | [Schema](../../../lgd/parquet/datasets/states.md) | `state_code` | 2001, 2011 | None |
| [districts](districts.md) | [Schema](../../../lgd/parquet/datasets/districts.md) | `district_code` | 2001, 2011 | None |
| [subdistricts](subdistricts.md) | [Schema](../../../lgd/parquet/datasets/subdistricts.md) | `subdistrict_code` | 2001, 2011 | None |
| [villages](villages.md) | [Schema](../../../lgd/parquet/datasets/villages.md) | `village_code` | 2001, 2011 | None |
| [blocks](blocks.md) | [Schema](../../../lgd/parquet/datasets/blocks.md) | `block_code` | None | None |
| [district_panchayats](district_panchayats.md) | [Schema](../../../lgd/parquet/datasets/district_panchayats.md) | `district_panchayat_code` | None | None |
| [pri_local_bodies](pri_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/pri_local_bodies.md) | `local_body_code` | None | pri_local_bodies |
| [urban_local_bodies](urban_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/urban_local_bodies.md) | `local_body_code` | 2011 | None |
| [traditional_local_bodies](traditional_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/traditional_local_bodies.md) | `local_body_code` | None | traditional_local_bodies, pri_local_bodies |
| [urban_local_body_wards](urban_local_body_wards.md) | [Schema](../../../lgd/parquet/datasets/urban_local_body_wards.md) | `ward_code` | None | None |
| [pri_local_body_wards](pri_local_body_wards.md) | [Schema](../../../lgd/parquet/datasets/pri_local_body_wards.md) | `ward_code` | None | None |
| [villages_by_blocks](villages_by_blocks.md) | [Schema](../../../lgd/parquet/datasets/villages_by_blocks.md) | `village_code` | 2011 | None |
| [gp_mapping](gp_mapping.md) | [Schema](../../../lgd/parquet/datasets/gp_mapping.md) | `village_code` | 2001, 2011 | None |
| [tlb_villages](tlb_villages.md) | [Schema](../../../lgd/parquet/datasets/tlb_villages.md) | `village_code` | 2011 | None |
| [statewise_ulbs_coverage](statewise_ulbs_coverage.md) | [Schema](../../../lgd/parquet/datasets/statewise_ulbs_coverage.md) | `local_body_code` | 2011 | None |
| [parliament_constituencies](parliament_constituencies.md) | [Schema](../../../lgd/parquet/datasets/parliament_constituencies.md) | `parliament_constituency_code` | None | None |
| [assembly_constituencies](assembly_constituencies.md) | [Schema](../../../lgd/parquet/datasets/assembly_constituencies.md) | `assembly_constituency_code` | None | None |
| [constituency_coverage](constituency_coverage.md) | [Schema](../../../lgd/parquet/datasets/constituency_coverage.md) | `entity_code` | None | None |
| [constituencies_mapping_pri](constituencies_mapping_pri.md) | [Schema](../../../lgd/parquet/datasets/constituencies_mapping_pri.md) | `village_code` | 2011 | states |
| [constituencies_mapping_urban](constituencies_mapping_urban.md) | [Schema](../../../lgd/parquet/datasets/constituencies_mapping_urban.md) | `ward_code` | None | states |
| [parliament_constituencies_lb_mapping](parliament_constituencies_lb_mapping.md) | [Schema](../../../lgd/parquet/datasets/parliament_constituencies_lb_mapping.md) | `parliament_constituency_code` | None | states |
| [pincode_villages](pincode_villages.md) | [Schema](../../../lgd/parquet/datasets/pincode_villages.md) | `village_code` | None | None |
| [pincode_urban](pincode_urban.md) | [Schema](../../../lgd/parquet/datasets/pincode_urban.md) | `local_body_code` | None | None |
| [invalidated_census_villages](invalidated_census_villages.md) | [Schema](../../../lgd/parquet/datasets/invalidated_census_villages.md) | `village_code` | 2001, 2011 | None |
| [state_orgs](state_orgs.md) | [Schema](../../../lgd/parquet/datasets/state_orgs.md) | `organization_code` | None | None |
| [central_orgs](central_orgs.md) | [Schema](../../../lgd/parquet/datasets/central_orgs.md) | `organization_code` | None | None |
| [state_org_units](state_org_units.md) | [Schema](../../../lgd/parquet/datasets/state_org_units.md) | `organization_unit_code` | None | org_unit_coverage, org_unit_details |
| [central_org_units](central_org_units.md) | [Schema](../../../lgd/parquet/datasets/central_org_units.md) | `organization_unit_code` | None | org_unit_coverage, org_unit_details |
| [state_org_designations](state_org_designations.md) | [Schema](../../../lgd/parquet/datasets/state_org_designations.md) | `designation_code` | None | None |
| [central_org_designations](central_org_designations.md) | [Schema](../../../lgd/parquet/datasets/central_org_designations.md) | `designation_code` | None | None |
| [state_admin_depts](state_admin_depts.md) | [Schema](../../../lgd/parquet/datasets/state_admin_depts.md) | `administrative_unit_level_code` | None | None |
| [central_admin_depts](central_admin_depts.md) | [Schema](../../../lgd/parquet/datasets/central_admin_depts.md) | `administrative_unit_level_code` | None | None |
| [state_admin_dept_units](state_admin_dept_units.md) | [Schema](../../../lgd/parquet/datasets/state_admin_dept_units.md) | `administrative_unit_code` | None | None |
| [central_admin_dept_units](central_admin_dept_units.md) | [Schema](../../../lgd/parquet/datasets/central_admin_dept_units.md) | `administrative_unit_code` | None | None |
| [org_unit_details](org_unit_details.md) | [Schema](../../../lgd/parquet/datasets/org_unit_details.md) | `organization_unit_code` | None | None |
| [org_unit_coverage](org_unit_coverage.md) | [Schema](../../../lgd/parquet/datasets/org_unit_coverage.md) | `organization_unit_code` | None | None |
| [nofn_panchayats](nofn_panchayats.md) | [Schema](../../../lgd/parquet/datasets/nofn_panchayats.md) | `local_body_code` | None | None |
| [changes](changes.md) | [Schema](../../../lgd/parquet/datasets/changes.md) | `entity_code` | None | None |
| [transactions](transactions.md) | [Schema](../../../lgd/parquet/datasets/transactions.md) | `transaction_id` | None | None |
