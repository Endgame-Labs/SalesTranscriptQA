"""Pinned source extraction; identity joins never alter the source dialogue."""

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import pyarrow as pa
import pyarrow.parquet as pq
import yaml


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def download(manifest, root):
    root = Path(root)
    for entry in manifest["files"]:
        path = root / entry["path"].removeprefix("data/")
        if path.exists() and sha(path.read_bytes()) == entry["sha256"]:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with httpx.Client(timeout=180, follow_redirects=True) as client:
            response = client.get(entry["url"])
            response.raise_for_status()
        data = response.content
        if len(data) != entry["bytes"] or sha(data) != entry["sha256"]:
            raise ValueError(f"Source integrity failure: {path.name}")
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)


def name(row):
    return (
        row.get("Name")
        or " ".join(str(row[k]) for k in ("FirstName", "LastName") if row.get(k))
        or None
    )


def extract(source_root, output, manifest):
    source_root, output = Path(source_root), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for domain in ("b2b", "b2c"):
        filename = f"crmarenapro_{domain}_data.db"
        source = source_root / "upstream/github/local_data" / filename
        entry = next(e for e in manifest["files"] if e["path"].endswith(filename))
        if sha(source.read_bytes()) != entry["sha256"]:
            raise ValueError("Database checksum mismatch")
        db = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        if db.execute("pragma integrity_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity failure")
        tables = {
            t: {r["Id"]: dict(r) for r in db.execute(f'SELECT * FROM "{t}"')}
            for t in ("Opportunity", "Lead", "Account", "Contact")
        }
        calls, issues, groups = [], [], defaultdict(list)
        for raw in db.execute("SELECT * FROM VoiceCallTranscript__c ORDER BY Id"):
            row = dict(raw)
            body = row["Body__c"]
            if not isinstance(body, str) or not body.strip():
                raise ValueError(f"Invalid dialogue: {domain}:{row['Id']}")
            metadata, provenance = {}, []

            def add(key, value, table, record, fields, via):
                metadata[key] = value
                provenance.append(
                    dict(
                        field=key,
                        table=table,
                        record_id=record,
                        source_fields=fields,
                        join_path=via,
                    )
                )

            for key, field in [("created_at", "CreatedDate"), ("end_time", "EndTime__c")]:
                add(key, row[field], "VoiceCallTranscript__c", row["Id"], [field], [])
            op_id, lead_id = row["OpportunityId__c"], row["LeadId__c"]
            group = None
            if bool(op_id) == bool(lead_id):
                issues.append({"call_id": row["Id"], "issue": "ambiguous_or_missing_group"})
            else:
                table, linked_id = ("Opportunity", op_id) if op_id else ("Lead", lead_id)
                linked = tables[table].get(linked_id)
                join = [
                    f"VoiceCallTranscript__c.{'OpportunityId__c' if op_id else 'LeadId__c'}",
                    f"{table}.Id",
                ]
                add(
                    "opportunity_id" if op_id else "lead_id",
                    linked_id,
                    "VoiceCallTranscript__c",
                    row["Id"],
                    ["OpportunityId__c" if op_id else "LeadId__c"],
                    [],
                )
                if linked is None:
                    issues.append({"call_id": row["Id"], "issue": "unresolved_group"})
                else:
                    group = f"{domain}:{table.lower()}:{linked_id}"
                    add(
                        "opportunity_name" if op_id else "lead_name",
                        name(linked),
                        table,
                        linked_id,
                        ["Name"] if op_id else ["FirstName", "LastName"],
                        join,
                    )
                    if op_id:
                        for target, fk in [("Account", "AccountId"), ("Contact", "ContactId")]:
                            target_id = linked.get(fk)
                            target_row = tables[target].get(target_id)
                            if target_id:
                                add(target.lower() + "_id", target_id, table, linked_id, [fk], join)
                                if target_row is not None:
                                    fields = (
                                        ["Name"]
                                        if target_row.get("Name")
                                        else [
                                            k for k in ("FirstName", "LastName") if k in target_row
                                        ]
                                    )
                                    add(
                                        target.lower() + "_name",
                                        name(target_row),
                                        target,
                                        target_id,
                                        fields,
                                        join + [table + "." + fk, target + ".Id"],
                                    )
                                else:
                                    issues.append(
                                        {
                                            "call_id": row["Id"],
                                            "issue": "unresolved_" + target.lower(),
                                        }
                                    )
                    elif linked.get("Company"):
                        add("company_name", linked["Company"], table, linked_id, ["Company"], join)
            call_id = f"{domain}:{row['Id']}"
            call = dict(
                schema_version=1,
                call_id=call_id,
                domain=domain,
                upstream_id=row["Id"],
                dialogue=body,
                dialogue_sha256=sha(body.encode()),
                metadata=metadata,
                group_id=group,
                field_provenance=provenance,
                source_revision=manifest["github_revision"],
            )
            calls.append(call)
            if group:
                groups[group].append(call_id)
            frontmatter = {"call_id": call_id, "domain": domain, **metadata}
            md = (
                "---\n"
                + yaml.safe_dump(frontmatter, sort_keys=True, allow_unicode=True)
                + "---\n"
                + body
            )
            folder = output / "markdown" / domain
            folder.mkdir(parents=True, exist_ok=True)
            (folder / (row["Id"] + ".md")).write_text(md)
            assert md.split("---\n", 2)[2] == body
        expected = manifest["database_table_counts"][filename]["VoiceCallTranscript__c"]
        assert len(calls) == expected
        pq.write_table(
            pa.Table.from_pylist(calls), output / f"{domain}-corpus.parquet", compression="zstd"
        )
        write_json(
            output / f"{domain}-groups.json",
            {g: ids for g, ids in sorted(groups.items()) if len(ids) >= 2},
        )
        inventory[domain] = dict(
            calls=len(calls),
            groups=len(groups),
            groups_with_multiple_calls=sum(len(ids) >= 2 for ids in groups.values()),
            eligible_pairs=sum(len(ids) * (len(ids) - 1) // 2 for ids in groups.values()),
            group_size_histogram=dict(sorted(Counter(map(len, groups.values())).items())),
            identity_join_issues=issues,
            unique_dialogue_hashes=len({c["dialogue_sha256"] for c in calls}),
        )
        db.close()
    write_json(output / "inventory.json", inventory)
    return inventory
