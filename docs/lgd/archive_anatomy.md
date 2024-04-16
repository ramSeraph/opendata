---
layout: page
title: LGD Archive Anatomy
permalink: /lgd/anatomy
---

# Anatomy of a LGD archive

---

## states.csv

description:
: list of all states

Location in LGD:
: - Download Directory
    - STATE
      - All States of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Version | State LGD Version |
| State Name(In English) | State Name in English |
| State Name (In Local) | State Name in Local |
| Census 2001 Code | State Code from 2001 Census |
| Census 2011 Code | State Code from 2011 Census |
| State or UT | State(S) or Union Territory(U) |

---

## districts.csv

description:
: list of all districts

Location in LGD:
: - Download Directory
    - DISTRICT
      - All Districts of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |
| District Code | District LGD Code |
| District Name (In English) | District Name in English |
| Census 2001 Code | District Code from 2001 Census |
| Census 2011 Code | District Code from 2011 Census |

---

## subdistricts.csv

description:
: list of all subdistricts

Location in LGD:
: - Download Directory
    - SUB-DISTRICT
      - All Sub-Districts of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name | State Name in English |
| District Code | District LGD Code |
| District Name | District Name in English |
| Sub-district Code | Sub District LGD Code |
| Sub-district Version | Sub District LGD Version |
| Sub-district Name | Sub District Name in English |
| Census 2001 code | Sub District Code from 2001 Census |
| Census 2011 code | Sub District Code from 2011 Census |

---

## blocks.csv

description:
: list of all blocks

Location in LGD:
: - Download Directory
    - Development Block
      - All Development Blocks of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |
| District Code | District LGD Code |
| District Name (In English) | District Name in English |
| Block Code | Block LGD Code |
| Block Version | Version of Block in LGD |
| Block Name (In English) | Block Name in English |
| Block Name (In Local) | Block Name in Local language |

---

## traditional_local_bodies.csv

description:
: list of all Traditional Local bodies

Location in LGD:
: - Download Directory
    - Local body
      - All Traditional Local Bodies of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |
| District Panchayat Code | LGD code of the District Panchayat the local body belongs to |
| Intermediate/Block Panchayat Code | LGD code of the Intermediate/Block Panchayat the local body belongs to |
| Local Body Code | LGD Code for the local body |
| Local Body Version | Version of the local body in LGD |
| Local Body Name (In English) | Name of the local body in English |
| Local Body Name (In Local) | Name of the local body in Local language |
| Localbody Type Code | LGD Code for the type of local body |
| Localbody Type Name | The type of local body |

---

## urban_local_bodies.csv

description:
: list of all Urban Local bodies

Location in LGD:
: - Download Directory
    - Local body
      - All Urban Local Bodies of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |
| Local Body Code | LGD Code for the local body |
| Local Body Version | Version of the local body in LGD |
| Local Body Name (In English) | Name of the local body in English |
| Local Body Name (In Local) | Name of the local body in Local language |
| Localbody Type Code | LGD Code for the type of local body |
| Census 2011 Code | census 2011 Code for the local body |

---

## statewise_ulbs_coverage.csv

description:
: list of all urban local bodies with coverage

Location in LGD:
: - Download Directory
    - Local body
      - Urban Localbodies with Coverage

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Name (In English) | State Name in English |
| Localbody Code | LGD Code for the local body |
| Localbody Name (In English) | Name of the local body in English |
| Census 2011 Code | census 2011 Code for the local body |
| District Code | District LGD Code |
| District Name (In English) | District  Name in English |
| Subdistrict Code | Sub District LGD Code |
| Subdistrict Name (In English) | Sub District Name in English |
| Village Code | Village LGD Code |
| Village Name (In English) | Village Name in English |

---

## district_panchayats.csv

description:
: list of all district panchayats with mapping to districts

Location in LGD:
: - Download Directory
    - Local body
      - District To District Panchayat Mapping Of India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name | State Name in English |
| District Code | District LGD Code |
| District Name | District Name in English |
| District Panchayat Code | District Panchayat LGD Code |
| District Panchayat | District Panchayat Name in English |

---

## parliament_constituencies.csv

description:
: list of all parliament constituencies

Location in LGD:
: - Download Directory
    - Parliament/Assembly Constituency
      - Parliament Constituency or Assembly Constituency of a State/India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name | State Name in English |
| Parliament Constituency Code | Parliament Constituency LGD Code |
| Parliament Constituency Name | Parliament Constituency Name |
| Assembly Constituency Code | Assembly Constituency LGD Code |
| Assembly Constituency Name | Assembly Constituency Name |

---

## assembly_constituencies.csv

description:
: list of all assembly constituencies

Location in LGD:
: - Download Directory
    - Parliament/Assembly Constituency
      - Parliament Constituency or Assembly Constituency of a State/India

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name | State Name in English |
| Parliament Constituency Code | Parliament Constituency LGD Code |
| Parliament Constituency Name | Parliament Constituency Name |
| Assembly Constituency Code | Assembly Constituency LGD Code |
| Assembly Constituency Name | Assembly Constituency Name |

---

## pincode_villages.csv

description:
: Pincode to Village Mapping

Location in LGD:
: - Download Directory
    - Pincode Mapping
      - Pincode to Village Mapping

Expected fields:
: | Name | Description |
| :---: | :---: |
| State Code | State LGD Code |
| State Name | State Name in English |
| District Code | District LGD Code |
| District Name | District Name in English |
| Subdistrict Code | Sub District LGD Code |
| Subdistrict Name | Sub District Name in English |
| Village Code | Village LGD Code |
| Village Name | Village Name in English |
| Pincode | Postal PIN Code |

---

## pincode_urban.csv

description:
: Pincode to Urban Mapping

Location in LGD:
: - Download Directory
    - Pincode Mapping
      - Pincode to Urban Mapping

Expected fields:
: | Name | Description |
| :---: | :---: |
| State Code | State LGD Code |
| State Name | State Name in English |
| Localbody Code | Urban Localbody LGD Code |
| Localbody Name | Urban Localbody Name in English |
| Localbody Type Name | Type of Urban Localbody |
| Pincode | Postal PIN Code |

---

## central_orgs.csv

description:
: list of all central organization details

Location in LGD:
: - Download Directory
    - Department/Organization
      - Ministries/Departments/Organizations Details

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Organization Code | Organization LGD Code |
| Organization Name | Organization Name |
| Organization Type | Organization Type |
| Parent Organization Code | Parent Organization LGD Code |
| Parent Organization Name | Parent Organization Name |
| Parent Organization Type | Parent Organization Type |

---

## gp_mapping.csv

description:
: list of all panchayat mappings

Location in LGD:
: - Download Directory
    - Village To Gram Panchayat Mapping
      - Village To Gram Panchayat Mapping

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| District Code | District LGD Code |
| District Name (in English) | District Name in English |
| District Census Code 2011 | District Census 2011 Code |
| District Census Code 2001 | District Census 2001 Code |
| Sub District Code | Sub District LGD Code |
| Sub District Name (in English) | Sub District Name in English |
| Sub District Census Code 2011 | Sub District Census 2011 Code |
| Sub District Census Code 2001 | Sub District Census 2001 Code |
| Village Code | Village LGD Code |
| Village Name (in English) | Village Name in English |
| Village Census Code 2011 | Village Census 2011 Code |
| Village Census Code 2001 | Village Census 2001 Code |
| Local Body Code | Local Body LGD Code |
| Local Body Name (in English) | Local Body Name in English |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## villages.csv

description:
: list of all villages

Location in LGD:
: - Download Directory
    - VILLAGE
      - All Villages of a State

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| District Code | District LGD Code |
| District Name (In English) | District Name in English |
| Sub-District Code | Sub District LGD Code |
| Sub-District Name (In English) | Sub District Name in English |
| Village Code | Village LGD Code |
| Village Version | Village LGD Version |
| Village Name (In English) | Village Name in English |
| Census 2001 code | Village Code from 2001 Census |
| Census 2011 code | Village Code from 2011 Census |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |

---

## villages_by_blocks.csv

description:
: list of all village to block mappings

Location in LGD:
: - Download Directory
    - Development Block
      - Subdistrict, Village,Development Block and Gps Mapping

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name (In English) | State Name in English |
| District Code | District LGD Code |
| District Name (In English) | District Name in English |
| District Census Code 2011 | District Census 2011 Code |
| Subdistrict Code | Sub District LGD Code |
| Subdistrict Name (In English) | Sub District Name in English |
| Subdistrict Census Code 2011 | Sub District Census 2011 Code |
| Village Code | Village LGD Code |
| Village Name (In English) | Village Name in English |
| Village Census Code 2011 | Village Census 2011 Code |
| localbody Code | Local Body LGD Code |
| Localbody Name (In English) | Local Body Name in English |
| Localbody Census Code 2011 | Local Body Census 2011 Code |
| Block Code | Block LGD Code |
| Block Name (In English) | Block Name in English |
| District Code of Block | District of block LGD Code |
| District Name of Block (In English) | District Name of block in English |

---

## pri_local_bodies.csv

description:
: list of all PRI(Panchayati Raj India) local bodies

Location in LGD:
: - Download Directory
    - Local body
      - PRI Local Body of a State

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Localbody Type Code | LGD Code for the type of local body |
| Localbody Type Name | Name of the type of local body |
| Localbody Code | LGD Code for the local body |
| Localbody Version | Version of the local body in LGD |
| Localbody Name (In English) | Name of the local body in English |
| Localbody Name (In Local) | Name of the local body in Local language |
| Parent Localbody Code | LGD Code for the parent local body |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## constituencies_mapping_urban.csv

description:
: list of all constituencies with Urban local body coverage

Location in LGD:
: - Download Directory
    - Parliament/Assembly Constituency
      - State Wise Parliament Constituency and Assembly Constituency along with coverage details Urban

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Parliament Constituency code | LGD Code for the parliament constituency |
| Parliament Constituency ECI Code | ECI(Election Commision of India) Code for the parliament constituency |
| Parliament Constituency Name | Name of the parliament constituency |
| Assembly Constituency code | LGD Code for the assembly constituency |
| Assembly Constituency ECI Code | ECI(Election Commision of India) Code for the assembly constituency |
| Assembly Constituency Name | Name of the assembly constituency |
| District Code | District LGD Code |
| District Name | Name of the District |
| SubDistrict Code | Sub District LGD Code |
| SubDistrict Name | Name of the Sub District |
| Ward Code | Ward LGD Code |
| Ward Name | Ward LGD Name |
| Urban Localbody Code | LGD Code of the Urban Local Body Code |
| Urban Localbody Name | Name of the Urban Local Body |
| State Code | State LGD Code |

---

## pri_local_body_wards.csv

description:
: list of all PRI Local body wards

Location in LGD:
: - Download Directory
    - Local body
      - Wards of PRI Local Bodies

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Local Body Code | LGD Code for the local body |
| Local Body Name | Name of the local body in English |
| Local Body Type | Type of the local body |
| Disrtict Level Parent Name | The name of the parent District Level Panchayat |
| Intermediate Level Parent Name | The name of the parent intermediate Level Panchayat |
| Ward Code | Ward LGD Code |
| Ward Number | Number of the Ward |
| Ward Name (In English) | Ward Name in English |
| Ward Name (In Local) | Ward Name in Local |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## urban_local_body_wards.csv

description:
: list of all Urban Local body wards

Location in LGD:
: - Download Directory
    - Local body
      - Wards of Urban local bodies

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Local Body Code | LGD Code for the local body |
| Local Body Name | Name of the local body in English |
| Ward Code | Ward LGD Code |
| Ward Number | Number of the Ward |
| Ward Name | Ward Name |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## constituency_coverage.csv

description:
: list of all assembly/parliament constituencies and their coverage

Location in LGD:
: - Download Directory
    - Parliament/Assembly Constituency
      - Constituency Coverage Details

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| State Code | State LGD Code |
| State Name English | State Name in English |
| Parliament Constituency Code | LGD Code for the parliament constituency |
| Parliament Constituency Name | Name of the parliament constituency |
| Assembly Constituency Code | LGD Code for the assembly constituency |
| Assembly Constituency Name | Name of the assembly constituency |
| Entity Type | Entity Type( like District, SubDistrict, Localbody ) |
| Entity Code | Entity LGD Code |
| Entity Name | Entity Name |
| Coverage Type | Type of coverage, fully or partialy covered |
| State Name | State Name |

---

## tlb_villages.csv

description:
: the mapping of villages to Traditional Local Bodies and Panchayats

Location in LGD:
: - Download Directory
    - Development Block
      - Subdistrict, Village,Development Block and GPs/TLB Mapping

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial Number |
| State Census 2011 Code | State Census 2011 Code |
| District Code | Sub District LGD Code |
| District Name (In English) | Sub District Name in English |
| District Census 2011 Code | Sub District Census 2011 Code |
| Sub-district Code | Sub District LGD Code |
| Sub-district Name (In English) | Sub District Name in English |
| Sub-district Census 2011 code | Sub District Census 2011 Code |
| Village Code | Village LGD Code |
| Village Name (In English) | Village Name in English |
| Village Census 2011 Code  | Village Census 2011 Code |
| Gram Panchayat/ TLB Code | LGD code of TLB/GP |
| Gram Panchayat/ TLB (In English) | Name of TLB/GP in English |
| Gram Panchayat/ TLB Census 2011 Code | TLB/GP Census 2011 Code |
| Gram Panchayat/ TLB Type Code | Type Code of TLB/GP |
| Gram Panchayat/ TLB Type Name | Type of TLB/GP |
| Block Code | Block LGD Code |
| Block Name (In English) | Block Name in English |
| State Code | State LGD Code |
| State Name | State Name |

---

## state_orgs.csv

description:
: list of all state level organizations

Location in LGD:
: - Download Directory
    - Department/Organization
      - Ministries/Departments/Organizations Details

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Organization Code | Organization LGD Code |
| Organization Name | Organization Name |
| Organization Type | Organization Type |
| Parent Organization Code | Parent Organization LGD Code |
| Parent Organization Name | Parent Organization Name |
| Parent Organization Type | Parent Organization Type |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## state_org_units.csv

description:
: list of all state level organization units

Location in LGD:
: - Download Directory
    - Department/Organization
      - Organization Units of a Department/Organization

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Org Unit Code | Org Unit LGD Code |
| Org Unit Name (In English) | Org Unit Name in English |
| Org Unit Name (In Local) | Org Unit Name in Local language |
| Entity Type | Associated Entity Type |
| Entity Lc | Associated Entity LGD Code |
| Parent Org Unit Code | Parent Org Unit LGD Code |
| Parent Org Unit Name | Parent Org Unit Name |
| Org Located Level Code | ??? |
| Base Organization Name | Base Organization Name |
| Base Organization Code | Base Organization LGD Code |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## central_org_units.csv

description:
: list of all central organization units

Location in LGD:
: - Download Directory
    - Department/Organization
      - Organization Units of a Department/Organization

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Org Unit Code | Org Unit LGD Code |
| Org Unit Name (In English) | Org Unit Name in English |
| Org Unit Name (In Local) | Org Unit Name in Local language |
| Entity Type | Associated Entity Type |
| Entity Lc | Associated Entity LGD Code |
| Parent Org Unit Code | Parent Org Unit LGD Code |
| Parent Org Unit Name | Parent Org Unit Name |
| Org Located Level Code | ??? |
| Base Organization Name | Base Organization Name |
| Base Organization Code | Base Organization LGD Code |

---

## state_org_designations.csv

description:
: list of all state level organization designations

Location in LGD:
: - Download Directory
    - Department/Organization
      - Designations of a Department/Organization

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Designation Code | Designation LGD Code |
| Designation Name (In English) | Designation Name in English |
| Designation Name Local (In Local) | Designation Name in Local language |
| Org Located Level Code | ??? |
| Org Level Specific Name | ??? |
| Base Organization Name | Base Organization Name |
| Base Organization Code | Base Organization LGD Code |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## central_org_designations.csv

description:
: list of all central organization designations

Location in LGD:
: - Download Directory
    - Department/Organization
      - Designations of a Department/Organization

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Designation Code | Designation LGD Code |
| Designation Name (In English) | Designation Name in English |
| Designation Name Local (In Local) | Designation Name in Local language |
| Org Located Level Code | ??? |
| Org Level Specific Name | ??? |
| Base Organization Name | Base Organization Name |
| Base Organization Code | Base Organization LGD Code |

---

## central_admin_dept_units.csv

description:
: list of all central adminstrative department units

Location in LGD:
: - Download Directory
    - Department/Organization
      - Administrative Unit Level Wise Administrative Unit Entity

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Admin Unit Entity Code | Admin Unit Entity LGD Code |
| Admin Unit Entity Name | Admin Unit Entity Name in English |
| Admin Unit Entity Name (Local) | Admin Unit Entity Name in Local Language |
| Admin Department Name | Admin Department Name in English |
| Admin Department Code | Admin Department LGD Code |

---

## state_admin_dept_units.csv

description:
: list of all state adminstrative department units

Location in LGD:
: - Download Directory
    - Department/Organization
      - Administrative Unit Level Wise Administrative Unit Entity

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Admin Unit Entity Code | Admin Unit Entity LGD Code |
| Admin Unit Entity Name | Admin Unit Entity Name in English |
| Admin Unit Entity Name (Local) | Admin Unit Entity Name in Local Language |
| Admin Department Name | Admin Department Name in English |
| Admin Department Code | Admin Department LGD Code |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## central_admin_depts.csv

description:
: list of all central administrative departments

Location in LGD:
: - Download Directory
    - Department/Organization
      - Administrative Unit Level Wise Administrative Unit Entity

Expected fields:
: | Name | Description |
| :---: | :---: |
| adminLevelNameEng | Name of Administrative Department in English |
| adminUnitCode | Administrative Department Code |
| parentAdminCode | Parent Administrative Department Code |

---

## state_admin_depts.csv

description:
: list of all state administrative departments

Location in LGD:
: - Download Directory
    - Department/Organization
      - Administrative Unit Level Wise Administrative Unit Entity

Expected fields:
: | Name | Description |
| :---: | :---: |
| adminLevelNameEng | Name of Administrative Department in English |
| adminUnitCode | Administrative Department Code |
| parentAdminCode | Parent Administrative Department Code |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## invalidated_census_villages.csv

description:
: list of all invalidated census villages

Location in LGD:
: - Likely Erroneous/Exceptions
    - Invalidated Census villages

Expected fields:
: | Name | Description |
| :---: | :---: |
| Sr No. | Serial number |
| State LGD Code | State LGD Code |
| State Name English | State Name in English |
| Village LGD Code | Village LGD Code |
| Village Name English | Village Name in English |

---

## nofn_panchayats.csv

description:
: list of all panchayats with National Optic Fiber Network(NOFN)

Location in LGD:
: - Local Government Directory (LGD) Reports
    - NOFN Panchayat List

Expected fields:
: | Name | Description |
| :---: | :---: |
| SR.NO | Serial number |
| District Name | District Name in English |
| Sub District Name(In English) | Sub District Name in English |
| Local Body Code | Local Body LGD Code |
| Local Body Name (In English) | Local Body Name in English |
| State Code | State LGD Code |
| State Name | State Name in English |

---

## changes.csv

description:
: all changes to entities in LGD

Location in LGD:
: - Local Government Directory (LGD) Reports
    - List Of Modification Done In LGD

Expected fields:
: | Name | Description |
| :---: | :---: |
| S.No. | Serial number |
| Entity Code | Entity LGD Code |
| Entity version | Entity Version |
| Entity Name (In English) | Entity Name in English |
| Entity Name (In Local) | Sub District Name in Local language |
| Census Code | Entity's Census 2011 Code |
| Operation | The change operation on the entity |
| date | The date on which the change happened |


