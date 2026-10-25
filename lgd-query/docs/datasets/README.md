# Dataset query index

[Query conventions and CLI options](../QUERIES.md) · [Reader APIs](../READER.md)

Dataset-aware APIs are [experimental](../QUERIES.md#experimental-status), available
from 0.2.0. Open a dataset for its queries and filters; open **Schema** for row
identity, source columns and caveats. A primary lookup can match several rows.
Run `lgd-query list --available-only` to check the selected release's availability.

## Geography

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [states](states.md) | [Schema](../../../lgd/parquet/datasets/states.md) | `state_code` | 2001, 2011 |
| [districts](districts.md) | [Schema](../../../lgd/parquet/datasets/districts.md) | `district_code` | 2001, 2011 |
| [subdistricts](subdistricts.md) | [Schema](../../../lgd/parquet/datasets/subdistricts.md) | `subdistrict_code` | 2001, 2011 |
| [villages](villages.md) | [Schema](../../../lgd/parquet/datasets/villages.md) | `village_code` | 2001, 2011 |
| [blocks](blocks.md) | [Schema](../../../lgd/parquet/datasets/blocks.md) | `block_code` | None |

## Local bodies and wards

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [pri_local_bodies](pri_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/pri_local_bodies.md) | `local_body_code` | None |
| [traditional_local_bodies](traditional_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/traditional_local_bodies.md) | `local_body_code` | None |
| [urban_local_bodies](urban_local_bodies.md) | [Schema](../../../lgd/parquet/datasets/urban_local_bodies.md) | `local_body_code` | 2011 |
| [pri_local_body_wards](pri_local_body_wards.md) | [Schema](../../../lgd/parquet/datasets/pri_local_body_wards.md) | `ward_code` | None |
| [urban_local_body_wards](urban_local_body_wards.md) | [Schema](../../../lgd/parquet/datasets/urban_local_body_wards.md) | `ward_code` | None |

## Geographic mappings

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [district_panchayats](district_panchayats.md) | [Schema](../../../lgd/parquet/datasets/district_panchayats.md) | `district_panchayat_code` | None |
| [villages_by_blocks](villages_by_blocks.md) | [Schema](../../../lgd/parquet/datasets/villages_by_blocks.md) | `village_code` | 2011 |
| [gp_mapping](gp_mapping.md) | [Schema](../../../lgd/parquet/datasets/gp_mapping.md) | `village_code` | 2001, 2011 |
| [tlb_villages](tlb_villages.md) | [Schema](../../../lgd/parquet/datasets/tlb_villages.md) | `village_code` | 2011 |
| [statewise_ulbs_coverage](statewise_ulbs_coverage.md) | [Schema](../../../lgd/parquet/datasets/statewise_ulbs_coverage.md) | `local_body_code` | 2011 |

## Constituencies

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [parliament_constituencies](parliament_constituencies.md) | [Schema](../../../lgd/parquet/datasets/parliament_constituencies.md) | `parliament_constituency_code` | None |
| [assembly_constituencies](assembly_constituencies.md) | [Schema](../../../lgd/parquet/datasets/assembly_constituencies.md) | `assembly_constituency_code` | None |
| [constituency_coverage](constituency_coverage.md) | [Schema](../../../lgd/parquet/datasets/constituency_coverage.md) | `entity_code` | None |
| [constituencies_mapping_pri](constituencies_mapping_pri.md) | [Schema](../../../lgd/parquet/datasets/constituencies_mapping_pri.md) | `village_code` | 2011 |
| [constituencies_mapping_urban](constituencies_mapping_urban.md) | [Schema](../../../lgd/parquet/datasets/constituencies_mapping_urban.md) | `ward_code` | None |
| [parliament_constituencies_lb_mapping](parliament_constituencies_lb_mapping.md) | [Schema](../../../lgd/parquet/datasets/parliament_constituencies_lb_mapping.md) | `parliament_constituency_code` | None |

## Organizations and administration

Start with the [data model](../ORGANIZATION_DATA.md) or [query cookbook](../ORGANIZATION_QUERIES.md).

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [state_orgs](state_orgs.md) | [Schema](../../../lgd/parquet/datasets/state_orgs.md) | `organization_code` | None |
| [central_orgs](central_orgs.md) | [Schema](../../../lgd/parquet/datasets/central_orgs.md) | `organization_code` | None |
| [state_org_units](state_org_units.md) | [Schema](../../../lgd/parquet/datasets/state_org_units.md) | `organization_unit_code` | None |
| [central_org_units](central_org_units.md) | [Schema](../../../lgd/parquet/datasets/central_org_units.md) | `organization_unit_code` | None |
| [org_unit_details](org_unit_details.md) | [Schema](../../../lgd/parquet/datasets/org_unit_details.md) | `organization_unit_code` | None |
| [org_unit_coverage](org_unit_coverage.md) | [Schema](../../../lgd/parquet/datasets/org_unit_coverage.md) | `organization_unit_code` | None |
| [state_org_designations](state_org_designations.md) | [Schema](../../../lgd/parquet/datasets/state_org_designations.md) | `designation_code` | None |
| [central_org_designations](central_org_designations.md) | [Schema](../../../lgd/parquet/datasets/central_org_designations.md) | `designation_code` | None |
| [state_admin_depts](state_admin_depts.md) | [Schema](../../../lgd/parquet/datasets/state_admin_depts.md) | `administrative_unit_level_code` | None |
| [central_admin_depts](central_admin_depts.md) | [Schema](../../../lgd/parquet/datasets/central_admin_depts.md) | `administrative_unit_level_code` | None |
| [state_admin_dept_units](state_admin_dept_units.md) | [Schema](../../../lgd/parquet/datasets/state_admin_dept_units.md) | `administrative_unit_code` | None |
| [central_admin_dept_units](central_admin_dept_units.md) | [Schema](../../../lgd/parquet/datasets/central_admin_dept_units.md) | `administrative_unit_code` | None |

## Postal and census records

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [pincode_villages](pincode_villages.md) | [Schema](../../../lgd/parquet/datasets/pincode_villages.md) | `village_code` | None |
| [pincode_urban](pincode_urban.md) | [Schema](../../../lgd/parquet/datasets/pincode_urban.md) | `local_body_code` | None |
| [invalidated_census_villages](invalidated_census_villages.md) | [Schema](../../../lgd/parquet/datasets/invalidated_census_villages.md) | `village_code` | 2001, 2011 |

## Events

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [changes](changes.md) | [Schema](../../../lgd/parquet/datasets/changes.md) | `entity_code` | None |
| [transactions](transactions.md) | [Schema](../../../lgd/parquet/datasets/transactions.md) | `transaction_id` | None |

## Retired collection

| Dataset / API | Source schema | Primary lookup | Census years |
| --- | --- | --- | --- |
| [nofn_panchayats](nofn_panchayats.md) | [Schema](../../../lgd/parquet/datasets/nofn_panchayats.md) | `local_body_code` | None |
