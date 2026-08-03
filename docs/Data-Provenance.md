# Bundled data provenance

FS FilterLab includes factual spectral curves reformatted for use on the
application's analytical grid. The upstream data repository states that these
values were digitized from publicly available graphs and tables published by
filter manufacturers, research institutions, and standards bodies.

The release preserves the bundled-data MIT license and every vendor notice
present in the pinned data repository. It does not add a source or attribution
that is absent from the upstream files.

Important limitations:

- per-dataset attribution may be incomplete, inaccurate, or out of date;
- curves are reference data and are not official manufacturer documentation;
- inclusion does not imply endorsement by any manufacturer or institution;
- structural validation does not establish measurement accuracy, provenance,
  authorization, suitability, or scientific correctness;
- product and organization names remain the property of their respective
  owners.

The v1 corpus is pinned to data commit
`a1e7a927dcd4c477aca2f7d36748532ad92fb895`. Its deterministic audit reconciles
1,566 discovered TSV files: 1,558 filters, 3 QE profiles, 1 illuminant, and 4
reflectors. Every file is structurally accepted, with zero skipped, duplicate,
or invalid datasets. These counts describe the pinned release corpus only.

This notice is factual release documentation and not legal advice.
