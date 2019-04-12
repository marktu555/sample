from oblib import taxonomy, data_model, util

import csv
import sys

ENTITY = "PLUTO"

# This table fails - the reason why is not fully understood.
skip = ["SiteLease",
    "IECRECertificate",
    "FinancialPerformance",
    "SystemDeviceListing",
    "System",
    "CutSheet",
    "ProjectFinancing",
    "All"
]

types = {}

if len(sys.argv) != 3:
    print("Incorrect number of arguments - 2 required")
    print("  Path and filename to types input file (example: types.csv)")
    print("  Path to Output directory (example: ./somepath/outdir)")
    sys.exit(1)

types_fn = sys.argv[1]
out_dn = sys.argv[2]

with open(types_fn, "r") as infile:
    reader = csv.reader(infile, delimiter=",")
    for row in reader:
        if row[0] in ["xbrli:decimalItemType", "xbrli:monetaryItemType"]:
            types[row[0]] = float(row[1])
        elif row[0] == "xbrli:integerItemType":
            types[row[0]] = int(row[1])
        elif row[0] == "xbrli:booleanItemType":
            types[row[0]] = bool(row[1])
        else:
            types[row[0]] = row[1]

tax = taxonomy.Taxonomy()
for en in tax.semantic.get_all_entrypoints():

    if en in skip:
        print("Skipping:", en)
        continue

    print("Processing:", en)

    entrypoint = data_model.OBInstance(en, tax, dev_validation_off=True)
    relationships = tax.semantic.get_entrypoint_relationships(en)

    for concept_name in tax.semantic.get_entrypoint_concepts(en):

        c = tax.semantic.get_concept_details(concept_name)
        table = entrypoint.get_table_for_concept(c.id)

        # Skip elements that can't be generated - note that the string check on "Abstract"
        # is due to a taxonomy bug.  Once fixed c.abstract will suffice as the check.
        if c.abstract or "Abstract" in c.id or "Axis" in c.id or "Table" in c.id:
            continue

        kwargs = {}
        if c.period_type == taxonomy.PeriodType.instant:
            kwargs["instant"] = util.convert_taxonomy_xsd_date("2018-01-01")
        else:
            kwargs["duration"] = "forever"
        kwargs["entity"] = ENTITY
        if len(table.get_axes()) > 0:
            found = False
            values_to_add = []
            for a in table.get_axes():
                d = None
                for r in relationships:
                    if r.from_ == a:
                        d = r.to
                        break
                if d is not None:
                    for r in relationships:
                        if r.from_ == d:
                            kwargs[a] = r.to
                            value = types[c.type_name]
                            values_to_add.append([c.id, value])

            i = 1
            for a in table.get_axes():
                if a not in kwargs:
                    kwargs[a] = str(i)
                    i = i + 1

            if not found:
                value = types[c.type_name]
                values_to_add.append([c.id, value])

            for v in values_to_add:
                try:
                    entrypoint.set(v[0], v[1], **kwargs)
                except Exception as e:
                    print("Exception processing", c.id)
                    print(e)
        else:
            value = types[c.type_name]
            try:
                entrypoint.set(c.id, value, **kwargs)
            except Exception as e:
                print("Exception processing", c.id)
                print(e)

    entrypoint.to_JSON(out_dn + "/" + en + ".json")
    entrypoint.to_XML(out_dn + "/" + en + ".xml")