# pri_local_bodies

[All schemas](README.md) · [Query API](../../../lgd-query/docs/datasets/pri_local_bodies.md) · [Common conversion rules](../README.md#schemas-and-interpretation)

The Panchayati Raj Institutions (PRI) register identifies local
bodies by `local_body_code` and supplies their names, version, type,
state and immediate parent code. In this report, type codes `1`, `2`
and `3` denote district, intermediate/block and village panchayats.

The reported name of each type varies by state and remains as supplied.
A top-level body can have a blank parent.
Parent codes support hierarchy lookups within the register, while
[district_panchayats](district_panchayats.md) supplies links to
administrative districts. A block panchayat's local-body code is
distinct from a development-block code.

## Row identity and conversion

The reported record key is:

```text
(local_body_code)
```

Identical records collapse. Conflicting attributes for this key are rejected;
rows differing only in a known version retain the highest version. A mixture
of known and unknown versions for one key is rejected.

## Local body types and state names

For this PRI report, the codes describe these levels:

| `local_body_type_code` | Level |
| --- | --- |
| `1` | District panchayat |
| `2` | Intermediate / block panchayat |
| `3` | Village panchayat |

`local_body_type_name` contains the name reported for that type in the state.
Keep that label as supplied: one code can have several names nationally,
including capitalization and spelling differences. The code alone does not
determine the reported name.

The table below comes from the [released PRI snapshot](https://github.com/ramSeraph/opendata/releases/download/lgd-parquet-latest/pri_local_bodies.2026-10-23.d55b3f55f3413115.parquet)
for **2026-10-23**. All 86 reported state/type combinations
have exactly one nonblank name in that snapshot. These are source labels,
not corrected or independently verified legal designations, and may change
between observations.

Only states/UTs represented in this report are listed. **—** means the
snapshot has no rows for that state and level; it does not assert that no
such body exists or substitute a name from another dataset.

| State code | State / UT | District (`1`) | Intermediate (`2`) | Village (`3`) |
| --- | --- | --- | --- | --- |
| `1` | Jammu And Kashmir | District Planning & Development Board | Block Development Council | Halqa Panchayat |
| `2` | Himachal Pradesh | Zila Parishad | Panchayat Samiti | Gram Panchayat |
| `3` | Punjab | Zilla Parishad | Panchayat Samiti | Gram Panchayat |
| `5` | Uttarakhand | Zila Panchayat | Kshetra Panchayat | Gram Panchayat |
| `6` | Haryana | Zilla Parishad | Panchayat Samiti | Gram Panchayat |
| `8` | Rajasthan | Zila Panchayat | Block Panchayat | Gram Panchayat |
| `9` | Uttar Pradesh | Zilla Panchayat | Kshetra Panchayat | Gram Panchayat |
| `10` | Bihar | Zilla Parishad | Panchayat Samiti | Gram Panchayat |
| `11` | Sikkim | Zila Panchayat | — | Gram Panchayat |
| `12` | Arunachal Pradesh | Zilla Parishad | — | Gram Panchayat |
| `14` | Manipur | Zilla Parishad | — | Gram Panchayat |
| `16` | Tripura | Zila Panchayat | Block Panchayat | Gram Panchayat |
| `18` | Assam | Zilla Parishad | Anchalik Panchayat | Gaon Panchayat |
| `19` | West Bengal | Zilla Panchayat | Panchayat Samiti | Gram Panchayat |
| `20` | Jharkhand | Zila Panchayat | Panchayat Samiti | Gram Panchayat |
| `21` | Odisha | Zilla Parishad | Panchayat Samiti | Gram Panchayat |
| `22` | Chhattisgarh | Zila Panchayat | Janpad Panchayat | Gram Panchayat |
| `23` | Madhya Pradesh | Zila Panchayat | Janpad Panchayat | Gram Panchayat |
| `24` | Gujarat | District Panchayat | Taluka Panchayat | Gram Panchayat |
| `27` | Maharashtra | Zilla Parishad | Block Panchayat | Village Panchayat |
| `28` | Andhra Pradesh | Zilla Parishad | Mandal Panchayat | Grama Panchayat |
| `29` | Karnataka | Zila Panchayat | Taluka Panchayat | Gram Panchayat |
| `30` | Goa | Zila Panchayat | — | Village Panchayat |
| `31` | Lakshadweep | Zila Panchayat | — | Gram Panchayat |
| `32` | Kerala | DISTRICT PANCHAYAT | BLOCK PANCHAYAT | GRAMA PANCHAYAT |
| `33` | Tamil Nadu | Zila Panchayat | Panchayat Samiti | Gram Panchayat |
| `34` | Puducherry | — | Commune Panchayat | Village Panchayat |
| `35` | Andaman And Nicobar Islands | Zilla Parishad | Panchayat Samiti | Gram Panchayat |
| `36` | Telangana | Zilla Parishad | Mandal Panchayat | Grama Panchayat |
| `37` | Ladakh | District Planning & Development Board | Block Development Council | Halqa Panchayat |
| `38` | The Dadra And Nagar Haveli And Daman And Diu | Zilla Parishad | — | Gram Panchayat |

To inspect labels in a different loaded snapshot:

```sql
SELECT DISTINCT state_code, state_name, local_body_type_code, local_body_type_name
FROM pri_local_bodies
ORDER BY state_name, local_body_type_code, local_body_type_name;
```

## Fields

| ID | Field | SQL type | Primary source header | Column may be absent |
| ---: | --- | --- | --- | --- |
| 1 | `local_body_code` | `VARCHAR` | `Localbody Code` | No |
| 2 | `local_body_version` | `INTEGER` | `Localbody Version` | No |
| 3 | `local_body_name` | `VARCHAR` | `Localbody Name (In English)` | No |
| 4 | `local_body_name_local` | `VARCHAR` | `Localbody Name (In Local)` | No |
| 5 | `local_body_type_code` | `VARCHAR` | `Localbody Type Code` | No |
| 6 | `local_body_type_name` | `VARCHAR` | `Localbody Type Name` | No |
| 7 | `parent_local_body_code` | `VARCHAR` | `Parent Localbody Code` | No |
| 8 | `state_code` | `VARCHAR` | `State Code` | No |
| 9 | `state_name` | `VARCHAR` | `State Name` | No |
