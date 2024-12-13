# STL Metadata Extractor for Archivematica

This repository provides a script that extracts metadata from ASCII and binary Standard Tessellation Language (STL) files in [Archivematica](https://www.archivematica.org/).

## Installation

To install this script, follow these steps:

### 1. Create a new characterization command

- In the Archivematica frontend, navigate to **Preservation planning** > **Characterization** > **Commands** > **Create new command** or go directly to [this link](http://10.10.10.20/fpr/fpcommand/create/).
- Fill in the following fields:
  - **The related tool**: Select **Archivematica Script**.
  - **Description**: Enter `Characterize using stl-metadata-extractor`.
  - **Command**: Paste the entire content of the [**stl-metadata-extractor.py**](./src/stl-metadata-extractor.py) file.
  - **Script type**: Select **Python script**.
  - **The related output format**: Select **Text (Markup): XML: XML (fmt/101)**.
  - **Command usage**: Select **Characterization**.
  - Leave all other input fields and combo boxes untouched.
- Click **Save**.

### 2. Create a new characterization rule for ASCII STL

- In the Archivematica frontend, navigate to **Preservation planning** > **Characterization** > **Rules** > **Create new rule** or go directly to [this link](http://10.10.10.20/fpr/fprule/create/).
- Fill in the following fields:
  - **Purpose**: Select **Characterization**.
  - **The related format**: Select **Text (Source Code): STL (Standard Tessellation Language) ASCII: STL (x-fmt/108)**.
  - **Command**: Select **Characterize using stl-metadata-extractor**.
- Click **Save**.

### 3. Create a new characterization rule for binary STL

- In the Archivematica frontend, navigate to **Preservation planning** > **Characterization** > **Rules** > **Create new rule** or go directly to [this link](http://10.10.10.20/fpr/fprule/create/).
- Fill in the following fields:
  - **Purpose**: Select **Characterization**.
  - **The related format**: Select **CAD: STL (Standard Tessellation Language) Binary: STL (Standard Tessellation Language) Binary (fmt/865)**.
  - **Command**: Select **Characterize using stl-metadata-extractor**.
- Click **Save**.

## Test

To test this metadata exctractor, you can use the sample STL files located [here](https://github.com/JoergHeseler/3d-sample-files-for-digital-preservation-testing/tree/main/stl).

### In Archivematica:

You can view the error codes and detailed characterization results in the Archivmatica frontend after starting a transfer by expanding the `▸ Microservice: Characterize and extract metadata` section and clicking on the gear icon of `Microservice: Characterize and extract metadata`.

Valid files should pass characterization with this script and return error code **0**. However, files containing errors should fail characterization and either return error code **1** or **255**.

### In the command line:

You can use the validator at the command line prompt by typing `python stl-metadata-extractor.py --file-full-name=<STL file to characterize>`.

### Example

If you use this script to characterize the ASCII STL model [`cockatoo-stl-ascii-valid.stl`](https://github.com/JoergHeseler/3d-sample-files-for-digital-preservation-testing/blob/main/stl/cockatoo-stl-ascii-valid/cockatoo-stl-ascii-valid.stl), the error code **0** should be returned and the following XML content will be included in the AIP's METS document in the <objectCharacteristicsExtension> element of the file:

```xml
<?xml version="1.0" ?>
<STLMetadataExtractor xmlns="http://nfdi4culture.de/stl-metadata-extractor1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://nfdi4culture.de/stl-metadata-extractor1 https://raw.githubusercontent.com/JoergHeseler/stl-metadata-extractor-for-archivematica/refs/heads/main/src/stl-metadata-extractor.xsd">
    <formatName>STL (Standard Tessellation Language)</formatName>
    <formatVersion>ASCII</formatVersion>
    <size>149392856</size>
    <SHA256Checksum>6f93dd43857abfdfcad2f6c6e958213bbb52e5a2005c903f0ced92fbe6bd338a</SHA256Checksum>
    <creationDate>2024-12-13T13:37:19.261605</creationDate>
    <modificationDate>2024-12-13T13:37:19.297967</modificationDate>
    <solidName/>
    <totalTriangleCount>776822</totalTriangleCount>
    <hasValidCounterclockwiseVertices>true</hasValidCounterclockwiseVertices>
    <hasValidPositiveVerticeCoordinates>false</hasValidPositiveVerticeCoordinates>
</STLMetadataExtractor>
```

## Dependencies

[Archivematica 1.13.2](https://github.com/artefactual/archivematica/releases/tag/v1.13.2) was used to analyze, design, develop and test this script.

## Background

As part of the [NFDI4Culture](https://nfdi4culture.de/) initiative, efforts are underway to enhance the capabilities of open-source digital preservation software like Archivematica to identify, validate and characterize 3D file formats. This repository provides a script to extract metadata extraction of STL files in Archivematica, enhancing its 3D content preservation capabilities.

## Related projects

- [3D Sample Files for Digital Preservation Testing](https://github.com/JoergHeseler/3d-sample-files-for-digital-preservation-testing)
- [DAE Validator for Archivematica](https://github.com/JoergHeseler/dae-validator-for-archivematica)
- [glTF Metadata Extractor for Archivematica](https://github.com/JoergHeseler/gltf-metadata-extractor-for-archivematica)
- [glTF Validator for Archivematica](https://github.com/JoergHeseler/gltf-validator-for-archivematica)
- [Siegfried Falls Back on Fido Identifier for Archivematica](https://github.com/JoergHeseler/siegfried-falls-back-on-fido-identifier-for-archivematica)
- [STL Validator for Archivematica](https://github.com/JoergHeseler/stl-validator-for-archivematica)
- [X3D Validator for Archivematica](https://github.com/JoergHeseler/x3d-validator-for-archivematica)

## Imprint

[NFDI4Culture](https://nfdi4culture.de/) – Consortium for Research Data on Material and Immaterial Cultural Heritage

NFDI4Culture is a consortium within the German [National Research Data Infrastructure (NFDI)](https://www.nfdi.de/).

Author: [Jörg Heseler](https://orcid.org/0000-0002-1497-627X)

This repository is licensed under a [Creative Commons Attribution 4.0 International License (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/).

NFDI4Culture is funded by the German Research Foundation (DFG) – Project number – [441958017](https://gepris.dfg.de/gepris/projekt/441958017).
